"""Tests for GET /api/learn/courses and GET /api/learn/courses/{id}."""
import pytest


class TestListLearnCourses:

    def test_unauthenticated_returns_401(self, client):
        res = client.get("/api/learn/courses")
        assert res.status_code in (401, 403)

    def test_returns_only_published_courses(self, client, trainee_token, published_course, draft_course):
        res = client.get(
            "/api/learn/courses",
            headers={"Authorization": f"Bearer {trainee_token}"},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["total"] == 1
        assert data["items"][0]["title"] == "Python Basics"

    def test_response_shape(self, client, trainee_token, published_course):
        res = client.get(
            "/api/learn/courses",
            headers={"Authorization": f"Bearer {trainee_token}"},
        )
        assert res.status_code == 200
        item = res.json()["items"][0]
        assert "id" in item
        assert "title" in item
        assert "description" in item
        assert "has_content" in item
        assert "created_at" in item
        # Admin-only fields must NOT be present
        assert "creator_id" not in item
        assert "status" not in item

    def test_has_content_true_when_content_set(self, client, trainee_token, published_course):
        res = client.get(
            "/api/learn/courses",
            headers={"Authorization": f"Bearer {trainee_token}"},
        )
        item = res.json()["items"][0]
        assert item["has_content"] is True

    def test_search_by_title(self, client, trainee_token, published_course):
        res = client.get(
            "/api/learn/courses?q=Python",
            headers={"Authorization": f"Bearer {trainee_token}"},
        )
        assert res.status_code == 200
        assert res.json()["total"] == 1

    def test_search_no_match_returns_empty(self, client, trainee_token, published_course):
        res = client.get(
            "/api/learn/courses?q=ZZZNOMATCH",
            headers={"Authorization": f"Bearer {trainee_token}"},
        )
        assert res.status_code == 200
        assert res.json()["total"] == 0

    def test_empty_catalogue_returns_zero(self, client, trainee_token):
        res = client.get(
            "/api/learn/courses",
            headers={"Authorization": f"Bearer {trainee_token}"},
        )
        assert res.status_code == 200
        assert res.json()["total"] == 0
        assert res.json()["items"] == []


class TestGetLearnCourse:

    def test_unauthenticated_returns_401(self, client, published_course):
        res = client.get(f"/api/learn/courses/{published_course.id}")
        assert res.status_code in (401, 403)

    def test_returns_published_course(self, client, trainee_token, published_course):
        res = client.get(
            f"/api/learn/courses/{published_course.id}",
            headers={"Authorization": f"Bearer {trainee_token}"},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["id"] == published_course.id
        assert data["title"] == "Python Basics"
        assert data["has_content"] is True
        assert "content" in data

    def test_draft_course_returns_404(self, client, trainee_token, draft_course):
        res = client.get(
            f"/api/learn/courses/{draft_course.id}",
            headers={"Authorization": f"Bearer {trainee_token}"},
        )
        assert res.status_code == 404

    def test_nonexistent_course_returns_404(self, client, trainee_token):
        res = client.get(
            "/api/learn/courses/99999",
            headers={"Authorization": f"Bearer {trainee_token}"},
        )
        assert res.status_code == 404


def test_my_required_training_endpoint(client, db, trainee_user, trainee_token, admin_user):
    from datetime import datetime
    from models import Department, DepartmentMember, DepartmentContent, Course, CourseStatus
    c = Course(title="Mandatory Course", status=CourseStatus.PUBLISHED, creator_id=admin_user.id)
    db.add(c); db.commit(); db.refresh(c)
    d = Department(name="RTDept"); db.add(d); db.commit(); db.refresh(d)
    db.add(DepartmentMember(department_id=d.id, user_id=trainee_user.id))
    db.add(DepartmentContent(department_id=d.id, course_id=c.id, mandatory=True, due_mode="fixed", due_date=datetime(2020, 1, 1)))
    db.commit()

    r = client.get("/api/learn/required-training", headers={"Authorization": f"Bearer {trainee_token}"})
    assert r.status_code == 200, r.text
    items = r.json()
    assert any(it["title"] == "Mandatory Course" and it["content_type"] == "course" and it["status"] == "overdue" for it in items)
