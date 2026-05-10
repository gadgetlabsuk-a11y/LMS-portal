"""
Phase 16 — Quiz Builder integration tests.
QUIZ-01 through QUIZ-08.
"""
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from main import app
from sse_starlette.sse import AppStatus

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_sse_state():
    AppStatus.should_exit_event = None
    yield


@pytest.fixture
def creator_quiz(creator_token, creator_course):
    """Create module → quiz chain for testing."""
    mod_res = client.post(
        f"/api/courses/{creator_course.id}/modules",
        json={"title": "Test Module", "order_index": 0},
        headers={"Authorization": f"Bearer {creator_token}"},
    )
    assert mod_res.status_code == 201
    module_id = mod_res.json()["id"]

    quiz_res = client.post(
        f"/api/modules/{module_id}/quizzes",
        json={"title": "Test Quiz"},
        headers={"Authorization": f"Bearer {creator_token}"},
    )
    assert quiz_res.status_code == 201
    return quiz_res.json()


def test_create_quiz_settings(creator_token, creator_quiz):
    """QUIZ-01: create quiz with pass_rate, attempts_allowed, show_feedback."""
    pytest.fail("QUIZ-01: not implemented")


def test_create_mcq_single_question(creator_token, creator_quiz):
    """QUIZ-02: create MCQ single-answer question with correct_answer as int index."""
    pytest.fail("QUIZ-02: not implemented")


def test_create_mcq_multi_question(creator_token, creator_quiz):
    """QUIZ-03: create MCQ multi-answer question with correct_answer as int array."""
    pytest.fail("QUIZ-03: not implemented")


def test_create_true_false_question(creator_token, creator_quiz):
    """QUIZ-04: create true/false question with correct_answer as 'True' or 'False' string."""
    pytest.fail("QUIZ-04: not implemented")


def test_create_short_answer_question(creator_token, creator_quiz):
    """QUIZ-05: create short answer question."""
    pytest.fail("QUIZ-05: not implemented")


def test_question_explanation(creator_token, creator_quiz):
    """QUIZ-06: explanation text saved and returned with question."""
    pytest.fail("QUIZ-06: not implemented")


def test_reorder_questions(creator_token, creator_quiz):
    """QUIZ-07: POST /api/quizzes/{quiz_id}/questions/reorder persists new order_index."""
    pytest.fail("QUIZ-07: not implemented")


def test_generate_questions_streams_tokens(creator_token, creator_quiz):
    """QUIZ-08: POST /api/quizzes/{quiz_id}/ai/generate-questions returns 200 SSE stream."""
    pytest.fail("QUIZ-08: not implemented")
