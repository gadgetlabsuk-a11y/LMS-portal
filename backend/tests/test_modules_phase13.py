"""
Phase 13 — BUILD-05 tests for POST /api/modules/:id/ai/generate-description SSE endpoint.
STUB: All tests call pytest.fail() — RED state before implementation.
Pattern from Phase 12: test_courses_phase12.py stubs used pytest.fail() directly.
"""
import pytest


def test_generate_module_description_streams_tokens():
    """POST /api/modules/:id/ai/generate-description returns SSE token stream."""
    pytest.fail(
        "BUILD-05 not implemented — POST /api/modules/:id/ai/generate-description "
        "SSE endpoint does not exist yet. Add to backend/routers/modules.py."
    )


def test_generate_module_description_requires_auth():
    """Unauthenticated POST returns 401."""
    pytest.fail(
        "BUILD-05 not implemented — auth guard on SSE endpoint not verified yet."
    )


def test_generate_module_description_404_for_unknown_module():
    """POST for non-existent module_id returns 404."""
    pytest.fail(
        "BUILD-05 not implemented — 404 handling not verified yet."
    )
