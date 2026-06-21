"""
auth_module/database.py
-----------------------
SQLAlchemy engine and session factory.

Usage in FastAPI routes:
    from auth_module.database import get_db
    def my_endpoint(db: Session = Depends(get_db)):
        ...
"""

from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from auth_module.config import get_settings


def _make_engine():
    settings = get_settings()
    kwargs: dict = {}
    if "sqlite" in settings.database_url:
        # Required for SQLite when FastAPI uses threads
        kwargs["connect_args"] = {"check_same_thread": False}
    return create_engine(settings.database_url, **kwargs)


engine = _make_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def create_tables() -> None:
    """Create all tables that don't exist yet and log their status. Safe to call multiple times."""
    from sqlalchemy import inspect
    from auth_module.models import Base  # local import avoids circular deps at module load

    existing = set(inspect(engine).get_table_names())
    Base.metadata.create_all(bind=engine)
    after = set(inspect(engine).get_table_names())

    for table in sorted(Base.metadata.tables):
        status = "created" if table not in existing else "ok"
        print(f"  [db] {table}: {status}")

    missing = set(Base.metadata.tables) - after
    if missing:
        raise RuntimeError(f"[db] Tables failed to create: {missing}")


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a DB session and ensures it is closed."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
