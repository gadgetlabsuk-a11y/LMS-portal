"""
Database configuration and session management.
Sets up SQLAlchemy with SQLite and provides database utilities.
"""

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker, Session
from config import settings
import logging

logger = logging.getLogger(__name__)

# Create engine with SQLite.
# QueuePool (the default) allows multiple connections so concurrent requests
# don't block on a single shared connection (StaticPool was the old setting).
# pool_timeout: wait up to 30 s for a free connection before raising.
# pool_size / max_overflow: up to 20 simultaneous connections.
engine = create_engine(
    settings.DB_URL,
    connect_args={
        "check_same_thread": False,
        "timeout": 30,          # wait up to 30 s on a locked SQLite file
    },
    pool_size=10,
    max_overflow=10,
    pool_timeout=30,
    pool_pre_ping=True,         # drop stale connections automatically
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
    """Configure SQLite for concurrent access."""
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    # WAL mode lets readers and writers work concurrently instead of blocking
    cursor.execute("PRAGMA journal_mode=WAL")
    # Give write operations a bit of breathing room before returning SQLITE_BUSY
    cursor.execute("PRAGMA busy_timeout=5000")
    cursor.close()


def init_db():
    """
    Initialize database by creating all tables.
    Call this on application startup.
    """
    from models import Base

    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created successfully")
