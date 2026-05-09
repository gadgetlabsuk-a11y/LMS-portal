"""
Phase 13 — BUILD-05 integration tests for POST /api/modules/:id/ai/generate-description.
"""
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from main import app
from sse_starlette.sse import AppStatus

client = TestClient(app)


@pytest.fixture
def creator_module(creator_token, creator_course, db):
    """Create a module for testing via the API."""
    res = client.post(
        f"/api/courses/{creator_course.id}/modules",
        json={"title": "Test Module for AI", "order_index": 0},
        headers={"Authorization": f"Bearer {creator_token}"},
    )
    assert res.status_code == 201
    return res.json()


def test_generate_module_description_streams_tokens(creator_token, creator_module):
    """POST /api/modules/:id/ai/generate-description returns 200 with SSE stream."""
    # Reset AppStatus.should_exit_event between tests (sse-starlette 2.x anyio.Event
    # class-level attribute causes cross-loop RuntimeError across TestClient invocations)
    AppStatus.should_exit_event = None

    mock_tokens = ["A ", "great ", "module."]

    async def mock_stream(prompt):
        for token in mock_tokens:
            yield token

    with patch("routers.modules.claude_service._stream_text", side_effect=mock_stream):
        res = client.post(
            f"/api/modules/{creator_module['id']}/ai/generate-description",
            json={"prompt": "Introduction to testing"},
            headers={"Authorization": f"Bearer {creator_token}"},
        )

    assert res.status_code == 200
    body = res.text
    assert "data:" in body


def test_generate_module_description_requires_auth(creator_module):
    """POST without auth token returns 401 or 403."""
    AppStatus.should_exit_event = None

    res = client.post(
        f"/api/modules/{creator_module['id']}/ai/generate-description",
        json={"prompt": "test prompt"},
    )
    assert res.status_code in (401, 403)


def test_generate_module_description_404_for_unknown_module(creator_token):
    """POST for non-existent module_id returns 404."""
    AppStatus.should_exit_event = None

    res = client.post(
        "/api/modules/99999/ai/generate-description",
        json={"prompt": "test"},
        headers={"Authorization": f"Bearer {creator_token}"},
    )
    assert res.status_code == 404
