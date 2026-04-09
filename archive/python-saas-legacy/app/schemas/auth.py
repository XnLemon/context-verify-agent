from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

MemberRole = Literal["admin", "employee"]
MemberType = Literal["admin", "legal", "procurement", "business", "other"]
ThemePreference = Literal["light", "dark", "system"]
FontScale = Literal["small", "medium", "large"]


class MemberPublic(BaseModel):
    id: int
    username: str
    display_name: str
    role: MemberRole
    member_type: MemberType
    is_active: bool
    avatar_url: str | None = None
    theme_preference: ThemePreference = "system"
    font_scale: FontScale = "medium"
    notify_enabled: bool = True
    last_login_at: datetime | None = None
    created_at: datetime


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    challenge_token: str = Field(min_length=1, max_length=256)
    password_proof: str = Field(min_length=64, max_length=64)


class LoginChallengeRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)


class LoginChallengeResponse(BaseModel):
    challenge_token: str
    nonce: str
    salt: str
    expires_at: datetime


class LoginResponse(BaseModel):
    token: str
    expires_at: datetime
    member: MemberPublic


class CreateEmployeeRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=6, max_length=128)
    display_name: str = Field(min_length=1, max_length=64)
    member_type: Literal["legal", "procurement", "business", "other"] = "legal"


class EmployeeListResponse(BaseModel):
    items: list[MemberPublic]
    total: int


class ProfileUpdateRequest(BaseModel):
    display_name: str = Field(min_length=1, max_length=64)


class SettingsUpdateRequest(BaseModel):
    theme_preference: ThemePreference
    font_scale: FontScale
    notify_enabled: bool


class AvatarUploadResponse(BaseModel):
    avatar_url: str
    member: MemberPublic
