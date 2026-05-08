"""Pytest fixtures shared across all backend tests."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Change to backend/ dir so relative imports work the same as the app
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

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
    """Create all tables before each test, drop after."""
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
    db = TestingSessionLocal()
    yield db
    db.close()


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
        content={"modules": [{"title": "Intro", "lessons": [{"title": "Hello World"}]}]},
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
        content=None,
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
        content={"modules": [{"title": "Module 1", "lessons": [{"title": "Lesson 1"}]}]},
    )
    db.add(course)
    db.commit()
    db.refresh(course)
    return course
