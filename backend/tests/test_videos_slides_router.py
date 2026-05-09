"""
Tests for Video and Slide CRUD + reorder routers.
Covers all 12 endpoints: 6 video, 6 slide.
"""

import pytest
from fastapi.testclient import TestClient

# conftest.py provides: client, db, creator_user, creator_token, trainee_token, creator_course


# ---------------------------------------------------------------------------
# Helper fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def creator_module(client, creator_token, creator_course):
    """Create a module via the API — returns response JSON dict."""
    resp = client.post(
        f"/api/courses/{creator_course.id}/modules",
        json={"title": "Module 1"},
        headers={"Authorization": f"Bearer {creator_token}"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


@pytest.fixture
def creator_video(client, creator_token, creator_module):
    """Create a video via the API — returns response JSON dict."""
    resp = client.post(
        f"/api/modules/{creator_module['id']}/videos",
        json={"title": "Video 1"},
        headers={"Authorization": f"Bearer {creator_token}"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


@pytest.fixture
def creator_slide(client, creator_token, creator_video):
    """Create a slide via the API — returns response JSON dict."""
    resp = client.post(
        f"/api/videos/{creator_video['id']}/slides",
        json={"layout_id": "layout_a"},
        headers={"Authorization": f"Bearer {creator_token}"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


# ---------------------------------------------------------------------------
# Video tests
# ---------------------------------------------------------------------------

def test_create_video(client, creator_token, creator_module):
    """POST /api/modules/{module_id}/videos → 201 with id and title."""
    resp = client.post(
        f"/api/modules/{creator_module['id']}/videos",
        json={"title": "My First Video"},
        headers={"Authorization": f"Bearer {creator_token}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert "id" in data
    assert data["title"] == "My First Video"
    assert data["module_id"] == creator_module["id"]
    assert data["video_type"] == "slideshow_narrated"
    assert data["status"] == "draft"


def test_list_videos(client, creator_token, creator_module, creator_video):
    """GET /api/modules/{module_id}/videos → list with correct module_id."""
    resp = client.get(
        f"/api/modules/{creator_module['id']}/videos",
        headers={"Authorization": f"Bearer {creator_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert all(v["module_id"] == creator_module["id"] for v in data)


def test_update_video(client, creator_token, creator_video):
    """PUT /api/videos/{video_id} updates video_type field."""
    resp = client.put(
        f"/api/videos/{creator_video['id']}",
        json={"video_type": "upload"},
        headers={"Authorization": f"Bearer {creator_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["video_type"] == "upload"
    assert data["id"] == creator_video["id"]


def test_delete_video(client, creator_token, creator_module):
    """DELETE /api/videos/{video_id} → 200; subsequent GET → 404."""
    # Create a video to delete
    create_resp = client.post(
        f"/api/modules/{creator_module['id']}/videos",
        json={"title": "Video to Delete"},
        headers={"Authorization": f"Bearer {creator_token}"},
    )
    assert create_resp.status_code == 201
    video_id = create_resp.json()["id"]

    # Delete it
    del_resp = client.delete(
        f"/api/videos/{video_id}",
        headers={"Authorization": f"Bearer {creator_token}"},
    )
    assert del_resp.status_code == 200
    assert del_resp.json()["message"] == "Video deleted"

    # Subsequent GET → 404
    get_resp = client.get(
        f"/api/videos/{video_id}",
        headers={"Authorization": f"Bearer {creator_token}"},
    )
    assert get_resp.status_code == 404


def test_reorder_videos(client, creator_token, creator_module):
    """Create 3 videos, reorder reversed, verify new order."""
    auth = {"Authorization": f"Bearer {creator_token}"}
    module_id = creator_module["id"]

    # Create 3 videos
    ids = []
    for i in range(3):
        resp = client.post(
            f"/api/modules/{module_id}/videos",
            json={"title": f"Video {i}"},
            headers=auth,
        )
        assert resp.status_code == 201
        ids.append(resp.json()["id"])

    # Reorder in reverse
    reversed_ids = list(reversed(ids))
    reorder_resp = client.post(
        f"/api/modules/{module_id}/videos/reorder",
        json={"video_ids": reversed_ids},
        headers=auth,
    )
    assert reorder_resp.status_code == 200

    # Verify new order
    list_resp = client.get(f"/api/modules/{module_id}/videos", headers=auth)
    assert list_resp.status_code == 200
    returned_ids = [v["id"] for v in list_resp.json()]
    assert returned_ids == reversed_ids


def test_trainee_cannot_create_video(client, trainee_token, creator_module):
    """A trainee token on a video endpoint returns 403."""
    resp = client.post(
        f"/api/modules/{creator_module['id']}/videos",
        json={"title": "Should Fail"},
        headers={"Authorization": f"Bearer {trainee_token}"},
    )
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Slide tests
# ---------------------------------------------------------------------------

def test_create_slide(client, creator_token, creator_video):
    """POST /api/videos/{video_id}/slides → 201 with video_id."""
    resp = client.post(
        f"/api/videos/{creator_video['id']}/slides",
        json={"layout_id": "layout_b", "narration_script": "Hello world"},
        headers={"Authorization": f"Bearer {creator_token}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert "id" in data
    assert data["video_id"] == creator_video["id"]
    assert data["layout_id"] == "layout_b"
    assert data["status"] == "draft"


def test_list_slides(client, creator_token, creator_video, creator_slide):
    """GET /api/videos/{video_id}/slides → ordered list."""
    resp = client.get(
        f"/api/videos/{creator_video['id']}/slides",
        headers={"Authorization": f"Bearer {creator_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    # Check ordering by order_index
    indices = [s["order_index"] for s in data]
    assert indices == sorted(indices)


def test_update_slide(client, creator_token, creator_slide):
    """PUT /api/slides/{slide_id} updates narration_script."""
    resp = client.put(
        f"/api/slides/{creator_slide['id']}",
        json={"narration_script": "Updated narration text"},
        headers={"Authorization": f"Bearer {creator_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["narration_script"] == "Updated narration text"
    assert data["id"] == creator_slide["id"]


def test_delete_slide(client, creator_token, creator_video):
    """DELETE /api/slides/{slide_id} → 200; subsequent GET → 404."""
    auth = {"Authorization": f"Bearer {creator_token}"}

    # Create a slide to delete
    create_resp = client.post(
        f"/api/videos/{creator_video['id']}/slides",
        json={"layout_id": "layout_to_delete"},
        headers=auth,
    )
    assert create_resp.status_code == 201
    slide_id = create_resp.json()["id"]

    # Delete it
    del_resp = client.delete(f"/api/slides/{slide_id}", headers=auth)
    assert del_resp.status_code == 200
    assert del_resp.json()["message"] == "Slide deleted"

    # Subsequent GET → 404
    get_resp = client.get(f"/api/slides/{slide_id}", headers=auth)
    assert get_resp.status_code == 404


def test_reorder_slides(client, creator_token, creator_video):
    """Create 3 slides, reorder reversed, verify new order."""
    auth = {"Authorization": f"Bearer {creator_token}"}
    video_id = creator_video["id"]

    # Create 3 slides
    ids = []
    for i in range(3):
        resp = client.post(
            f"/api/videos/{video_id}/slides",
            json={"layout_id": f"layout_{i}"},
            headers=auth,
        )
        assert resp.status_code == 201
        ids.append(resp.json()["id"])

    # Reorder in reverse
    reversed_ids = list(reversed(ids))
    reorder_resp = client.post(
        f"/api/videos/{video_id}/slides/reorder",
        json={"slide_ids": reversed_ids},
        headers=auth,
    )
    assert reorder_resp.status_code == 200

    # Verify new order
    list_resp = client.get(f"/api/videos/{video_id}/slides", headers=auth)
    assert list_resp.status_code == 200
    returned_ids = [s["id"] for s in list_resp.json()]
    assert returned_ids == reversed_ids


def test_trainee_cannot_create_slide(client, trainee_token, creator_video):
    """A trainee token on a slide endpoint returns 403."""
    resp = client.post(
        f"/api/videos/{creator_video['id']}/slides",
        json={"layout_id": "layout_x"},
        headers={"Authorization": f"Bearer {trainee_token}"},
    )
    assert resp.status_code == 403
