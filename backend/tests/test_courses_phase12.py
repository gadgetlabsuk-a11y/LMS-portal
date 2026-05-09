"""
Phase 12 tests — Course Identity & Structure.
Backend integration tests for COURSE-01, COURSE-02, COURSE-03, COURSE-05.
"""
import pytest
from unittest.mock import patch
from sse_starlette.sse import AppStatus


def test_create_course_with_identity(client, creator_token):
    """COURSE-01: POST /api/courses persists identity fields."""
    payload = {
        "title": "Python for Data Science",
        "description": "Learn Python fundamentals for data analysis.",
        "status": "draft",
        "audience_level": "beginner",
        "learning_objectives": ["Understand variables", "Write loops", "Use pandas"],
        "ai_tone_preset": "casual",
    }
    res = client.post(
        "/api/courses",
        json=payload,
        headers={"Authorization": f"Bearer {creator_token}"},
    )
    assert res.status_code == 201
    body = res.json()
    assert body["audience_level"] == "beginner"
    assert body["ai_tone_preset"] == "casual"
    # learning_objectives stored as JSON array
    assert isinstance(body.get("learning_objectives"), list)
    assert body["learning_objectives"] == ["Understand variables", "Write loops", "Use pandas"]


async def _mock_stream(*args, **kwargs):
    """Yields two tokens as a mock async generator."""
    for token in ["Hello", " world"]:
        yield token


def test_generate_description_sse(client, creator_token):
    """COURSE-02: POST /api/courses/ai/generate-description returns text/event-stream."""
    # Reset sse-starlette AppStatus so anyio.Event is re-created in the current event loop.
    AppStatus.should_exit_event = None
    with patch(
        "routers.courses.claude_service.stream_course_description",
        side_effect=lambda *a, **k: _mock_stream(*a, **k),
    ):
        res = client.post(
            "/api/courses/ai/generate-description",
            json={"topic": "Python basics", "tone_preset": "professional"},
            headers={"Authorization": f"Bearer {creator_token}"},
        )
    assert res.status_code == 200
    assert "text/event-stream" in res.headers.get("content-type", "")
    body = res.text
    assert "data:" in body


def test_generate_objectives_sse(client, creator_token):
    """COURSE-03: POST /api/courses/ai/generate-objectives returns text/event-stream."""
    # Reset sse-starlette AppStatus so anyio.Event is re-created in the current event loop.
    AppStatus.should_exit_event = None
    with patch(
        "routers.courses.claude_service.stream_learning_objectives",
        side_effect=lambda *a, **k: _mock_stream(*a, **k),
    ):
        res = client.post(
            "/api/courses/ai/generate-objectives",
            json={"course_title": "Python basics", "tone_preset": "professional"},
            headers={"Authorization": f"Bearer {creator_token}"},
        )
    assert res.status_code == 200
    assert "text/event-stream" in res.headers.get("content-type", "")
    body = res.text
    assert "data:" in body


def test_scaffold_structure(client, creator_token, creator_course):
    """COURSE-05: Scaffolding creates expected modules and videos in order."""
    course_id = creator_course.id

    # Create 2 modules
    modules = []
    for i in range(2):
        res = client.post(
            f"/api/courses/{course_id}/modules",
            json={"title": f"Module {i + 1}", "status": "draft"},
            headers={"Authorization": f"Bearer {creator_token}"},
        )
        assert res.status_code == 201, f"Module {i+1} creation failed: {res.text}"
        modules.append(res.json())

    # Create 2 videos in each module
    for mod in modules:
        for j in range(2):
            res = client.post(
                f"/api/modules/{mod['id']}/videos",
                json={"title": f"Video {j + 1}", "status": "draft", "video_type": "slides"},
                headers={"Authorization": f"Bearer {creator_token}"},
            )
            assert res.status_code == 201, f"Video creation failed: {res.text}"

    # Verify modules exist with correct order
    list_res = client.get(
        f"/api/courses/{course_id}/modules",
        headers={"Authorization": f"Bearer {creator_token}"},
    )
    assert list_res.status_code == 200
    module_list = list_res.json()
    assert len(module_list) == 2
    assert module_list[0]["order_index"] < module_list[1]["order_index"]
