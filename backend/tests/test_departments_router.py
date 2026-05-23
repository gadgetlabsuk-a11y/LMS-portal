"""Integration tests for the departments router (CRUD + members)."""
from models import Department, DepartmentMember, DepartmentContent, Enrollment, Course, CourseStatus


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
