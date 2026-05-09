"""
Phase 14 — SLIDE-11 and SLIDE-12 integration tests.
POST /api/slides/{slide_id}/ai/generate-narration
POST /api/slides/{slide_id}/ai/generate-outline
"""
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from main import app
from sse_starlette.sse import AppStatus

client = TestClient(app)


@pytest.fixture
def creator_slide(creator_token, creator_course, db):
    """Create video → slide chain for testing."""
    video_res = client.post(
        f"/api/courses/{creator_course.id}/modules",
        json={"title": "Test Module", "order_index": 0},
        headers={"Authorization": f"Bearer {creator_token}"},
    )
    assert video_res.status_code == 201
    module_id = video_res.json()["id"]

    vid_res = client.post(
        f"/api/modules/{module_id}/videos",
        json={"title": "Test Video", "order_index": 0, "video_type": "slideshow_narrated"},
        headers={"Authorization": f"Bearer {creator_token}"},
    )
    assert vid_res.status_code == 201
    video_id = vid_res.json()["id"]

    slide_res = client.post(
        f"/api/videos/{video_id}/slides",
        json={"title": "Test Slide", "order_index": 0},
        headers={"Authorization": f"Bearer {creator_token}"},
    )
    assert slide_res.status_code == 201
    return slide_res.json()


# ---------------------------------------------------------------------------
# SLIDE-11: POST /api/slides/{slide_id}/ai/generate-narration
# ---------------------------------------------------------------------------

def test_generate_narration_streams_tokens(creator_token, creator_slide):
    """POST /api/slides/{id}/ai/generate-narration returns 200 with SSE stream."""
    AppStatus.should_exit_event = None

    mock_tokens = ["Here ", "is ", "the ", "narration."]

    async def mock_stream(prompt):
        for token in mock_tokens:
            yield token

    with patch("routers.slides.claude_service._stream_text", side_effect=mock_stream):
        res = client.post(
            f"/api/slides/{creator_slide['id']}/ai/generate-narration",
            json={"tone_preset": "professional"},
            headers={"Authorization": f"Bearer {creator_token}"},
        )

    assert res.status_code == 200
    assert "data:" in res.text


def test_generate_narration_requires_auth(creator_slide):
    """POST without auth token returns 401 or 403."""
    AppStatus.should_exit_event = None
    res = client.post(
        f"/api/slides/{creator_slide['id']}/ai/generate-narration",
        json={"tone_preset": "professional"},
    )
    assert res.status_code in (401, 403)


def test_generate_narration_404_for_unknown_slide(creator_token):
    """POST with unknown slide_id returns 404."""
    AppStatus.should_exit_event = None
    res = client.post(
        "/api/slides/999999/ai/generate-narration",
        json={"tone_preset": "professional"},
        headers={"Authorization": f"Bearer {creator_token}"},
    )
    assert res.status_code == 404


# ---------------------------------------------------------------------------
# SLIDE-12: POST /api/slides/{slide_id}/ai/generate-outline
# ---------------------------------------------------------------------------

def test_generate_outline_streams_json(creator_token, creator_slide):
    """POST /api/slides/{id}/ai/generate-outline returns 200 with SSE stream."""
    AppStatus.should_exit_event = None

    mock_tokens = ["[", '{"title":', '"Slide 1"', "}]"]

    async def mock_stream(prompt):
        for token in mock_tokens:
            yield token

    with patch("routers.slides.claude_service._stream_text", side_effect=mock_stream):
        res = client.post(
            f"/api/slides/{creator_slide['id']}/ai/generate-outline",
            json={"prompt": "Intro to Python", "slide_count": 3},
            headers={"Authorization": f"Bearer {creator_token}"},
        )

    assert res.status_code == 200
    assert "data:" in res.text


def test_generate_outline_requires_auth(creator_slide):
    """POST without auth token returns 401 or 403."""
    AppStatus.should_exit_event = None
    res = client.post(
        f"/api/slides/{creator_slide['id']}/ai/generate-outline",
        json={"prompt": "test"},
    )
    assert res.status_code in (401, 403)
