"""Model-level tests for departments, membership, and content assignment."""
import pytest
from sqlalchemy.exc import IntegrityError

from models import (
    Department, DepartmentMember, DepartmentContent,
    User, UserRole, Course, CourseStatus, Broadcast,
)
from services.auth_service import AuthService


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


def test_create_department_defaults(db):
    d = Department(name="Operations", description="Ops team")
    db.add(d); db.commit(); db.refresh(d)
    assert d.id is not None
    assert d.is_active is True
    assert d.members == []
    assert d.content == []


def test_department_name_unique(db):
    db.add(Department(name="Sales")); db.commit()
    db.add(Department(name="Sales"))
    with pytest.raises(IntegrityError):
        db.commit()


def test_member_unique_per_department(db):
    d = Department(name="QA"); db.add(d); db.commit(); db.refresh(d)
    u = _user(db, "alice")
    db.add(DepartmentMember(department_id=d.id, user_id=u.id)); db.commit()
    db.add(DepartmentMember(department_id=d.id, user_id=u.id))
    with pytest.raises(IntegrityError):
        db.commit()


def test_content_unique_per_department(db):
    creator = _user(db, "creator1")
    d = Department(name="Finance"); db.add(d); db.commit(); db.refresh(d)
    c = _course(db, creator.id)
    db.add(DepartmentContent(department_id=d.id, course_id=c.id)); db.commit()
    db.add(DepartmentContent(department_id=d.id, course_id=c.id))
    with pytest.raises(IntegrityError):
        db.commit()


def test_broadcast_content_unique_per_department(db):
    creator = _user(db, "creator_b")
    d = Department(name="Comms"); db.add(d); db.commit(); db.refresh(d)
    b = _broadcast(db, creator.id)
    db.add(DepartmentContent(department_id=d.id, broadcast_id=b.id)); db.commit()
    db.add(DepartmentContent(department_id=d.id, broadcast_id=b.id))
    with pytest.raises(IntegrityError):
        db.commit()


def test_course_and_broadcast_assignments_coexist(db):
    creator = _user(db, "creator_mix")
    d = Department(name="Mixed"); db.add(d); db.commit(); db.refresh(d)
    c = _course(db, creator.id)
    b = _broadcast(db, creator.id)
    db.add(DepartmentContent(department_id=d.id, course_id=c.id))
    db.add(DepartmentContent(department_id=d.id, broadcast_id=b.id))
    db.commit()
    rows = db.query(DepartmentContent).filter(DepartmentContent.department_id == d.id).all()
    assert len(rows) == 2
    # the unused FK is NULL on each row, and "kind" is derivable from which id is set
    assert {(r.course_id is not None, r.broadcast_id is not None) for r in rows} == {(True, False), (False, True)}


def test_deleting_department_cascades_members_and_content(db):
    creator = _user(db, "creator2")
    d = Department(name="Legal"); db.add(d); db.commit(); db.refresh(d)
    u = _user(db, "bob")
    c = _course(db, creator.id)
    b = _broadcast(db, creator.id)
    db.add(DepartmentMember(department_id=d.id, user_id=u.id))
    db.add(DepartmentContent(department_id=d.id, course_id=c.id))
    db.add(DepartmentContent(department_id=d.id, broadcast_id=b.id))
    db.commit()

    db.delete(d); db.commit()
    assert db.query(DepartmentMember).filter(DepartmentMember.department_id == d.id).count() == 0
    assert db.query(DepartmentContent).filter(DepartmentContent.department_id == d.id).count() == 0
