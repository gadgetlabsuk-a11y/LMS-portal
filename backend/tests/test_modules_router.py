"""Tests for the Module CRUD + reorder router (11-01)."""
import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def create_module(client: TestClient, course_id: int, token: str, title: str = "Test Module") -> dict:
    resp = client.post(
        f"/api/courses/{course_id}/modules",
        json={"title": title},
        headers=auth_headers(token),
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_create_module(client, creator_token, creator_course):
    resp = client.post(
        f"/api/courses/{creator_course.id}/modules",
        json={"title": "Intro Module"},
        headers=auth_headers(creator_token),
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "Intro Module"
    assert "id" in data
    assert data["course_id"] == creator_course.id
    assert data["order_index"] == 0


def test_list_modules(client, creator_token, creator_course):
    # Create three modules
    create_module(client, creator_course.id, creator_token, "Module A")
    create_module(client, creator_course.id, creator_token, "Module B")
    create_module(client, creator_course.id, creator_token, "Module C")

    resp = client.get(
        f"/api/courses/{creator_course.id}/modules",
        headers=auth_headers(creator_token),
    )
    assert resp.status_code == 200
    modules = resp.json()
    assert len(modules) == 3
    # Verify order_index is ascending
    assert [m["order_index"] for m in modules] == [0, 1, 2]
    assert [m["title"] for m in modules] == ["Module A", "Module B", "Module C"]


def test_update_module(client, creator_token, creator_course):
    module = create_module(client, creator_course.id, creator_token, "Old Title")

    resp = client.put(
        f"/api/modules/{module['id']}",
        json={"title": "New Title"},
        headers=auth_headers(creator_token),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == "New Title"
    # Old title gone
    assert data["title"] != "Old Title"


def test_delete_module(client, creator_token, creator_course):
    module = create_module(client, creator_course.id, creator_token, "To Delete")

    resp = client.delete(
        f"/api/modules/{module['id']}",
        headers=auth_headers(creator_token),
    )
    assert resp.status_code == 200
    assert resp.json() == {"message": "Module deleted"}

    # Subsequent GET returns 404
    resp2 = client.get(
        f"/api/modules/{module['id']}",
        headers=auth_headers(creator_token),
    )
    assert resp2.status_code == 404


def test_reorder_modules(client, creator_token, creator_course):
    m1 = create_module(client, creator_course.id, creator_token, "First")
    m2 = create_module(client, creator_course.id, creator_token, "Second")
    m3 = create_module(client, creator_course.id, creator_token, "Third")

    # Reverse order
    reversed_ids = [m3["id"], m2["id"], m1["id"]]

    resp = client.post(
        f"/api/courses/{creator_course.id}/modules/reorder",
        json={"module_ids": reversed_ids},
        headers=auth_headers(creator_token),
    )
    assert resp.status_code == 200
    assert resp.json() == {"message": "Reordered"}

    # Verify new order
    list_resp = client.get(
        f"/api/courses/{creator_course.id}/modules",
        headers=auth_headers(creator_token),
    )
    assert list_resp.status_code == 200
    modules = list_resp.json()
    assert len(modules) == 3
    # After reorder, sorted by order_index → titles should be reversed
    assert modules[0]["title"] == "Third"
    assert modules[1]["title"] == "Second"
    assert modules[2]["title"] == "First"
    assert [m["order_index"] for m in modules] == [0, 1, 2]


def test_trainee_cannot_create(client, trainee_token, creator_course):
    resp = client.post(
        f"/api/courses/{creator_course.id}/modules",
        json={"title": "Should Fail"},
        headers=auth_headers(trainee_token),
    )
    assert resp.status_code == 403


def test_trainee_cannot_reorder(client, trainee_token, creator_token, creator_course):
    m1 = create_module(client, creator_course.id, creator_token, "A")
    m2 = create_module(client, creator_course.id, creator_token, "B")

    resp = client.post(
        f"/api/courses/{creator_course.id}/modules/reorder",
        json={"module_ids": [m2["id"], m1["id"]]},
        headers=auth_headers(trainee_token),
    )
    assert resp.status_code == 403
