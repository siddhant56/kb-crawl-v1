"""
auth_module/models.py
---------------------
SQLAlchemy ORM models.

Tables
------
users   – all registered accounts (users and super admins)
"""

import enum
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Enum as SAEnum, ForeignKey, Integer, String
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
