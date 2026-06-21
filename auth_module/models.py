"""
auth_module/models.py
---------------------
SQLAlchemy ORM models.

Tables
------
users            – all registered accounts (users and super admins)
document_uploads – audit trail of every uploaded document
"""

import enum
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Enum as SAEnum, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class UserRole(str, enum.Enum):
    USER = "user"
    SUPER_ADMIN = "super_admin"


class UserStatus(str, enum.Enum):
    PENDING = "pending"    # just registered, awaiting approval
    APPROVED = "approved"  # super admin granted access
    DENIED = "denied"      # super admin rejected the request
    REVOKED = "revoked"    # access removed after previous approval


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    full_name = Column(String(255), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(SAEnum(UserRole), nullable=False, default=UserRole.USER)
    status = Column(SAEnum(UserStatus), nullable=False, default=UserStatus.PENDING)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Populated when status changes to APPROVED
    approved_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    approved_at = Column(DateTime, nullable=True)

    # Populated when status changes to DENIED
    denial_reason = Column(String(500), nullable=True)

    # Document upload permission — granted independently by a super admin
    upload_access = Column(Boolean, nullable=False, default=False)


class CustomCategory(Base):
    __tablename__ = "custom_categories"

    id            = Column(Integer, primary_key=True, index=True)
    name          = Column(String(100), unique=True, nullable=False, index=True)
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at    = Column(DateTime, nullable=False, default=datetime.utcnow)


class DocumentUpload(Base):
    __tablename__ = "document_uploads"

    id           = Column(Integer, primary_key=True, index=True)
    user_id      = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    filename     = Column(String(255), nullable=False)   # original filename from the client
    saved_as     = Column(String(255), nullable=False)   # path on disk (relative to knowledge-base/)
    category     = Column(String(100), nullable=False)
    content_hash = Column(String(64),  nullable=False, unique=True, index=True)  # SHA-256 of sanitized markdown
    chunks_added = Column(Integer,     nullable=False, default=0)
    uploaded_at  = Column(DateTime,    nullable=False, default=datetime.utcnow)


class ChatSession(Base):
    """One active conversation thread per user."""
    __tablename__ = "chat_sessions"

    id         = Column(Integer, primary_key=True, index=True)
    user_id    = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True, index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class ChatMessage(Base):
    """Individual turn within a chat session, ordered by turn_index."""
    __tablename__ = "chat_messages"

    id          = Column(Integer, primary_key=True, index=True)
    session_id  = Column(Integer, ForeignKey("chat_sessions.id"), nullable=False, index=True)
    role        = Column(String(20), nullable=False)   # "user" or "assistant"
    content     = Column(Text, nullable=False)
    turn_index  = Column(Integer, nullable=False)      # 0-based insertion order
    created_at  = Column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (UniqueConstraint("session_id", "turn_index", name="uq_session_turn"),)


class GuardrailLog(Base):
    """Audit trail for every message classified by the input guardrail layer."""
    __tablename__ = "guardrail_logs"

    id              = Column(Integer, primary_key=True, index=True)
    user_id         = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    direction       = Column(String(10), nullable=False)   # "input" (output reserved for future use)
    rule_id         = Column(String(50), nullable=False)   # "allowed" | "pricing" | "off_topic" | …
    message_snippet = Column(String(300), nullable=False)  # first 300 chars of the user message
    blocked         = Column(Boolean, nullable=False)
    created_at      = Column(DateTime, nullable=False, default=datetime.utcnow)
