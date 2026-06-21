#!/usr/bin/env python3
"""
scripts/seed_admin.py
---------------------
Create or reset a super-admin account directly in the database.

Usage
-----
  # Interactive (prompts for all values):
  python scripts/seed_admin.py

  # Non-interactive (CI / Docker entrypoint):
  python scripts/seed_admin.py --email admin@example.com --name "Admin" --password secret

  # Force-reset an existing super-admin's password / name:
  python scripts/seed_admin.py --email admin@example.com --name "Admin" --password newpass --force
"""

import argparse
import getpass
import sys
from datetime import datetime, timezone
from pathlib import Path

# ── Make sure imports resolve from the project root ───────────────
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

from auth_module.database import SessionLocal, create_tables
from auth_module.models import User, UserRole, UserStatus
from auth_module.security import hash_password, is_valid_email

# ── ANSI colours ──────────────────────────────────────────────────
GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
RESET  = "\033[0m"

def ok(msg: str)   -> None: print(f"{GREEN}  ✓  {msg}{RESET}")
def warn(msg: str) -> None: print(f"{YELLOW}  !  {msg}{RESET}")
def err(msg: str)  -> None: print(f"{RED}  ✗  {msg}{RESET}"); sys.exit(1)


# ── CLI args ──────────────────────────────────────────────────────
def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Seed a super-admin account into the auth database.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument("--email",    help="Admin email address")
    p.add_argument("--name",     help="Admin full name")
    p.add_argument("--password", help="Admin password (omit to be prompted securely)")
    p.add_argument(
        "--force",
        action="store_true",
        help="Update name/password if this email already exists as super-admin",
    )
    return p.parse_args()


# ── Prompt helpers ────────────────────────────────────────────────
def prompt_email() -> str:
    while True:
        value = input("  Email: ").strip()
        if is_valid_email(value):
            return value
        warn("Invalid email format, try again.")


def prompt_name() -> str:
    while True:
        value = input("  Full name: ").strip()
        if value:
            return value
        warn("Name cannot be empty.")


def prompt_password() -> str:
    while True:
        pw = getpass.getpass("  Password: ")
        if len(pw) < 8:
            warn("Password must be at least 8 characters.")
            continue
        confirm = getpass.getpass("  Confirm password: ")
        if pw != confirm:
            warn("Passwords do not match, try again.")
            continue
        return pw


# ── Main ──────────────────────────────────────────────────────────
def main() -> None:
    args = parse_args()

    print()
    print("  Radixweb — Admin Seeder")
    print("  " + "─" * 36)

    # Collect missing values interactively
    email    = args.email    or prompt_email()
    name     = args.name     or prompt_name()
    password = args.password or prompt_password()

    # Validate
    if not is_valid_email(email):
        err(f"Invalid email: {email}")
    if len(password) < 8:
        err("Password must be at least 8 characters.")

    # Ensure tables exist
    create_tables()

    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.email == email).first()

        if existing:
            if existing.role != UserRole.SUPER_ADMIN:
                err(
                    f"A non-admin account with email '{email}' already exists "
                    f"(role={existing.role.value}). Use a different email."
                )
            if not args.force:
                err(
                    f"Super-admin '{email}' already exists. "
                    "Use --force to update their name/password."
                )
            # --force: update in-place
            existing.full_name       = name.strip()
            existing.hashed_password = hash_password(password)
            existing.status          = UserStatus.APPROVED
            db.commit()
            db.refresh(existing)
            warn(f"Existing super-admin updated  →  id={existing.id}  email={existing.email}")

        else:
            # Check whether any super-admin exists (different email)
            other_admin = db.query(User).filter(User.role == UserRole.SUPER_ADMIN).first()
            if other_admin:
                warn(
                    f"Another super-admin already exists (email={other_admin.email}). "
                    "Creating a second one."
                )

            admin = User(
                email=email,
                full_name=name.strip(),
                hashed_password=hash_password(password),
                role=UserRole.SUPER_ADMIN,
                status=UserStatus.APPROVED,
                approved_at=datetime.now(timezone.utc),
                upload_access=True,
            )
            db.add(admin)
            db.commit()
            db.refresh(admin)
            ok(f"Super-admin created  →  id={admin.id}  email={admin.email}")

        print()
        ok("Done. You can now log in via POST /auth/login.")
        print()

    finally:
        db.close()


if __name__ == "__main__":
    main()
