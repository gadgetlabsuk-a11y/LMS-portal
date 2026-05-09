"""
Tests for Block CRUD and Quiz+Question CRUD+reorder routers.
"""
import pytest
from fastapi.testclient import TestClient

from models import Course, CourseStatus


# ---------------------------------------------------------------------------
# File-local fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def setup_hierarchy(client, creator_token, db, creator_user):
    """Build course → module → video → slide hierarchy. Returns dict with ids."""
    course = Course(title="Test Course", creator_id=creator_user.id, status=CourseStatus.DRAFT)
    db.add(course)
    db.commit()
    db.refresh(course)

    mod = client.post(
        f"/api/courses/{course.id}/modules",
        json={"title": "M1"},
        headers={"Authorization": f"Bearer {creator_token}"},
    )
    assert mod.status_code == 201

    vid = client.post(
        f"/api/modules/{mod.json()['id']}/videos",
        json={"title": "V1"},
        headers={"Authorization": f"Bearer {creator_token}"},
    )
    assert vid.status_code == 201

    sld = client.post(
        f"/api/videos/{vid.json()['id']}/slides",
        json={},
        headers={"Authorization": f"Bearer {creator_token}"},
    )
    assert sld.status_code == 201

    return {
        "course_id": course.id,
        "module_id": mod.json()["id"],
        "video_id": vid.json()["id"],
        "slide_id": sld.json()["id"],
    }


# ---------------------------------------------------------------------------
# Block tests
# ---------------------------------------------------------------------------

def test_create_block(client, creator_token, setup_hierarchy):
    slide_id = setup_hierarchy["slide_id"]
    resp = client.post(
        f"/api/slides/{slide_id}/blocks",
        json={"type": "text", "content": {"text": "Hello"}},
        headers={"Authorization": f"Bearer {creator_token}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert "id" in data
    assert data["type"] == "text"
    assert data["slide_id"] == slide_id


def test_list_blocks(client, creator_token, setup_hierarchy):
    slide_id = setup_hierarchy["slide_id"]
    # Create two blocks
    client.post(
        f"/api/slides/{slide_id}/blocks",
        json={"type": "text"},
        headers={"Authorization": f"Bearer {creator_token}"},
    )
    client.post(
        f"/api/slides/{slide_id}/blocks",
        json={"type": "image"},
        headers={"Authorization": f"Bearer {creator_token}"},
    )
    resp = client.get(
        f"/api/slides/{slide_id}/blocks",
        headers={"Authorization": f"Bearer {creator_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    assert all(b["slide_id"] == slide_id for b in data)


def test_update_block(client, creator_token, setup_hierarchy):
    slide_id = setup_hierarchy["slide_id"]
    create_resp = client.post(
        f"/api/slides/{slide_id}/blocks",
        json={"type": "text", "content": {"text": "Original"}},
        headers={"Authorization": f"Bearer {creator_token}"},
    )
    block_id = create_resp.json()["id"]

    resp = client.put(
        f"/api/blocks/{block_id}",
        json={"content": {"text": "Updated"}},
        headers={"Authorization": f"Bearer {creator_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["content"]["text"] == "Updated"


def test_delete_block(client, creator_token, setup_hierarchy):
    slide_id = setup_hierarchy["slide_id"]
    create_resp = client.post(
        f"/api/slides/{slide_id}/blocks",
        json={"type": "heading"},
        headers={"Authorization": f"Bearer {creator_token}"},
    )
    block_id = create_resp.json()["id"]

    del_resp = client.delete(
        f"/api/blocks/{block_id}",
        headers={"Authorization": f"Bearer {creator_token}"},
    )
    assert del_resp.status_code == 200
    assert del_resp.json() == {"message": "Block deleted"}

    # Subsequent GET returns 404
    get_resp = client.get(
        f"/api/blocks/{block_id}",
        headers={"Authorization": f"Bearer {creator_token}"},
    )
    assert get_resp.status_code == 404


def test_trainee_cannot_create_block(client, trainee_token, setup_hierarchy):
    slide_id = setup_hierarchy["slide_id"]
    resp = client.post(
        f"/api/slides/{slide_id}/blocks",
        json={"type": "text"},
        headers={"Authorization": f"Bearer {trainee_token}"},
    )
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Quiz tests
# ---------------------------------------------------------------------------

def test_create_quiz(client, creator_token, setup_hierarchy):
    module_id = setup_hierarchy["module_id"]
    resp = client.post(
        f"/api/modules/{module_id}/quizzes",
        json={"title": "Knowledge Check 1"},
        headers={"Authorization": f"Bearer {creator_token}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert "id" in data
    assert data["pass_rate"] == 80
    assert data["module_id"] == module_id


def test_update_quiz_pass_rate(client, creator_token, setup_hierarchy):
    module_id = setup_hierarchy["module_id"]
    create_resp = client.post(
        f"/api/modules/{module_id}/quizzes",
        json={"title": "Q1"},
        headers={"Authorization": f"Bearer {creator_token}"},
    )
    quiz_id = create_resp.json()["id"]

    resp = client.put(
        f"/api/quizzes/{quiz_id}",
        json={"pass_rate": 70},
        headers={"Authorization": f"Bearer {creator_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["pass_rate"] == 70


def test_delete_quiz(client, creator_token, setup_hierarchy):
    module_id = setup_hierarchy["module_id"]
    create_resp = client.post(
        f"/api/modules/{module_id}/quizzes",
        json={"title": "Q to delete"},
        headers={"Authorization": f"Bearer {creator_token}"},
    )
    quiz_id = create_resp.json()["id"]

    # Add a question so cascade is exercised
    client.post(
        f"/api/quizzes/{quiz_id}/questions",
        json={"type": "multiple_choice", "prompt": "Q1?"},
        headers={"Authorization": f"Bearer {creator_token}"},
    )

    del_resp = client.delete(
        f"/api/quizzes/{quiz_id}",
        headers={"Authorization": f"Bearer {creator_token}"},
    )
    assert del_resp.status_code == 200
    assert del_resp.json() == {"message": "Quiz deleted"}


def test_trainee_cannot_create_quiz(client, trainee_token, setup_hierarchy):
    module_id = setup_hierarchy["module_id"]
    resp = client.post(
        f"/api/modules/{module_id}/quizzes",
        json={"title": "Attempt"},
        headers={"Authorization": f"Bearer {trainee_token}"},
    )
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Question tests
# ---------------------------------------------------------------------------

def _create_quiz(client, creator_token, module_id):
    resp = client.post(
        f"/api/modules/{module_id}/quizzes",
        json={"title": "Test Quiz"},
        headers={"Authorization": f"Bearer {creator_token}"},
    )
    assert resp.status_code == 201
    return resp.json()["id"]


def test_create_question(client, creator_token, setup_hierarchy):
    quiz_id = _create_quiz(client, creator_token, setup_hierarchy["module_id"])
    resp = client.post(
        f"/api/quizzes/{quiz_id}/questions",
        json={"type": "multiple_choice", "prompt": "What is 2+2?"},
        headers={"Authorization": f"Bearer {creator_token}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert "id" in data
    assert data["type"] == "multiple_choice"
    assert data["prompt"] == "What is 2+2?"


def test_list_questions(client, creator_token, setup_hierarchy):
    quiz_id = _create_quiz(client, creator_token, setup_hierarchy["module_id"])
    for i in range(3):
        client.post(
            f"/api/quizzes/{quiz_id}/questions",
            json={"type": "true_false", "prompt": f"Question {i}"},
            headers={"Authorization": f"Bearer {creator_token}"},
        )
    resp = client.get(
        f"/api/quizzes/{quiz_id}/questions",
        headers={"Authorization": f"Bearer {creator_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 3
    # Verify ordered by order_index
    indices = [q["order_index"] for q in data]
    assert indices == sorted(indices)


def test_update_question(client, creator_token, setup_hierarchy):
    quiz_id = _create_quiz(client, creator_token, setup_hierarchy["module_id"])
    create_resp = client.post(
        f"/api/quizzes/{quiz_id}/questions",
        json={"type": "multiple_choice", "prompt": "Original prompt"},
        headers={"Authorization": f"Bearer {creator_token}"},
    )
    question_id = create_resp.json()["id"]

    resp = client.put(
        f"/api/questions/{question_id}",
        json={"prompt": "Updated prompt"},
        headers={"Authorization": f"Bearer {creator_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["prompt"] == "Updated prompt"


def test_delete_question(client, creator_token, setup_hierarchy):
    quiz_id = _create_quiz(client, creator_token, setup_hierarchy["module_id"])
    create_resp = client.post(
        f"/api/quizzes/{quiz_id}/questions",
        json={"type": "multiple_choice", "prompt": "To delete"},
        headers={"Authorization": f"Bearer {creator_token}"},
    )
    question_id = create_resp.json()["id"]

    del_resp = client.delete(
        f"/api/questions/{question_id}",
        headers={"Authorization": f"Bearer {creator_token}"},
    )
    assert del_resp.status_code == 200
    assert del_resp.json() == {"message": "Question deleted"}


def test_reorder_questions(client, creator_token, setup_hierarchy):
    quiz_id = _create_quiz(client, creator_token, setup_hierarchy["module_id"])

    # Create 3 questions
    ids = []
    for i in range(3):
        resp = client.post(
            f"/api/quizzes/{quiz_id}/questions",
            json={"type": "multiple_choice", "prompt": f"Q{i}"},
            headers={"Authorization": f"Bearer {creator_token}"},
        )
        ids.append(resp.json()["id"])

    # Reorder in reverse
    reversed_ids = list(reversed(ids))
    reorder_resp = client.post(
        f"/api/quizzes/{quiz_id}/questions/reorder",
        json={"question_ids": reversed_ids},
        headers={"Authorization": f"Bearer {creator_token}"},
    )
    assert reorder_resp.status_code == 200

    # Verify new order
    list_resp = client.get(
        f"/api/quizzes/{quiz_id}/questions",
        headers={"Authorization": f"Bearer {creator_token}"},
    )
    new_order_ids = [q["id"] for q in list_resp.json()]
    assert new_order_ids == reversed_ids
