"""Database session scaffold using SQLAlchemy."""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from app.core.config import settings

# SQLAlchemy base class for ORM models.
Base = declarative_base()

# Engine configured from environment settings.
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    echo=settings.sqlalchemy_echo,
    future=True,
)

# Factory for database sessions.
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    class_=Session,
    future=True,
)


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency that yields a DB session and ensures cleanup.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
