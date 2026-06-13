"""
auth_module/schemas.py
----------------------
Pydantic v2 request/response schemas.

All schemas use `model_config = {"from_attributes": True}` where they need
to be constructed from SQLAlchemy ORM objects.
"""

from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel, Field, field_validator

from auth_module.models import UserRole, UserStatus
from auth_module.security import is_valid_email


# ---------------------------------------------------------------------------
# Shared validators
# ---------------------------------------------------------------------------

def _normalize_email(v: str) -> str:
    v = v.strip().lower()
    if not is_valid_email(v):
        raise ValueError("Invalid email address format.")
    return v


# ---------------------------------------------------------------------------
# User schemas
# ---------------------------------------------------------------------------

class UserPublic(BaseModel):
    """Safe user representation returned to any authenticated caller."""

    id: int
    email: str
    full_name: str
    role: UserRole
    status: UserStatus
    created_at: datetime

    model_config = {"from_attributes": True}


class UserAdmin(BaseModel):
    """Extended user representation returned to super admins."""

    id: int
    email: str
    full_name: str
    role: UserRole
    status: UserStatus
    created_at: datetime
    approved_by_id: Optional[int]
    approved_at: Optional[datetime]
    denial_reason: Optional[str]

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Auth request/response schemas
# ---------------------------------------------------------------------------

class RegisterRequest(BaseModel):
    email: str = Field(..., description="Valid email address")
    full_name: str = Field(..., min_length=2, max_length=255)
    password: str = Field(..., min_length=8, description="Minimum 8 characters")

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        return _normalize_email(v)


class LoginRequest(BaseModel):
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return v.strip().lower()


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserPublic


class SuperAdminInitRequest(BaseModel):
    """Used once to bootstrap the first super admin account."""

    email: str = Field(..., description="Super admin email address")
    full_name: str = Field(..., min_length=2, max_length=255)
    password: str = Field(..., min_length=8)

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        return _normalize_email(v)


# ---------------------------------------------------------------------------
# Admin operation schemas
# ---------------------------------------------------------------------------

class DenyRequest(BaseModel):
    reason: str = Field(..., min_length=5, max_length=500, description="Reason for denial")


class ChangeRoleRequest(BaseModel):
    role: UserRole


# ---------------------------------------------------------------------------
# Chat schemas
# ---------------------------------------------------------------------------

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    history: List[Any] = Field(default_factory=list, description="Prior turn list from Gradio/LangChain")


class ChatResponse(BaseModel):
    answer: str
    sources: List[Any] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Misc
# ---------------------------------------------------------------------------

class MessageResponse(BaseModel):
    message: str
