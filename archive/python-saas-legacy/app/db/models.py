from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class ContractModel(Base):
    __tablename__ = "contracts"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    type: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    author: Mapped[str] = mapped_column(Text, nullable=False)
    owner_username: Mapped[str | None] = mapped_column(Text, nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    source_file_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class ReviewRecordModel(Base):
    __tablename__ = "review_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    contract_id: Mapped[str] = mapped_column(
        Text,
        ForeignKey("contracts.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    summary: Mapped[dict] = mapped_column(JSONB, nullable=False)
    report_overview: Mapped[str] = mapped_column(Text, nullable=False)
    key_findings: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    next_actions: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    issues: Mapped[list["ReviewIssueModel"]] = relationship(
        back_populates="review",
        cascade="all, delete-orphan",
        lazy="joined",
    )


class ReviewIssueModel(Base):
    __tablename__ = "review_issues"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    review_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("review_records.id", ondelete="CASCADE"),
        nullable=False,
    )
    contract_id: Mapped[str] = mapped_column(Text, nullable=False)
    issue_id: Mapped[str] = mapped_column(Text, nullable=False)
    type: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(Text, nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    suggestion: Mapped[str] = mapped_column(Text, nullable=False)
    location: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    start_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    end_index: Mapped[int | None] = mapped_column(Integer, nullable=True)

    review: Mapped[ReviewRecordModel] = relationship(back_populates="issues")

    __table_args__ = (
        UniqueConstraint("review_id", "issue_id", name="uq_review_issue_id"),
    )


class ChatThreadModel(Base):
    __tablename__ = "chat_threads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    contract_id: Mapped[str] = mapped_column(
        Text,
        ForeignKey("contracts.id", ondelete="CASCADE"),
        nullable=False,
    )
    member_id: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    messages: Mapped[list["ChatMessageModel"]] = relationship(
        back_populates="thread",
        cascade="all, delete-orphan",
        lazy="joined",
    )

    __table_args__ = (
        UniqueConstraint("contract_id", "member_id", name="uq_chat_thread_contract_member"),
    )


class ChatMessageModel(Base):
    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    thread_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("chat_threads.id", ondelete="CASCADE"),
        nullable=False,
    )
    contract_id: Mapped[str] = mapped_column(Text, nullable=False)
    msg_id: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[str] = mapped_column(Text, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    timestamp: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    thread: Mapped[ChatThreadModel] = relationship(back_populates="messages")


class HistoryLogModel(Base):
    __tablename__ = "history_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    contract_id: Mapped[str] = mapped_column(
        Text,
        ForeignKey("contracts.id", ondelete="CASCADE"),
        nullable=False,
    )
    member_id: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    event_id: Mapped[str] = mapped_column(Text, nullable=False)
    type: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    metadata_json: Mapped[dict[str, str]] = mapped_column(JSONB, default=dict, nullable=False)


class KnowledgeChunkModel(Base):
    __tablename__ = "knowledge_chunks"

    chunk_id: Mapped[str] = mapped_column(Text, primary_key=True)
    doc_id: Mapped[str] = mapped_column(Text, nullable=False)
    source_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    version: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(Text, nullable=False)
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class MemberModel(Base):
    __tablename__ = "members"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    display_name: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[str] = mapped_column(Text, nullable=False)
    member_type: Mapped[str] = mapped_column(Text, nullable=False)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    password_salt: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    avatar_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    theme_preference: Mapped[str] = mapped_column(Text, nullable=False, default="system")
    font_scale: Mapped[str] = mapped_column(Text, nullable=False, default="medium")
    notify_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AuthSessionModel(Base):
    __tablename__ = "auth_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    member_id: Mapped[int] = mapped_column(Integer, ForeignKey("members.id", ondelete="CASCADE"), nullable=False)
    token: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class LoginAuditModel(Base):
    __tablename__ = "login_audits"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    member_id: Mapped[int] = mapped_column(Integer, ForeignKey("members.id", ondelete="CASCADE"), nullable=False)
    login_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    ip_address: Mapped[str | None] = mapped_column(Text, nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)


Index("idx_contracts_status_updated_at", ContractModel.status, ContractModel.updated_at)
Index("idx_contracts_owner_updated_at", ContractModel.owner_username, ContractModel.updated_at)
Index("idx_review_issues_contract_status_severity", ReviewIssueModel.contract_id, ReviewIssueModel.status, ReviewIssueModel.severity)
Index("idx_chat_messages_contract_created_at", ChatMessageModel.contract_id, ChatMessageModel.created_at)
Index("idx_history_logs_contract_member_created_at", HistoryLogModel.contract_id, HistoryLogModel.member_id, HistoryLogModel.created_at.desc())
Index("idx_members_role_active", MemberModel.role, MemberModel.is_active)
Index("idx_auth_sessions_member_expires", AuthSessionModel.member_id, AuthSessionModel.expires_at)
Index("idx_login_audits_member_login_at", LoginAuditModel.member_id, LoginAuditModel.login_at.desc())
