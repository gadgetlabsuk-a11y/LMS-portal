"""
Database configuration and session management.
Sets up SQLAlchemy with SQLite and provides database utilities.
"""

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from config import settings
import logging

logger = logging.getLogger(__name__)

# Create engine with SQLite
engine = create_engine(
    settings.DB_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    echo=settings.SQLALCHEMY_ECHO,
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Session:
    """
    Dependency function to get database session.
    Yields a session and ensures it's closed after use.
    """
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        db.rollback()
        logger.error(f"Database session error: {str(e)}")
        raise
    finally:
        db.close()


@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_conn, connection_record):
    """Enable foreign key constraints in SQLite."""
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def init_db():
    """
    Initialize database by creating all tables.
    Call this on application startup.
    """
    from models import Base

    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created successfully")
