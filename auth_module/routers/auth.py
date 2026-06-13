"""
auth_module/routers/auth.py
---------------------------
Public authentication endpoints.

Routes
------
POST /auth/register        – create a new PENDING account
POST /auth/login           – exchange credentials for a JWT
GET  /auth/me              – return current user's profile
POST /auth/token/verify    – validate a token (used by Next.js middleware)
POST /auth/admin/init      – one-time bootstrap of the first super admin
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from auth_module.database import get_db
from auth_module.dependencies import get_current_user
from auth_module.models import User, UserRole, UserStatus
from auth_module.schemas import (
    LoginRequest,
    RegisterRequest,
    SuperAdminInitRequest,
    TokenResponse,
    UserPublic,
)
from auth_module.security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["Authentication"])

# Status-specific error messages returned on login
_LOGIN_BLOCKED: dict[UserStatus, str] = {
    UserStatus.PENDING: "Your account is pending approval by a super admin.",
    UserStatus.DENIED: "Your account access has been denied. Contact the admin for details.",
    UserStatus.REVOKED: "Your account access has been revoked. Contact the admin.",
}


@router.post(
    "/register",
    response_model=UserPublic,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new account",
    description=(
        "Creates a new user account with **pending** status. "
        "The account cannot be used to log in until a super admin approves it "
        "via `PATCH /auth/admin/users/{user_id}/approve`."
    ),
)
def register(body: RegisterRequest, db: Session = Depends(get_db)) -> User:
    if db.query(User).filter(User.email == body.email).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )
    user = User(
        email=body.email,
        full_name=body.full_name.strip(),
        hashed_password=hash_password(body.password),
        role=UserRole.USER,
        status=UserStatus.PENDING,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login",
    description=(
        "Authenticate with email and password. "
        "Returns a JWT Bearer token valid for 24 hours (configurable via `AUTH_TOKEN_EXPIRE_MINUTES`). "
        "Only **approved** accounts can log in."
    ),
)
def login(body: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = db.query(User).filter(User.email == body.email).first()

    # Constant-time failure — don't reveal whether the email exists
    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    if user.status != UserStatus.APPROVED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=_LOGIN_BLOCKED.get(user.status, "Account not active."),
        )

    token = create_access_token(
        user_id=user.id,
        role=user.role.value,
        email=user.email,
        status=user.status.value,
    )
    return TokenResponse(access_token=token, user=UserPublic.model_validate(user))


@router.get(
    "/me",
    response_model=UserPublic,
    summary="Get current user profile",
    description="Returns the profile of the authenticated caller. Works for any valid token.",
)
def me(current_user: User = Depends(get_current_user)) -> User:
    return current_user


@router.post(
    "/token/verify",
    response_model=UserPublic,
    summary="Verify a token",
    description=(
        "Returns the user profile if the Bearer token is valid. "
        "Designed for Next.js middleware to verify session tokens without "
        "requiring the user to be fully approved (just authenticated)."
    ),
)
def verify_token(current_user: User = Depends(get_current_user)) -> User:
    return current_user


@router.post(
    "/admin/init",
    response_model=UserPublic,
    status_code=status.HTTP_201_CREATED,
    summary="Bootstrap the first super admin",
    description=(
        "**One-time endpoint.** Creates the initial super admin account with "
        "`APPROVED` status. Automatically disabled once any super admin exists. "
        "Call this immediately after first deployment."
    ),
)
def init_super_admin(
    body: SuperAdminInitRequest, db: Session = Depends(get_db)
) -> User:
    if db.query(User).filter(User.role == UserRole.SUPER_ADMIN).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A super admin already exists. Use the admin panel to manage users.",
        )
    if db.query(User).filter(User.email == body.email).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )
    admin = User(
        email=body.email,
        full_name=body.full_name.strip(),
        hashed_password=hash_password(body.password),
        role=UserRole.SUPER_ADMIN,
        status=UserStatus.APPROVED,
        approved_at=datetime.utcnow(),
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)
    return admin
