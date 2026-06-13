"""
auth_module/routers/admin.py
----------------------------
Super-admin–only endpoints for managing user accounts.

All routes require: valid JWT + role=super_admin + status=approved.

Routes
------
GET    /auth/admin/users                   – list all users (filterable)
GET    /auth/admin/users/{id}              – get one user
PATCH  /auth/admin/users/{id}/approve      – grant access
PATCH  /auth/admin/users/{id}/deny         – deny access
PATCH  /auth/admin/users/{id}/revoke       – remove previously granted access
PATCH  /auth/admin/users/{id}/role         – change role (user ↔ super_admin)
DELETE /auth/admin/users/{id}              – permanently delete a user
GET    /auth/admin/stats                   – user counts by status
"""

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from auth_module.database import get_db
from auth_module.dependencies import require_super_admin
from auth_module.models import User, UserRole, UserStatus
from auth_module.schemas import ChangeRoleRequest, DenyRequest, UserAdmin

router = APIRouter(prefix="/auth/admin", tags=["Admin — User Management"])


# ---------------------------------------------------------------------------
# Query endpoints
# ---------------------------------------------------------------------------


@router.get(
    "/users",
    response_model=List[UserAdmin],
    summary="List all users",
    description=(
        "Returns all registered users ordered by registration date (newest first). "
        "Filter by `status` or `role`. Supports pagination via `skip` and `limit`."
    ),
)
def list_users(
    status_filter: Optional[UserStatus] = Query(None, alias="status"),
    role_filter: Optional[UserRole] = Query(None, alias="role"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    _: User = Depends(require_super_admin),
) -> List[User]:
    q = db.query(User)
    if status_filter is not None:
        q = q.filter(User.status == status_filter)
    if role_filter is not None:
        q = q.filter(User.role == role_filter)
    return q.order_by(User.created_at.desc()).offset(skip).limit(limit).all()


@router.get(
    "/users/{user_id}",
    response_model=UserAdmin,
    summary="Get a single user",
)
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_super_admin),
) -> User:
    return _get_or_404(db, user_id)


@router.get(
    "/stats",
    summary="User statistics",
    description="Returns total user count and a breakdown of counts by status.",
)
def get_stats(
    db: Session = Depends(get_db),
    _: User = Depends(require_super_admin),
) -> dict:
    rows = db.query(User.status, func.count(User.id)).group_by(User.status).all()
    by_status = {s.value: count for s, count in rows}
    return {"total": sum(by_status.values()), "by_status": by_status}


# ---------------------------------------------------------------------------
# Status mutation endpoints
# ---------------------------------------------------------------------------


@router.patch(
    "/users/{user_id}/approve",
    response_model=UserAdmin,
    summary="Approve a user",
    description=(
        "Sets the user's status to `approved`, allowing them to log in and access "
        "the Gradio UI and chatbot API. Records which admin approved and when."
    ),
)
def approve_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_super_admin),
) -> User:
    user = _get_or_404(db, user_id)
    user.status = UserStatus.APPROVED
    user.approved_by_id = admin.id
    user.approved_at = datetime.utcnow()
    user.denial_reason = None
    db.commit()
    db.refresh(user)
    return user


@router.patch(
    "/users/{user_id}/deny",
    response_model=UserAdmin,
    summary="Deny a user",
    description=(
        "Sets the user's status to `denied`. A reason is required and will be "
        "stored for record-keeping. Cannot be applied to super admins or yourself."
    ),
)
def deny_user(
    user_id: int,
    body: DenyRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(require_super_admin),
) -> User:
    user = _get_or_404(db, user_id)
    _guard_self(user, admin, "deny")
    _guard_is_super_admin(user)
    user.status = UserStatus.DENIED
    user.denial_reason = body.reason
    db.commit()
    db.refresh(user)
    return user


@router.patch(
    "/users/{user_id}/revoke",
    response_model=UserAdmin,
    summary="Revoke a user's access",
    description=(
        "Sets the user's status to `revoked`, immediately blocking login. "
        "Any existing JWT for this user will be rejected on next DB lookup. "
        "Cannot be applied to super admins or yourself."
    ),
)
def revoke_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_super_admin),
) -> User:
    user = _get_or_404(db, user_id)
    _guard_self(user, admin, "revoke")
    _guard_is_super_admin(user)
    user.status = UserStatus.REVOKED
    db.commit()
    db.refresh(user)
    return user


# ---------------------------------------------------------------------------
# Role and deletion endpoints
# ---------------------------------------------------------------------------


@router.patch(
    "/users/{user_id}/role",
    response_model=UserAdmin,
    summary="Change a user's role",
    description=(
        "Promotes a regular user to `super_admin` or demotes a super_admin to `user`. "
        "Cannot be used on yourself."
    ),
)
def change_role(
    user_id: int,
    body: ChangeRoleRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(require_super_admin),
) -> User:
    user = _get_or_404(db, user_id)
    _guard_self(user, admin, "change the role of")
    user.role = body.role
    db.commit()
    db.refresh(user)
    return user


@router.delete(
    "/users/{user_id}",
    status_code=204,
    summary="Delete a user",
    description=(
        "Permanently removes the user record. "
        "Cannot be used on super admins or yourself."
    ),
)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_super_admin),
) -> None:
    user = _get_or_404(db, user_id)
    _guard_self(user, admin, "delete")
    _guard_is_super_admin(user)
    db.delete(user)
    db.commit()


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _get_or_404(db: Session, user_id: int) -> User:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    return user


def _guard_self(user: User, admin: User, action: str) -> None:
    if user.id == admin.id:
        raise HTTPException(status_code=400, detail=f"Cannot {action} yourself.")


def _guard_is_super_admin(user: User) -> None:
    if user.role == UserRole.SUPER_ADMIN:
        raise HTTPException(
            status_code=400,
            detail="This operation cannot be performed on a super admin account.",
        )
