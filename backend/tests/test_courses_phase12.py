"""
Phase 12 test stubs — Course Identity & Structure.
All tests start as FAILING stubs (Wave 0).
Replace pytest.fail() with real assertions in Wave 1.
"""
import pytest


def test_create_course_with_identity(client, creator_token):
    """COURSE-01: POST /api/courses saves audience_level, learning_objectives, ai_tone_preset."""
    pytest.fail("STUB — implement in 12-02")


def test_generate_description_sse(client, creator_token):
    """COURSE-02: POST /api/courses/ai/generate-description returns SSE text/event-stream."""
    pytest.fail("STUB — implement in 12-02")


def test_generate_objectives_sse(client, creator_token):
    """COURSE-03: POST /api/courses/ai/generate-objectives returns SSE text/event-stream."""
    pytest.fail("STUB — implement in 12-02")


def test_scaffold_structure(client, creator_token, creator_course):
    """COURSE-05: Scaffolding creates expected modules and videos in order."""
    pytest.fail("STUB — implement in 12-02")
