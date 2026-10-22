import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from sqlalchemy.orm import DeclarativeBase, sessionmaker

# Values come from the repo-root .env (git-ignored). Real environment variables win.
load_dotenv(Path(__file__).resolve().parents[2] / ".env")


def get_database_url() -> str | URL:
    """Pick the database from the environment.

    1. DATABASE_URL, if set (any SQLAlchemy URL).
    2. PGHOST/PGUSER/PGPASSWORD/PGDATABASE -> PostgreSQL. The URL is built with URL.create so
       special characters in the password (@ : / #) are encoded correctly. Azure requires TLS.
    3. Otherwise a local SQLite file (Day 1).
    """
    if url := os.environ.get("DATABASE_URL"):
        return url
    if host := os.environ.get("PGHOST"):
        return URL.create(
            "postgresql+psycopg",
            username=os.environ.get("PGUSER"),
            password=os.environ.get("PGPASSWORD"),
            host=host,
            port=int(os.environ.get("PGPORT", "5432")),
            database=os.environ.get("PGDATABASE", "postgres"),
            query={"sslmode": os.environ.get("PGSSLMODE", "require")},
        )
    return "sqlite:///./caredesk.db"


DATABASE_URL = get_database_url()
_is_sqlite = str(DATABASE_URL).startswith("sqlite")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if _is_sqlite else {},
    pool_pre_ping=True,
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
