"""Pytest fixtures shared across all backend tests."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

# Change to backend/ dir so relative imports work the same as the app
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# --- Patch: bcrypt 5.0 raises ValueError for passwords > 72 bytes, which breaks
# passlib's detect_wrap_bug() self-test during backend initialisation.
# The "wrap bug" only affects bcrypt versions prior to ~2012 — not relevant here.
# Patch before any passlib import so the backend initialises cleanly.
try:
    import passlib.handlers.bcrypt as _pb  # noqa: E402
    _pb.detect_wrap_bug = lambda *args, **kwargs: False
except Exception:
    pass  # passlib not installed; will fail later with a clearer error

from database import get_db
from main import app
from models import Base, User, UserRole, Course, CourseStatus
from services.auth_service import AuthService

TEST_DB_URL = "sqlite:///./test_lms_tmp.db"

test_engine = create_engine(
    TEST_DB_URL,
    connect_args={"check_same_thread": False},
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def setup_test_db():
    """Create all tables before each test, drop after.

    Sets override_get_db as fallback for tests that don't use the `db` fixture.
    Tests that DO use the `db` fixture will have override_get_db replaced with
    a same-connection override inside that fixture.

    drop_all before create_all ensures idempotency when a previous test's
    rollback-based `db` fixture left tables in place (e.g. under randomised
    test ordering via pytest-randomly).
    """
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)
    app.dependency_overrides[get_db] = override_get_db
    yield
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def client():
    return TestClient(app, raise_server_exceptions=True)


@pytest.fixture
def db():
    """Per-test DB session. All writes are rolled back at teardown.

    Uses a connection-level outer transaction + SAVEPOINT so that even
    explicit db.commit() calls inside fixtures are undone after each test.
    This prevents state bleed between tests when pytest randomises order.

    Also overrides the FastAPI get_db dependency to use the SAME connection,
    so TestClient API calls and direct db queries share the same transaction
    scope — ensuring committed rows are visible across both within one test.

    Note: Session(bind=connection) is deprecated in SA 2.0 but still
    functional — removal is planned for SA 2.1. Suppress the warning with
    filterwarnings if needed.
    """
    connection = test_engine.connect()
    outer_tx = connection.begin()
    nested = connection.begin_nested()  # SAVEPOINT
    session = TestingSessionLocal(bind=connection)

    @event.listens_for(session, "after_transaction_end")
    def restart_savepoint(session, transaction):
        """Re-open SAVEPOINT after each commit so the outer rollback still works."""
        nonlocal nested
        if transaction.nested and not transaction._parent.nested:
            nested = connection.begin_nested()

    # Override the FastAPI dependency to use the SAME connection so that
    # TestClient API calls see rows committed by direct db writes in the test.
    def override():
        yield session

    app.dependency_overrides[get_db] = override

    yield session

    session.close()
    outer_tx.rollback()
    connection.close()


@pytest.fixture
def admin_user(db):
    user = User(
        username="admin_test",
        email="admin_test@example.com",
        hashed_password=AuthService.hash_password("pass123"),
        role=UserRole.ADMIN,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def trainee_user(db):
    user = User(
        username="trainee_test",
        email="trainee_test@example.com",
        hashed_password=AuthService.hash_password("pass123"),
        role=UserRole.TRAINEE,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def trainee_token(trainee_user):
    """JWT token for the trainee — created directly, no login endpoint DB writes."""
    return AuthService.create_access_token(
        user_id=trainee_user.id,
        username=trainee_user.username,
        role=trainee_user.role.value,
    )


@pytest.fixture
def published_course(db, admin_user):
    course = Course(
        title="Python Basics",
        description="Learn Python from scratch.",
        status=CourseStatus.PUBLISHED,
        creator_id=admin_user.id,
    )
    db.add(course)
    db.commit()
    db.refresh(course)
    return course


@pytest.fixture
def draft_course(db, admin_user):
    course = Course(
        title="Draft Course",
        description="Not published yet.",
        status=CourseStatus.DRAFT,
        creator_id=admin_user.id,
    )
    db.add(course)
    db.commit()
    db.refresh(course)
    return course


@pytest.fixture
def creator_user(db):
    user = User(
        username="creator_test",
        email="creator_test@example.com",
        hashed_password=AuthService.hash_password("pass123"),
        role=UserRole.CREATOR,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def creator_token(creator_user):
    """JWT token for the creator — created directly, no login endpoint DB writes."""
    return AuthService.create_access_token(
        user_id=creator_user.id,
        username=creator_user.username,
        role=creator_user.role.value,
    )


@pytest.fixture
def admin_token(admin_user):
    """JWT token for the admin — created directly, no login endpoint DB writes."""
    return AuthService.create_access_token(
        user_id=admin_user.id,
        username=admin_user.username,
        role=admin_user.role.value,
    )


@pytest.fixture
def creator_course(db, creator_user):
    course = Course(
        title="Creator's Python Course",
        description="A course by the creator.",
        status=CourseStatus.PUBLISHED,
        creator_id=creator_user.id,
    )
    db.add(course)
    db.commit()
    db.refresh(course)
    return course
