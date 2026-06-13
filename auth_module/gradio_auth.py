"""
auth_module/gradio_auth.py
--------------------------
Gradio-compatible auth callback.

Pass this function to `gr.mount_gradio_app(..., auth=gradio_auth)`.
Gradio will show a login form and call this with the submitted
username (treated as email) and password before granting access.

Only accounts with status=APPROVED are allowed in.
"""

from auth_module.database import SessionLocal
from auth_module.models import User, UserStatus
from auth_module.security import verify_password


def gradio_auth(email: str, password: str) -> bool:
    """Return True only when email/password match an APPROVED account."""
    db = SessionLocal()
    try:
        user = (
            db.query(User)
            .filter(
                User.email == email.strip().lower(),
                User.status == UserStatus.APPROVED,
            )
            .first()
        )
        if user is None:
            return False
        return verify_password(password, user.hashed_password)
    finally:
        db.close()
