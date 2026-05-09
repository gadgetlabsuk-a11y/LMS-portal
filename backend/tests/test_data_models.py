"""
Schema smoke tests for Phase 10 Data Models.
These tests verify that new tables exist with the correct columns.
All tests use a fresh in-memory SQLite DB created via Base.metadata.create_all().
Alembic is NOT used in tests — create_all() is the test-environment source of truth.
"""
import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from models import Base


@pytest.fixture(scope="module")
def test_engine():
    """Create an in-memory SQLite DB with all models for this test module."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    yield engine
    engine.dispose()


@pytest.fixture(scope="module")
def inspector(test_engine):
    return inspect(test_engine)


# ── DATA-01: Module table ──────────────────────────────────────────────────
def test_module_table_exists(inspector):
    assert "modules" in inspector.get_table_names(), "modules table missing"


def test_module_required_columns(inspector):
    cols = {c["name"] for c in inspector.get_columns("modules")}
    required = {
        "id", "course_id", "order_index", "title", "description",
        "learning_objectives", "estimated_duration_minutes", "pass_rate_override",
        "unlock_rule", "unlock_days_after_enrolment", "status",
        "created_at", "updated_at",
    }
    missing = required - cols
    assert not missing, f"modules table missing columns: {missing}"


# ── DATA-02: Video table ───────────────────────────────────────────────────
def test_video_table_exists(inspector):
    assert "videos" in inspector.get_table_names(), "videos table missing"


def test_video_required_columns(inspector):
    cols = {c["name"] for c in inspector.get_columns("videos")}
    required = {
        "id", "module_id", "order_index", "title", "description",
        "video_type", "estimated_duration_seconds", "narration_voice_id",
        "source_video_url", "status", "created_at", "updated_at",
    }
    missing = required - cols
    assert not missing, f"videos table missing columns: {missing}"


# ── DATA-03: Slide table ───────────────────────────────────────────────────
def test_slide_table_exists(inspector):
    assert "slides" in inspector.get_table_names(), "slides table missing"


def test_slide_required_columns(inspector):
    cols = {c["name"] for c in inspector.get_columns("slides")}
    required = {
        "id", "video_id", "order_index", "layout_id", "duration_seconds",
        "narration_script", "narration_audio_url", "narration_script_hash",
        "transition", "status", "created_at", "updated_at",
    }
    missing = required - cols
    assert not missing, f"slides table missing columns: {missing}"


# ── DATA-04: Block table ───────────────────────────────────────────────────
def test_block_table_exists(inspector):
    assert "blocks" in inspector.get_table_names(), "blocks table missing"


def test_block_required_columns(inspector):
    cols = {c["name"] for c in inspector.get_columns("blocks")}
    required = {
        "id", "slide_id", "order_index", "type", "content",
        "style", "alt_text", "grid_position", "created_at", "updated_at",
    }
    missing = required - cols
    assert not missing, f"blocks table missing columns: {missing}"


# ── DATA-05: Quiz table ────────────────────────────────────────────────────
def test_quiz_table_exists(inspector):
    assert "quizzes" in inspector.get_table_names(), "quizzes table missing"


def test_quiz_required_columns(inspector):
    cols = {c["name"] for c in inspector.get_columns("quizzes")}
    required = {
        "id", "module_id", "video_id", "order_index", "title", "description",
        "quiz_type", "pass_rate", "attempts_allowed", "time_limit_seconds",
        "shuffle_questions", "show_feedback", "on_fail_action",
        "status", "created_at", "updated_at",
    }
    missing = required - cols
    assert not missing, f"quizzes table missing columns: {missing}"


# ── DATA-06: Question table ────────────────────────────────────────────────
def test_question_table_exists(inspector):
    assert "questions" in inspector.get_table_names(), "questions table missing"


def test_question_required_columns(inspector):
    cols = {c["name"] for c in inspector.get_columns("questions")}
    required = {
        "id", "quiz_id", "order_index", "type", "prompt", "points",
        "explanation", "options", "correct_answer",
        "linked_objective_id", "difficulty", "created_at", "updated_at",
    }
    missing = required - cols
    assert not missing, f"questions table missing columns: {missing}"


# ── DATA-07: Resource table ────────────────────────────────────────────────
def test_resource_table_exists(inspector):
    assert "resources" in inspector.get_table_names(), "resources table missing"


def test_resource_required_columns(inspector):
    cols = {c["name"] for c in inspector.get_columns("resources")}
    required = {
        "id", "module_id", "type", "title", "url_or_file",
        "visible_to_learner", "created_at",
    }
    missing = required - cols
    assert not missing, f"resources table missing columns: {missing}"


# ── DATA-08: Alembic migrations infrastructure ────────────────────────────
def test_alembic_ini_exists():
    """alembic.ini must exist in backend/"""
    backend_dir = os.path.dirname(os.path.dirname(__file__))
    assert os.path.isfile(os.path.join(backend_dir, "alembic.ini")), \
        "alembic.ini missing from backend/"


def test_alembic_env_imports_base():
    """alembic/env.py must reference Base.metadata"""
    backend_dir = os.path.dirname(os.path.dirname(__file__))
    env_path = os.path.join(backend_dir, "alembic", "env.py")
    assert os.path.isfile(env_path), "alembic/env.py missing"
    content = open(env_path).read()
    assert "target_metadata = Base.metadata" in content, \
        "alembic/env.py must set target_metadata = Base.metadata"


# ── DATA-09: Course.content column absent after migration ─────────────────
def test_content_column_absent(inspector):
    """Course.content column must NOT exist — it is retired in Phase 10."""
    cols = {c["name"] for c in inspector.get_columns("courses")}
    assert "content" not in cols, \
        "courses.content column still present — data migration not complete"


def test_course_new_columns_exist(inspector):
    """Courses table must have the new columns added in migration 001."""
    cols = {c["name"] for c in inspector.get_columns("courses")}
    required = {
        "slug", "summary", "thumbnail_url", "audience_level",
        "learning_objectives", "ai_tone_preset", "version", "published_at",
    }
    missing = required - cols
    assert not missing, f"courses table missing new columns: {missing}"
