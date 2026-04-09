from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from threading import Lock

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import AuthSessionModel, LoginAuditModel, MemberModel
from app.db.session import session_scope
from app.schemas.auth import (
    CreateEmployeeRequest,
    LoginChallengeResponse,
    LoginResponse,
    MemberPublic,
    ProfileUpdateRequest,
    SettingsUpdateRequest,
)


@dataclass
class _LoginChallenge:
    username: str
    nonce: str
    password_hash: str
    member_id: int | None
    expires_at: datetime


class AuthService:
    _LOGIN_CHALLENGE_TTL_SECONDS = 90

    def __init__(self) -> None:
        self._enabled = True
        self._login_challenges: dict[str, _LoginChallenge] = {}
        self._challenge_lock = Lock()
        try:
            self._bootstrap_admin_if_needed()
        except RuntimeError:
            self._enabled = False

    def issue_login_challenge(self, *, username: str) -> LoginChallengeResponse:
        self._ensure_enabled()

        normalized_username = username.strip()
        if not normalized_username:
            raise ValueError("用户名或密码错误")

        with session_scope() as session:
            stmt = select(MemberModel).where(MemberModel.username == normalized_username)
            member = session.execute(stmt).scalar_one_or_none()

            if member is not None and member.is_active:
                salt = member.password_salt
                password_hash = member.password_hash
                member_id: int | None = member.id
            else:
                # Return challenge for unknown users too to avoid leaking account existence.
                salt = secrets.token_hex(16)
                password_hash = secrets.token_hex(32)
                member_id = None

        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(seconds=self._LOGIN_CHALLENGE_TTL_SECONDS)
        nonce = secrets.token_urlsafe(24)
        challenge_token = secrets.token_urlsafe(32)

        with self._challenge_lock:
            self._prune_expired_challenges(now)
            self._login_challenges[challenge_token] = _LoginChallenge(
                username=normalized_username,
                nonce=nonce,
                password_hash=password_hash,
                member_id=member_id,
                expires_at=expires_at,
            )

        return LoginChallengeResponse(
            challenge_token=challenge_token,
            nonce=nonce,
            salt=salt,
            expires_at=expires_at,
        )

    def login_with_proof(
        self,
        *,
        username: str,
        challenge_token: str,
        password_proof: str,
        ip_address: str | None,
        user_agent: str | None,
    ) -> LoginResponse:
        self._ensure_enabled()

        normalized_username = username.strip()
        if not normalized_username or not challenge_token.strip() or not password_proof.strip():
            raise ValueError("用户名或密码错误")

        now = datetime.now(timezone.utc)
        with self._challenge_lock:
            challenge = self._login_challenges.pop(challenge_token.strip(), None)

        if challenge is None:
            raise ValueError("用户名或密码错误")
        if challenge.expires_at <= now:
            raise ValueError("登录挑战已过期，请重试")
        if challenge.username != normalized_username:
            raise ValueError("用户名或密码错误")

        expected_proof = hashlib.sha256(f"{challenge.nonce}:{challenge.password_hash}".encode("utf-8")).hexdigest()
        if not secrets.compare_digest(expected_proof, password_proof):
            raise ValueError("用户名或密码错误")

        if challenge.member_id is None:
            raise ValueError("用户名或密码错误")

        with session_scope() as session:
            member = self._require_member_by_id(session, challenge.member_id)
            if member.username != normalized_username:
                raise ValueError("用户名或密码错误")
            return self._create_login_response(session, member, ip_address=ip_address, user_agent=user_agent)

    def authenticate_bearer(self, authorization: str | None) -> MemberPublic:
        self._ensure_enabled()

        if not authorization:
            raise PermissionError("缺少登录凭证")

        if not authorization.lower().startswith("bearer "):
            raise PermissionError("无效的登录凭证")

        token = authorization.split(" ", 1)[1].strip()
        if not token:
            raise PermissionError("无效的登录凭证")

        with session_scope() as session:
            stmt = (
                select(AuthSessionModel, MemberModel)
                .join(MemberModel, MemberModel.id == AuthSessionModel.member_id)
                .where(AuthSessionModel.token == token)
            )
            row = session.execute(stmt).first()
            if row is None:
                raise PermissionError("登录已失效，请重新登录")

            auth_session, member = row
            now = datetime.now(timezone.utc)
            if auth_session.expires_at <= now or not member.is_active:
                session.delete(auth_session)
                raise PermissionError("登录已失效，请重新登录")

            return self._to_member_public(member)

    def get_profile(self, member_id: int) -> MemberPublic:
        self._ensure_enabled()
        with session_scope() as session:
            member = self._require_member(session, member_id)
            return self._to_member_public(member)

    def update_profile(self, member_id: int, payload: ProfileUpdateRequest) -> MemberPublic:
        self._ensure_enabled()

        display_name = payload.display_name.strip()
        if not display_name:
            raise ValueError("昵称不能为空")

        with session_scope() as session:
            member = self._require_member(session, member_id)
            member.display_name = display_name
            member.updated_at = datetime.now(timezone.utc)
            session.add(member)
            session.flush()
            return self._to_member_public(member)

    def update_settings(self, member_id: int, payload: SettingsUpdateRequest) -> MemberPublic:
        self._ensure_enabled()

        with session_scope() as session:
            member = self._require_member(session, member_id)
            member.theme_preference = payload.theme_preference
            member.font_scale = payload.font_scale
            member.notify_enabled = payload.notify_enabled
            member.updated_at = datetime.now(timezone.utc)
            session.add(member)
            session.flush()
            return self._to_member_public(member)

    def update_avatar(self, member_id: int, avatar_url: str) -> MemberPublic:
        self._ensure_enabled()

        with session_scope() as session:
            member = self._require_member(session, member_id)
            member.avatar_url = avatar_url
            member.updated_at = datetime.now(timezone.utc)
            session.add(member)
            session.flush()
            return self._to_member_public(member)

    def logout(self, authorization: str | None) -> None:
        if not self._enabled:
            return

        if not authorization or not authorization.lower().startswith("bearer "):
            return

        token = authorization.split(" ", 1)[1].strip()
        if not token:
            return

        with session_scope() as session:
            existing = session.execute(select(AuthSessionModel).where(AuthSessionModel.token == token)).scalar_one_or_none()
            if existing is not None:
                session.delete(existing)

    def list_employees(self) -> list[MemberPublic]:
        self._ensure_enabled()

        with session_scope() as session:
            stmt = select(MemberModel).where(MemberModel.role == "employee").order_by(MemberModel.created_at.desc())
            rows = session.execute(stmt).scalars().all()
            return [self._to_member_public(item) for item in rows]

    def create_employee(self, payload: CreateEmployeeRequest) -> MemberPublic:
        self._ensure_enabled()

        username = payload.username.strip()
        if not username:
            raise ValueError("用户名不能为空")

        with session_scope() as session:
            existing = session.execute(select(MemberModel).where(MemberModel.username == username)).scalar_one_or_none()
            if existing is not None:
                raise ValueError("用户名已存在")

            salt, password_hash = self._hash_password(payload.password)
            now = datetime.now(timezone.utc)
            member = MemberModel(
                username=username,
                display_name=payload.display_name.strip(),
                role="employee",
                member_type=payload.member_type,
                password_hash=password_hash,
                password_salt=salt,
                is_active=True,
                theme_preference="system",
                font_scale="medium",
                notify_enabled=True,
                created_at=now,
                updated_at=now,
            )
            session.add(member)
            session.flush()
            return self._to_member_public(member)

    def _bootstrap_admin_if_needed(self) -> None:
        with session_scope() as session:
            existing_admin = session.execute(
                select(MemberModel).where(MemberModel.role == "admin").limit(1)
            ).scalar_one_or_none()
            if existing_admin is not None:
                return

            salt, password_hash = self._hash_password(settings.bootstrap_admin_password)
            now = datetime.now(timezone.utc)
            member = MemberModel(
                username=settings.bootstrap_admin_username,
                display_name=settings.bootstrap_admin_display_name,
                role="admin",
                member_type="admin",
                password_hash=password_hash,
                password_salt=salt,
                is_active=True,
                theme_preference="system",
                font_scale="medium",
                notify_enabled=True,
                created_at=now,
                updated_at=now,
            )
            session.add(member)

    def _ensure_enabled(self) -> None:
        if not self._enabled:
            raise RuntimeError("鉴权服务不可用：请先配置 POSTGRES_DSN。")

    def _hash_password(self, password: str) -> tuple[str, str]:
        salt = secrets.token_hex(16)
        digest = hashlib.sha256(f"{salt}:{password}".encode("utf-8")).hexdigest()
        return salt, digest

    def _require_member(self, session: Session, member_id: int) -> MemberModel:
        member = session.execute(select(MemberModel).where(MemberModel.id == member_id)).scalar_one_or_none()
        if member is None or not member.is_active:
            raise PermissionError("登录已失效，请重新登录")
        return member

    def _require_member_by_id(self, session: Session, member_id: int) -> MemberModel:
        member = session.execute(select(MemberModel).where(MemberModel.id == member_id)).scalar_one_or_none()
        if member is None or not member.is_active:
            raise ValueError("用户名或密码错误")
        return member

    def _prune_expired_challenges(self, now: datetime) -> None:
        expired_keys = [token for token, challenge in self._login_challenges.items() if challenge.expires_at <= now]
        for token in expired_keys:
            self._login_challenges.pop(token, None)

    def _create_login_response(
        self,
        session: Session,
        member: MemberModel,
        *,
        ip_address: str | None,
        user_agent: str | None,
    ) -> LoginResponse:
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(hours=settings.auth_session_ttl_hours)
        token = secrets.token_urlsafe(32)

        member.last_login_at = now
        member.updated_at = now
        session.add(member)

        session.add(
            AuthSessionModel(
                member_id=member.id,
                token=token,
                created_at=now,
                expires_at=expires_at,
            )
        )
        session.add(
            LoginAuditModel(
                member_id=member.id,
                login_at=now,
                ip_address=ip_address,
                user_agent=user_agent,
            )
        )
        session.flush()

        return LoginResponse(
            token=token,
            expires_at=expires_at,
            member=self._to_member_public(member),
        )

    def _to_member_public(self, member: MemberModel) -> MemberPublic:
        return MemberPublic(
            id=member.id,
            username=member.username,
            display_name=member.display_name,
            role=member.role,
            member_type=member.member_type,
            is_active=member.is_active,
            avatar_url=member.avatar_url,
            theme_preference=member.theme_preference,
            font_scale=member.font_scale,
            notify_enabled=member.notify_enabled,
            last_login_at=member.last_login_at,
            created_at=member.created_at,
        )
