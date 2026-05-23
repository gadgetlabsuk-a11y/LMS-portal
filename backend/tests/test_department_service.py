"""Unit tests for department_service: enrolment sync, due-date, status, completion."""
from datetime import datetime, timedelta

from models import (
    Department, DepartmentMember, DepartmentContent,
    Enrollment, BroadcastSession, User, UserRole, Course, CourseStatus, Broadcast,
)
from services.auth_service import AuthService
from services import department_service as svc


def _user(db, name):
    u = User(username=name, email=f"{name}@example.com",
             hashed_password=AuthService.hash_password("pass123"),
             role=UserRole.TRAINEE, is_active=True)
    db.add(u); db.commit(); db.refresh(u)
    return u


def _course(db, creator_id, title="C1"):
    c = Course(title=title, status=CourseStatus.PUBLISHED, creator_id=creator_id)
    db.add(c); db.commit(); db.refresh(c)
    return c


def _broadcast(db, creator_id, title="B1"):
    b = Broadcast(title=title, creator_id=creator_id, published=True)
    db.add(b); db.commit(); db.refresh(b)
    return b


def _dept(db, name="Ops"):
    d = Department(name=name); db.add(d); db.commit(); db.refresh(d)
    return d


def test_ensure_enrollment_is_idempotent(db):
    u = _user(db, "alice"); c = _course(db, u.id)
    e1 = svc.ensure_enrollment(db, u.id, c.id); db.commit()
    e2 = svc.ensure_enrollment(db, u.id, c.id); db.commit()
    assert e1.id == e2.id
    assert db.query(Enrollment).filter(Enrollment.user_id == u.id, Enrollment.course_id == c.id).count() == 1


def test_sync_assignment_enrolls_current_members(db):
    creator = _user(db, "creator"); u1 = _user(db, "u1"); u2 = _user(db, "u2")
    d = _dept(db); c = _course(db, creator.id)
    db.add(DepartmentMember(department_id=d.id, user_id=u1.id))
    db.add(DepartmentMember(department_id=d.id, user_id=u2.id))
    db.commit()
    svc.sync_assignment_enrollments(db, d.id, c.id)
    assert db.query(Enrollment).filter(Enrollment.course_id == c.id).count() == 2


def test_sync_member_enrolls_in_course_content_only(db):
    creator = _user(db, "creator"); u = _user(db, "joiner")
    d = _dept(db)
    c1 = _course(db, creator.id, "A"); c2 = _course(db, creator.id, "B")
    b = _broadcast(db, creator.id)
    db.add(DepartmentContent(department_id=d.id, course_id=c1.id))
    db.add(DepartmentContent(department_id=d.id, course_id=c2.id))
    db.add(DepartmentContent(department_id=d.id, broadcast_id=b.id))  # must NOT create an enrolment
    db.add(DepartmentMember(department_id=d.id, user_id=u.id))
    db.commit()
    svc.sync_member_enrollments(db, d.id, u.id)
    assert db.query(Enrollment).filter(Enrollment.user_id == u.id).count() == 2


def test_effective_due_date_fixed_and_relative_uses_anchor():
    fixed = DepartmentContent(mandatory=True, due_mode="fixed", due_date=datetime(2026, 6, 30))
    assert svc.effective_due_date(fixed, datetime(2026, 1, 1)) == datetime(2026, 6, 30)
    rel = DepartmentContent(mandatory=True, due_mode="relative", due_days=30)
    anchor = datetime(2026, 1, 1)
    assert svc.effective_due_date(rel, anchor) == anchor + timedelta(days=30)
    not_mand = DepartmentContent(mandatory=False, due_mode="fixed", due_date=datetime(2026, 6, 30))
    assert svc.effective_due_date(not_mand, anchor) is None
    no_deadline = DepartmentContent(mandatory=True, due_mode=None)
    assert svc.effective_due_date(no_deadline, anchor) is None


def test_status_for():
    now = datetime(2026, 5, 23)
    assert svc.status_for(completed=True, started=True, due=datetime(2026, 1, 1), now=now) == "completed"
    assert svc.status_for(completed=False, started=True, due=datetime(2026, 1, 1), now=now) == "overdue"
    assert svc.status_for(completed=False, started=True, due=datetime(2026, 12, 1), now=now) == "in_progress"
    assert svc.status_for(completed=False, started=False, due=None, now=now) == "not_started"
    assert svc.status_for(completed=False, started=False, due=datetime(2026, 1, 1), now=now) == "overdue"


def test_course_completion_signals(db):
    u = _user(db, "u"); c = _course(db, u.id)
    content = DepartmentContent(course_id=c.id)
    assert svc.content_completed(db, u.id, content) is False
    e = Enrollment(user_id=u.id, course_id=c.id, progress=50.0, completed=False)
    db.add(e); db.commit()
    assert svc.content_started(db, u.id, content) is True
    assert svc.content_completed(db, u.id, content) is False
    e.completed = True; db.commit()
    assert svc.content_completed(db, u.id, content) is True


def test_broadcast_completion_signals(db):
    u = _user(db, "u"); b = _broadcast(db, u.id)
    content = DepartmentContent(broadcast_id=b.id)
    assert svc.content_started(db, u.id, content) is False
    assert svc.content_completed(db, u.id, content) is False
    bs = BroadcastSession(broadcast_id=b.id, learner_id=u.id, mode="interrupt",
                          started_at=datetime.utcnow(), completion_status="in_progress")
    db.add(bs); db.commit()
    assert svc.content_started(db, u.id, content) is True
    assert svc.content_completed(db, u.id, content) is False
    bs.completion_status = "completed"; db.commit()
    assert svc.content_completed(db, u.id, content) is True


def test_effective_due_for_user_earliest_across_departments(db):
    creator = _user(db, "creator"); u = _user(db, "multi")
    c = _course(db, creator.id)
    d1 = _dept(db, "D1"); d2 = _dept(db, "D2")
    db.add(DepartmentMember(department_id=d1.id, user_id=u.id, added_at=datetime(2026, 1, 1)))
    db.add(DepartmentMember(department_id=d2.id, user_id=u.id, added_at=datetime(2026, 1, 1)))
    db.add(DepartmentContent(department_id=d1.id, course_id=c.id, mandatory=True, due_mode="fixed", due_date=datetime(2026, 9, 1)))
    db.add(DepartmentContent(department_id=d2.id, course_id=c.id, mandatory=True, due_mode="fixed", due_date=datetime(2026, 7, 1)))
    db.commit()
    assert svc.is_mandatory_for_user(db, u.id, course_id=c.id) is True
    assert svc.effective_due_for_user(db, u.id, course_id=c.id) == datetime(2026, 7, 1)


def test_effective_due_for_user_relative_uses_per_department_join_date(db):
    creator = _user(db, "creator_r"); u = _user(db, "rel")
    c = _course(db, creator.id)
    d1 = _dept(db, "RD1"); d2 = _dept(db, "RD2")
    db.add(DepartmentMember(department_id=d1.id, user_id=u.id, added_at=datetime(2026, 1, 1)))
    db.add(DepartmentMember(department_id=d2.id, user_id=u.id, added_at=datetime(2026, 3, 1)))
    db.add(DepartmentContent(department_id=d1.id, course_id=c.id, mandatory=True, due_mode="relative", due_days=10))
    db.add(DepartmentContent(department_id=d2.id, course_id=c.id, mandatory=True, due_mode="relative", due_days=10))
    db.commit()
    # d1: Jan 1 + 10d = Jan 11; d2: Mar 1 + 10d = Mar 11 -> earliest = Jan 11
    assert svc.effective_due_for_user(db, u.id, course_id=c.id) == datetime(2026, 1, 11)
