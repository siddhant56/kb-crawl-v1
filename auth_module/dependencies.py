"""
auth_module/dependencies.py
---------------------------
FastAPI dependency functions for authentication and authorisation.

Usage in route handlers:
    current_user: User = Depends(get_current_user)
    approved_user: User = Depends(require_approved)
    admin: User = Depends(require_super_admin)
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from auth_module.database import get_db
from auth_module.models import User, UserRole, UserStatus
from auth_module.security import decode_token

_bearer = HTTPBearer(auto_error=True)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User:
    """Validate Bearer token and return the corresponding User row.

    Raises 401 if the token is missing, malformed, or expired.
    Raises 401 if the user no longer exists in the database.
    """
    payload = decode_token(credentials.credentials)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user_id: str | None = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Malformed token payload.",
        )
    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account no longer exists.",
        )
    return user


def require_approved(user: User = Depends(get_current_user)) -> User:
    """Extend get_current_user: also require status == APPROVED.

    Raises 403 with the current account status if not approved.
    """
    if user.status != UserStatus.APPROVED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                f"Access not granted. "
                f"Your account status is '{user.status.value}'. "
                "Contact the super admin for access."
            ),
        )
    return user


def require_upload_access(user: User = Depends(require_approved)) -> User:
    """Extend require_approved: also require upload_access == True.

    Raises 403 if the user is approved but has not been granted upload access.
    """
    if not user.upload_access:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Upload access not granted. Contact the super admin to request document upload permissions.",
        )
    return user


def require_super_admin(user: User = Depends(get_current_user)) -> User:
    """Extend get_current_user: require role == SUPER_ADMIN and status == APPROVED.

    Raises 403 if the caller is not a super admin or their account is not active.
    """
    if user.role != UserRole.SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super admin privileges required.",
        )
    if user.status != UserStatus.APPROVED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super admin account is not active.",
        )
    return user
