import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

# No top-level import of non-existent endpoints (routers.courses publish/archive/preflight)
# — avoids ImportError before endpoints exist; produces FAILED not ERROR (TDD RED state).


def test_preview_endpoint_returns_draft_course(db, creator_token, creator_course):
    pytest.fail("not implemented — PREVIEW-01")


def test_preview_includes_slides_and_blocks(db, creator_token, creator_course):
    pytest.fail("not implemented — PREVIEW-02")


def test_preflight_returns_results(db, creator_token, creator_course):
    pytest.fail("not implemented — PUBLISH-02")


def test_preflight_fails_no_modules(db, creator_token, creator_course):
    pytest.fail("not implemented — PUBLISH-03")


def test_preflight_fix_urls_present(db, creator_token, creator_course):
    pytest.fail("not implemented — PUBLISH-04")


def test_publish_transitions_to_published(db, creator_token, creator_course):
    pytest.fail("not implemented — PUBLISH-05")


def test_publish_creates_version_snapshot(db, creator_token, creator_course):
    pytest.fail("not implemented — PUBLISH-06")


def test_learner_gets_enrolled_version(db, creator_token, creator_course):
    pytest.fail("not implemented — PUBLISH-07")


def test_archive_hides_from_catalogue(db, creator_token, creator_course):
    pytest.fail("not implemented — PUBLISH-08")
