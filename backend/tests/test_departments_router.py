"""Integration tests for the departments router (CRUD + members)."""
from models import Department, DepartmentMember, DepartmentContent, Enrollment, Course, CourseStatus, Broadcast, BroadcastSession


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def _make_course(db, creator_id, title="C1"):
    c = Course(title=title, status=CourseStatus.PUBLISHED, creator_id=creator_id)
    db.add(c); db.commit(); db.refresh(c)
    return c


def test_requires_admin(client, trainee_token):
    r = client.get("/api/departments", headers=_auth(trainee_token))
    assert r.status_code == 403


def test_create_list_get_update_delete(client, db, admin_token):
    r = client.post("/api/departments", json={"name": "Operations", "description": "Ops"}, headers=_auth(admin_token))
    assert r.status_code == 201, r.text
    dept_id = r.json()["id"]
    assert r.json()["member_count"] == 0 and r.json()["content_count"] == 0

    r = client.post("/api/departments", json={"name": "Operations"}, headers=_auth(admin_token))
    assert r.status_code == 409

    r = client.get("/api/departments", headers=_auth(admin_token))
    assert r.status_code == 200 and any(d["id"] == dept_id for d in r.json())

    r = client.get(f"/api/departments/{dept_id}", headers=_auth(admin_token))
    assert r.status_code == 200 and r.json()["members"] == [] and r.json()["content"] == []

    r = client.put(f"/api/departments/{dept_id}", json={"is_active": False}, headers=_auth(admin_token))
    assert r.status_code == 200 and r.json()["is_active"] is False

    r = client.delete(f"/api/departments/{dept_id}", headers=_auth(admin_token))
    assert r.status_code == 200
    assert db.query(Department).filter(Department.id == dept_id).first() is None


def test_get_missing_department_404(client, admin_token):
    r = client.get("/api/departments/9999", headers=_auth(admin_token))
    assert r.status_code == 404


def test_add_and_remove_members(client, db, admin_token, trainee_user):
    dept_id = client.post("/api/departments", json={"name": "Ops"}, headers=_auth(admin_token)).json()["id"]
    r = client.post(f"/api/departments/{dept_id}/members", json={"user_ids": [trainee_user.id]}, headers=_auth(admin_token))
    assert r.status_code == 200 and any(m["id"] == trainee_user.id for m in r.json())
    r = client.post(f"/api/departments/{dept_id}/members", json={"user_ids": [trainee_user.id]}, headers=_auth(admin_token))
    assert r.status_code == 200
    assert db.query(DepartmentMember).filter(DepartmentMember.department_id == dept_id).count() == 1
    r = client.post(f"/api/departments/{dept_id}/members", json={"user_ids": [99999]}, headers=_auth(admin_token))
    assert r.status_code == 400
    r = client.delete(f"/api/departments/{dept_id}/members/{trainee_user.id}", headers=_auth(admin_token))
    assert r.status_code == 200
    assert db.query(DepartmentMember).filter(DepartmentMember.department_id == dept_id).count() == 0


def test_new_member_inherits_course_enrollment(client, db, admin_token, admin_user, trainee_user):
    dept_id = client.post("/api/departments", json={"name": "Compliance"}, headers=_auth(admin_token)).json()["id"]
    course = _make_course(db, admin_user.id)
    db.add(DepartmentContent(department_id=dept_id, course_id=course.id, mandatory=True)); db.commit()
    r = client.post(f"/api/departments/{dept_id}/members", json={"user_ids": [trainee_user.id]}, headers=_auth(admin_token))
    assert r.status_code == 200
    assert db.query(Enrollment).filter(Enrollment.user_id == trainee_user.id, Enrollment.course_id == course.id).count() == 1


from datetime import datetime


def _make_broadcast(db, creator_id, title="B1", published=True):
    b = Broadcast(title=title, creator_id=creator_id, published=published)
    db.add(b); db.commit(); db.refresh(b)
    return b


def test_assign_course_enrolls_members_and_validates(client, db, admin_token, admin_user, trainee_user):
    dept_id = client.post("/api/departments", json={"name": "Safety"}, headers=_auth(admin_token)).json()["id"]
    course = _make_course(db, admin_user.id, "Fire Safety")
    client.post(f"/api/departments/{dept_id}/members", json={"user_ids": [trainee_user.id]}, headers=_auth(admin_token))
    r = client.post(f"/api/departments/{dept_id}/content",
                    json={"course_id": course.id, "mandatory": True, "due_mode": "fixed", "due_date": "2026-06-30T00:00:00"},
                    headers=_auth(admin_token))
    assert r.status_code == 201, r.text
    assert r.json()["content_type"] == "course" and r.json()["mandatory"] is True
    content_id = r.json()["id"]
    assert db.query(Enrollment).filter(Enrollment.user_id == trainee_user.id, Enrollment.course_id == course.id).count() == 1
    assert client.post(f"/api/departments/{dept_id}/content", json={"course_id": course.id}, headers=_auth(admin_token)).status_code == 409
    assert client.post(f"/api/departments/{dept_id}/content", json={"course_id": 99999}, headers=_auth(admin_token)).status_code == 404
    r = client.put(f"/api/departments/{dept_id}/content/{content_id}",
                   json={"mandatory": True, "due_mode": "relative", "due_days": 14}, headers=_auth(admin_token))
    assert r.status_code == 200 and r.json()["due_mode"] == "relative" and r.json()["due_date"] is None
    assert client.delete(f"/api/departments/{dept_id}/content/{content_id}", headers=_auth(admin_token)).status_code == 200
    assert db.query(Enrollment).filter(Enrollment.user_id == trainee_user.id, Enrollment.course_id == course.id).count() == 1


def test_assign_broadcast_creates_no_enrollment(client, db, admin_token, admin_user, trainee_user):
    dept_id = client.post("/api/departments", json={"name": "Comms"}, headers=_auth(admin_token)).json()["id"]
    b = _make_broadcast(db, admin_user.id)
    client.post(f"/api/departments/{dept_id}/members", json={"user_ids": [trainee_user.id]}, headers=_auth(admin_token))
    r = client.post(f"/api/departments/{dept_id}/content",
                    json={"broadcast_id": b.id, "mandatory": True, "due_mode": "relative", "due_days": 7},
                    headers=_auth(admin_token))
    assert r.status_code == 201, r.text
    assert r.json()["content_type"] == "broadcast" and r.json()["is_podcast"] is True
    assert db.query(Enrollment).filter(Enrollment.user_id == trainee_user.id).count() == 0
    assert client.post(f"/api/departments/{dept_id}/content", json={"broadcast_id": b.id}, headers=_auth(admin_token)).status_code == 409
    assert client.post(f"/api/departments/{dept_id}/content", json={"broadcast_id": 99999}, headers=_auth(admin_token)).status_code == 404


def test_assign_requires_exactly_one_target(client, db, admin_token, admin_user):
    dept_id = client.post("/api/departments", json={"name": "XOne"}, headers=_auth(admin_token)).json()["id"]
    course = _make_course(db, admin_user.id)
    b = _make_broadcast(db, admin_user.id)
    assert client.post(f"/api/departments/{dept_id}/content", json={"mandatory": False}, headers=_auth(admin_token)).status_code == 400
    assert client.post(f"/api/departments/{dept_id}/content", json={"course_id": course.id, "broadcast_id": b.id}, headers=_auth(admin_token)).status_code == 400


def test_assign_invalid_due_config_400(client, db, admin_token, admin_user):
    dept_id = client.post("/api/departments", json={"name": "BadDue"}, headers=_auth(admin_token)).json()["id"]
    course = _make_course(db, admin_user.id)
    assert client.post(f"/api/departments/{dept_id}/content", json={"course_id": course.id, "mandatory": True, "due_mode": "fixed"}, headers=_auth(admin_token)).status_code == 400
    assert client.post(f"/api/departments/{dept_id}/content", json={"course_id": course.id, "mandatory": True, "due_mode": "relative", "due_days": 0}, headers=_auth(admin_token)).status_code == 400


def test_compliance_counts_courses_and_broadcasts(client, db, admin_token, admin_user, trainee_user):
    dept_id = client.post("/api/departments", json={"name": "Counts"}, headers=_auth(admin_token)).json()["id"]
    course = _make_course(db, admin_user.id, "C101")
    b = _make_broadcast(db, admin_user.id, "B101")
    client.post(f"/api/departments/{dept_id}/members", json={"user_ids": [trainee_user.id]}, headers=_auth(admin_token))
    client.post(f"/api/departments/{dept_id}/content",
                json={"course_id": course.id, "mandatory": True, "due_mode": "fixed", "due_date": "2020-01-01T00:00:00"},
                headers=_auth(admin_token))
    client.post(f"/api/departments/{dept_id}/content", json={"broadcast_id": b.id, "mandatory": True}, headers=_auth(admin_token))

    r = client.get(f"/api/departments/{dept_id}/compliance", headers=_auth(admin_token))
    assert r.status_code == 200, r.text
    items = {it["content_type"]: it for it in r.json()["items"]}
    assert items["course"]["overdue"] == 1 and items["course"]["completed"] == 0
    assert items["broadcast"]["not_started"] == 1

    db.add(BroadcastSession(broadcast_id=b.id, learner_id=trainee_user.id, mode="interrupt",
                            started_at=datetime.utcnow(), completion_status="completed"))
    db.commit()
    r = client.get(f"/api/departments/{dept_id}/compliance", headers=_auth(admin_token))
    items = {it["content_type"]: it for it in r.json()["items"]}
    assert items["broadcast"]["completed"] == 1
