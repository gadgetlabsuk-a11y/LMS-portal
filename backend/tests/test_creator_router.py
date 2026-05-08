"""Tests for GET /api/creator/stats and GET /api/creator/learners."""
import pytest
from models import Enrollment, CourseStatus


class TestCreatorStats:

    def test_unauthenticated_returns_401(self, client):
        res = client.get("/api/creator/stats")
        assert res.status_code in (401, 403)

    def test_trainee_returns_403(self, client, trainee_token):
        res = client.get(
            "/api/creator/stats",
            headers={"Authorization": f"Bearer {trainee_token}"},
        )
        assert res.status_code == 403

    def test_creator_with_no_courses_returns_zeros(self, client, creator_token):
        res = client.get(
            "/api/creator/stats",
            headers={"Authorization": f"Bearer {creator_token}"},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["total_courses"] == 0
        assert data["published_courses"] == 0
        assert data["draft_courses"] == 0
        assert data["total_enrollments"] == 0

    def test_counts_only_own_courses(self, client, creator_token, creator_course, published_course):
        # published_course belongs to admin_user, not creator_user
        res = client.get(
            "/api/creator/stats",
            headers={"Authorization": f"Bearer {creator_token}"},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["total_courses"] == 1
        assert data["published_courses"] == 1
        assert data["draft_courses"] == 0

    def test_enrollment_count(self, client, creator_token, creator_course, trainee_user, db):
        enrollment = Enrollment(
            user_id=trainee_user.id,
            course_id=creator_course.id,
        )
        db.add(enrollment)
        db.commit()

        res = client.get(
            "/api/creator/stats",
            headers={"Authorization": f"Bearer {creator_token}"},
        )
        assert res.status_code == 200
        assert res.json()["total_enrollments"] == 1

    def test_response_shape(self, client, creator_token):
        res = client.get(
            "/api/creator/stats",
            headers={"Authorization": f"Bearer {creator_token}"},
        )
        assert res.status_code == 200
        data = res.json()
        assert "total_courses" in data
        assert "published_courses" in data
        assert "draft_courses" in data
        assert "total_enrollments" in data


class TestCreatorLearners:

    def test_unauthenticated_returns_401(self, client):
        res = client.get("/api/creator/learners")
        assert res.status_code in (401, 403)

    def test_trainee_returns_403(self, client, trainee_token):
        res = client.get(
            "/api/creator/learners",
            headers={"Authorization": f"Bearer {trainee_token}"},
        )
        assert res.status_code == 403

    def test_no_enrollments_returns_empty_list(self, client, creator_token, creator_course):
        res = client.get(
            "/api/creator/learners",
            headers={"Authorization": f"Bearer {creator_token}"},
        )
        assert res.status_code == 200
        assert res.json() == []

    def test_returns_enrolled_learner(self, client, creator_token, creator_course, trainee_user, db):
        enrollment = Enrollment(
            user_id=trainee_user.id,
            course_id=creator_course.id,
        )
        db.add(enrollment)
        db.commit()

        res = client.get(
            "/api/creator/learners",
            headers={"Authorization": f"Bearer {creator_token}"},
        )
        assert res.status_code == 200
        data = res.json()
        assert len(data) == 1
        assert data[0]["learner_name"] == trainee_user.username
        assert data[0]["email"] == trainee_user.email
        assert data[0]["course_id"] == creator_course.id
        assert data[0]["course_title"] == creator_course.title
        assert "enrolled_at" in data[0]

    def test_course_id_filter(self, client, creator_token, creator_course, trainee_user, db):
        enrollment = Enrollment(
            user_id=trainee_user.id,
            course_id=creator_course.id,
        )
        db.add(enrollment)
        db.commit()

        # Filter to the correct course — should return 1
        res = client.get(
            f"/api/creator/learners?course_id={creator_course.id}",
            headers={"Authorization": f"Bearer {creator_token}"},
        )
        assert res.status_code == 200
        assert len(res.json()) == 1

    def test_course_id_filter_wrong_course_returns_empty(self, client, creator_token, creator_course, trainee_user, db):
        enrollment = Enrollment(
            user_id=trainee_user.id,
            course_id=creator_course.id,
        )
        db.add(enrollment)
        db.commit()

        # Filter to a non-existent course_id — should return empty (not an error)
        res = client.get(
            "/api/creator/learners?course_id=99999",
            headers={"Authorization": f"Bearer {creator_token}"},
        )
        assert res.status_code == 200
        assert res.json() == []

    def test_does_not_return_other_creators_learners(self, client, creator_token, published_course, trainee_user, db):
        # published_course belongs to admin_user, not creator_user
        enrollment = Enrollment(
            user_id=trainee_user.id,
            course_id=published_course.id,
        )
        db.add(enrollment)
        db.commit()

        res = client.get(
            "/api/creator/learners",
            headers={"Authorization": f"Bearer {creator_token}"},
        )
        assert res.status_code == 200
        assert res.json() == []
