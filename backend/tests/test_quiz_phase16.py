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
    """QUIZ-01: update pass_rate, attempts_allowed, show_feedback."""
    res = client.put(
        f"/api/quizzes/{creator_quiz['id']}",
        json={"pass_rate": 70, "attempts_allowed": 2, "show_feedback": "on_completion"},
        headers={"Authorization": f"Bearer {creator_token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["pass_rate"] == 70
    assert data["attempts_allowed"] == 2
    assert data["show_feedback"] == "on_completion"


def test_create_mcq_single_question(creator_token, creator_quiz):
    """QUIZ-02: create MCQ single question — correct_answer is int index."""
    res = client.post(
        f"/api/quizzes/{creator_quiz['id']}/questions",
        json={
            "type": "mcq_single",
            "prompt": "Which is a programming language?",
            "options": ["Python", "HTML", "CSS"],
            "correct_answer": 0,
        },
        headers={"Authorization": f"Bearer {creator_token}"},
    )
    assert res.status_code == 201
    data = res.json()
    assert data["type"] == "mcq_single"
    assert data["correct_answer"] == 0


def test_create_mcq_multi_question(creator_token, creator_quiz):
    """QUIZ-03: create MCQ multi question — correct_answer is int array."""
    res = client.post(
        f"/api/quizzes/{creator_quiz['id']}/questions",
        json={
            "type": "mcq_multi",
            "prompt": "Which are programming languages?",
            "options": ["Python", "HTML", "JavaScript", "CSS"],
            "correct_answer": [0, 2],
        },
        headers={"Authorization": f"Bearer {creator_token}"},
    )
    assert res.status_code == 201
    data = res.json()
    assert data["type"] == "mcq_multi"
    assert data["correct_answer"] == [0, 2]


def test_create_true_false_question(creator_token, creator_quiz):
    """QUIZ-04: create true/false question — correct_answer is 'True' or 'False' string."""
    res = client.post(
        f"/api/quizzes/{creator_quiz['id']}/questions",
        json={
            "type": "true_false",
            "prompt": "Python is a programming language.",
            "options": ["True", "False"],
            "correct_answer": "True",
        },
        headers={"Authorization": f"Bearer {creator_token}"},
    )
    assert res.status_code == 201
    data = res.json()
    assert data["type"] == "true_false"
    assert data["correct_answer"] == "True"


def test_create_short_answer_question(creator_token, creator_quiz):
    """QUIZ-05: create short answer question — correct_answer is string or null."""
    res = client.post(
        f"/api/quizzes/{creator_quiz['id']}/questions",
        json={
            "type": "short_answer",
            "prompt": "What does HTTP stand for?",
            "correct_answer": "HyperText Transfer Protocol",
        },
        headers={"Authorization": f"Bearer {creator_token}"},
    )
    assert res.status_code == 201
    data = res.json()
    assert data["type"] == "short_answer"
    assert "HyperText" in (data["correct_answer"] or "")


def test_question_explanation(creator_token, creator_quiz):
    """QUIZ-06: explanation text saved and returned with question."""
    res = client.post(
        f"/api/quizzes/{creator_quiz['id']}/questions",
        json={
            "type": "mcq_single",
            "prompt": "Test question?",
            "options": ["A", "B"],
            "correct_answer": 0,
            "explanation": "Because A is correct.",
        },
        headers={"Authorization": f"Bearer {creator_token}"},
    )
    assert res.status_code == 201
    data = res.json()
    assert data["explanation"] == "Because A is correct."


def test_reorder_questions(creator_token, creator_quiz):
    """QUIZ-07: POST /api/quizzes/{quiz_id}/questions/reorder persists new order_index."""
    pytest.fail("QUIZ-07: not implemented")


def test_generate_questions_streams_tokens(creator_token, creator_quiz):
    """QUIZ-08: POST /api/quizzes/{quiz_id}/ai/generate-questions returns 200 SSE."""
    AppStatus.should_exit_event = None

    mock_tokens = ['[', '{"type":"mcq_single","prompt":"What is Python?","options":["A lang","A snake"],"correct_answer":0,"explanation":"Python is a programming language."}', ']']

    async def mock_stream(prompt):
        for token in mock_tokens:
            yield token

    with patch("routers.quizzes.claude_service._stream_text", side_effect=mock_stream):
        res = client.post(
            f"/api/quizzes/{creator_quiz['id']}/ai/generate-questions",
            json={"count": 1, "tone_preset": "professional"},
            headers={"Authorization": f"Bearer {creator_token}"},
        )
    assert res.status_code == 200
    assert "data:" in res.text


def test_generate_questions_requires_auth(creator_quiz):
    """QUIZ-08: unauthenticated request is rejected."""
    res = client.post(
        f"/api/quizzes/{creator_quiz['id']}/ai/generate-questions",
        json={"count": 1},
    )
    assert res.status_code in (401, 403)
