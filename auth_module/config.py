"""
auth_module/config.py
---------------------
Central settings read from environment variables (with safe defaults).
All settings are prefixed with AUTH_ in the environment.

Environment variables:
  AUTH_JWT_SECRET              – HS256 signing secret (must change in production)
  AUTH_JWT_ALGORITHM           – JWT algorithm, default "HS256"
  AUTH_TOKEN_EXPIRE_MINUTES    – Token TTL in minutes, default 1440 (24 h)
  AUTH_DATABASE_URL            – SQLAlchemy database URL, default SQLite
"""

import os
from dataclasses import dataclass
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()  # idempotent; loads .env if present


@dataclass(frozen=True)
class Settings:
    jwt_secret_key: str
    jwt_algorithm: str
    access_token_expire_minutes: int
    database_url: str


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings(
        jwt_secret_key=os.getenv(
            "AUTH_JWT_SECRET", "CHANGE-THIS-SECRET-KEY-AT-LEAST-32-CHARS"
        ),
        jwt_algorithm=os.getenv("AUTH_JWT_ALGORITHM", "HS256"),
        access_token_expire_minutes=int(os.getenv("AUTH_TOKEN_EXPIRE_MINUTES", "1440")),
        database_url=os.getenv(
            "AUTH_DATABASE_URL", "sqlite:///./auth_module/auth.db"
        ),
    )
