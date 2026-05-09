"""
Phase 14 — SLIDE-11, SLIDE-12 integration tests for slides SSE endpoints.
Wave 0 stubs: all tests fail with pytest.fail() until implementation in Plan 02.
"""
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


# ---------------------------------------------------------------------------
# SLIDE-11: POST /api/slides/{slide_id}/ai/generate-narration
# ---------------------------------------------------------------------------

def test_generate_narration_streams_tokens(creator_token, creator_course):
    """POST /api/slides/{id}/ai/generate-narration returns 200 with SSE stream."""
    pytest.fail("SLIDE-11 not yet implemented — Plan 02")


def test_generate_narration_requires_auth():
    """POST without auth token returns 401 or 403."""
    pytest.fail("SLIDE-11 not yet implemented — Plan 02")


def test_generate_narration_404_for_unknown_slide(creator_token):
    """POST with unknown slide_id returns 404."""
    pytest.fail("SLIDE-11 not yet implemented — Plan 02")


# ---------------------------------------------------------------------------
# SLIDE-12: POST /api/slides/{slide_id}/ai/generate-outline
# ---------------------------------------------------------------------------

def test_generate_outline_streams_json(creator_token, creator_course):
    """POST /api/slides/{id}/ai/generate-outline returns 200 with SSE stream."""
    pytest.fail("SLIDE-12 not yet implemented — Plan 02")


def test_generate_outline_requires_auth():
    """POST without auth token returns 401 or 403."""
    pytest.fail("SLIDE-12 not yet implemented — Plan 02")
