"""Pydantic request/response schemas."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models import JobStatus, VideoStyle


# ---- Auth ----

class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str | None = None


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: EmailStr
    full_name: str | None = None
    created_at: datetime


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    sub: str | None = None


# ---- Video jobs ----

class VideoJobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    status: JobStatus
    style: VideoStyle
    input_photos: list[str]
    output_path: str | None = None
    error_message: str | None = None
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None


class VideoJobCreateResponse(BaseModel):
    job: VideoJobOut
    remaining_today: int


class DailyUsageOut(BaseModel):
    used_today: int
    limit: int
    remaining: int


# ---- Admin ----

class AdminLoginRequest(BaseModel):
    password: str


class AdminToken(BaseModel):
    access_token: str
    token_type: str = "bearer"


class AdminUserOut(BaseModel):
    id: str
    email: EmailStr
    full_name: str | None = None
    created_at: datetime
    last_seen_at: datetime | None = None
    online: bool
    jobs_count: int


class LoginEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    success: bool
    ip_address: str | None = None
    created_at: datetime


class AdminOverviewOut(BaseModel):
    users: list[AdminUserOut]
    recent_logins: list[LoginEventOut]
