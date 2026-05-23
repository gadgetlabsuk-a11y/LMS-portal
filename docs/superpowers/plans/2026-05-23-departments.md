# Departments, Assignments & Mandatory Training — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let admins create departments, assign users to them, assign courses/podcasts to a department, and mark an assignment mandatory with a deadline — auto-enrolling current and future members so completion can be tracked.

**Architecture:** Three new tables (`departments`, `department_members`, `department_content`) with the assignment table as the source of truth for "what is required." Adding a member or assigning content find-or-creates `Enrollment` rows so progress/completion has somewhere to live. Completion reads `Enrollment.completed` (a small patch makes finishing an ILB broadcast set that flag, matching how regular courses already do it). All endpoints are admin-only; an admin UI mirrors the existing `/admin/*` pages.

**Tech Stack:** Backend — FastAPI, SQLAlchemy, Alembic, SQLite, pytest. Frontend — React + TypeScript, Vite, Tailwind, Vitest + Testing Library.

**Spec:** `docs/superpowers/specs/2026-05-23-departments-design.md`

**Note on environment:** The repo lives on iCloud, so backend `pytest`/`alembic` runs are slow (often minutes per run) but not hung. Run narrow test selections. Backend tests build their schema from the models via `Base.metadata.create_all`, so they do **not** require running Alembic.

**Convention note:** The frontend `api` helper (`frontend/src/services/api.ts`) has `get/post/put/delete` but no `patch`. The spec wrote update endpoints as `PATCH`; this plan implements them as **`PUT`** to match the existing helper and the `users` router. Same behaviour, partial-update semantics preserved server-side.

---

## File Structure

**Backend (cwd = `backend/`):**
- Modify `models/models.py` — add `Department`, `DepartmentMember`, `DepartmentContent` classes.
- Modify `models/__init__.py` — export the three new models.
- Create `alembic/versions/010_departments.py` — create the three tables.
- Create `services/department_service.py` — enrollment sync + due-date + status helpers.
- Create `routers/departments.py` — admin-only CRUD/members/content/compliance endpoints.
- Modify `main.py` — import and register the departments router.
- Modify `routers/ilb.py` — broadcast-complete also marks the enrollment complete.
- Create `tests/test_departments_models.py`, `tests/test_department_service.py`, `tests/test_departments_router.py`; add a test to `tests/test_ilb_router.py`.

**Frontend (cwd = `frontend/`):**
- Create `src/pages/admin/DepartmentsPage.tsx` — list/create/delete departments.
- Create `src/pages/admin/DepartmentDetailPage.tsx` — members + content assignment + compliance.
- Modify `src/App.tsx` — add two routes.
- Modify `src/components/layout/AdminLayout.tsx` — add a nav item.
- Create `src/pages/admin/__tests__/DepartmentsPage.test.tsx`, `src/pages/admin/__tests__/DepartmentDetailPage.test.tsx`.

---

## Task 1: New SQLAlchemy models

**Files:**
- Modify: `backend/models/models.py` (append new classes after the `Enrollment` class, ~line 162)
- Modify: `backend/models/__init__.py`
- Test: `backend/tests/test_departments_models.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_departments_models.py`:

```python
"""Model-level tests for departments, membership, and content assignment."""
import pytest
from sqlalchemy.exc import IntegrityError

from models import Department, DepartmentMember, DepartmentContent, User, UserRole, Course, CourseStatus
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


def test_deleting_department_cascades_members_and_content(db):
    creator = _user(db, "creator2")
    d = Department(name="Legal"); db.add(d); db.commit(); db.refresh(d)
    u = _user(db, "bob")
    c = _course(db, creator.id)
    db.add(DepartmentMember(department_id=d.id, user_id=u.id))
    db.add(DepartmentContent(department_id=d.id, course_id=c.id))
    db.commit()

    db.delete(d); db.commit()
    assert db.query(DepartmentMember).filter(DepartmentMember.department_id == d.id).count() == 0
    assert db.query(DepartmentContent).filter(DepartmentContent.department_id == d.id).count() == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_departments_models.py -v`
Expected: FAIL — `ImportError: cannot import name 'Department' from 'models'`.

- [ ] **Step 3: Add the model classes**

In `backend/models/models.py`, append after the `Enrollment` class (after ~line 162):

```python
class Department(Base):
    """A group of users that courses/podcasts can be assigned to."""

    __tablename__ = "departments"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    members = relationship(
        "DepartmentMember", back_populates="department", cascade="all, delete-orphan"
    )
    content = relationship(
        "DepartmentContent", back_populates="department", cascade="all, delete-orphan"
    )


class DepartmentMember(Base):
    """Join row: a user belongs to a department (many-to-many)."""

    __tablename__ = "department_members"

    id = Column(Integer, primary_key=True, index=True)
    department_id = Column(Integer, ForeignKey("departments.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    added_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    department = relationship("Department", back_populates="members")
    user = relationship("User")

    __table_args__ = (
        UniqueConstraint("department_id", "user_id", name="uq_department_user"),
        Index("idx_department_member_user", "user_id"),
        Index("idx_department_member_dept", "department_id"),
    )


class DepartmentContent(Base):
    """A course/podcast assigned to a department, optionally mandatory with a deadline.

    A "podcast" is a Course with ilb_published=true; there is no separate entity.
    due_mode is 'fixed' (use due_date) or 'relative' (use due_days from each user's
    enrolment date), or None for a mandatory item with no hard deadline.
    """

    __tablename__ = "department_content"

    id = Column(Integer, primary_key=True, index=True)
    department_id = Column(Integer, ForeignKey("departments.id", ondelete="CASCADE"), nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    mandatory = Column(Boolean, default=False, nullable=False)
    due_mode = Column(String(20), nullable=True)
    due_date = Column(DateTime, nullable=True)
    due_days = Column(Integer, nullable=True)
    assigned_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    department = relationship("Department", back_populates="content")
    course = relationship("Course")

    __table_args__ = (
        UniqueConstraint("department_id", "course_id", name="uq_department_course"),
        Index("idx_department_content_course", "course_id"),
    )
```

- [ ] **Step 4: Export the new models**

In `backend/models/__init__.py`, add `Department`, `DepartmentMember`, `DepartmentContent` to BOTH the `from .models import (...)` block and the `__all__` list (e.g. after `SessionAttestation,` in each):

```python
    SessionAttestation,
    Department,
    DepartmentMember,
    DepartmentContent,
)
```

and in `__all__`:

```python
    "SessionAttestation",
    "Department",
    "DepartmentMember",
    "DepartmentContent",
]
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_departments_models.py -v`
Expected: PASS (5 tests).

- [ ] **Step 6: Commit**

```bash
cd backend && git add models/models.py models/__init__.py tests/test_departments_models.py
git commit -m "feat(departments): add Department, DepartmentMember, DepartmentContent models"
```

---

## Task 2: Alembic migration 010

**Files:**
- Create: `backend/alembic/versions/010_departments.py`

This migration is for the real (prod) SQLite DB; tests build their schema from the models, so no test drives it. Verify it imports cleanly and chains from `009`.

- [ ] **Step 1: Write the migration**

Create `backend/alembic/versions/010_departments.py`:

```python
"""Add departments, department_members, department_content tables.

Departments group users; courses/podcasts are assigned to a department and optionally
marked mandatory with a deadline. See docs/superpowers/specs/2026-05-23-departments-design.md.

Revision ID: 010
Revises: 009
Create Date: 2026-05-23
"""
from alembic import op
import sqlalchemy as sa

revision = '010'
down_revision = '009'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'departments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name', name='uq_department_name'),
    )

    op.create_table(
        'department_members',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('department_id', sa.Integer(), sa.ForeignKey('departments.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('added_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('department_id', 'user_id', name='uq_department_user'),
    )
    op.create_index('idx_department_member_user', 'department_members', ['user_id'])
    op.create_index('idx_department_member_dept', 'department_members', ['department_id'])

    op.create_table(
        'department_content',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('department_id', sa.Integer(), sa.ForeignKey('departments.id', ondelete='CASCADE'), nullable=False),
        sa.Column('course_id', sa.Integer(), sa.ForeignKey('courses.id', ondelete='CASCADE'), nullable=False),
        sa.Column('mandatory', sa.Boolean(), server_default='0', nullable=False),
        sa.Column('due_mode', sa.String(length=20), nullable=True),
        sa.Column('due_date', sa.DateTime(), nullable=True),
        sa.Column('due_days', sa.Integer(), nullable=True),
        sa.Column('assigned_by', sa.Integer(), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('department_id', 'course_id', name='uq_department_course'),
    )
    op.create_index('idx_department_content_course', 'department_content', ['course_id'])


def downgrade() -> None:
    op.drop_index('idx_department_content_course', table_name='department_content')
    op.drop_table('department_content')
    op.drop_index('idx_department_member_dept', table_name='department_members')
    op.drop_index('idx_department_member_user', table_name='department_members')
    op.drop_table('department_members')
    op.drop_table('departments')
```

- [ ] **Step 2: Verify it imports and the revision chain is correct**

Run: `cd backend && python -c "import importlib.util, pathlib; p='alembic/versions/010_departments.py'; s=importlib.util.spec_from_file_location('m010', p); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); print('revision', m.revision, 'down_revision', m.down_revision)"`
Expected: `revision 010 down_revision 009`

- [ ] **Step 3: (Best-effort) apply the migration to the real DB**

Run: `cd backend && alembic upgrade head`
Expected: completes without error (slow on iCloud — allow several minutes). If `alembic` is not available in this environment, skip; the models + tests cover schema correctness.

- [ ] **Step 4: Commit**

```bash
cd backend && git add alembic/versions/010_departments.py
git commit -m "feat(departments): migration 010 creates department tables"
```

---

## Task 3: Department service (enrollment sync + status helpers)

**Files:**
- Create: `backend/services/department_service.py`
- Test: `backend/tests/test_department_service.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_department_service.py`:

```python
"""Unit tests for department_service: enrolment sync, due-date and status logic."""
from datetime import datetime, timedelta

from models import (
    Department, DepartmentMember, DepartmentContent,
    Enrollment, User, UserRole, Course, CourseStatus,
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
    creator = _user(db, "creator")
    u1 = _user(db, "u1"); u2 = _user(db, "u2")
    d = _dept(db); c = _course(db, creator.id)
    db.add(DepartmentMember(department_id=d.id, user_id=u1.id))
    db.add(DepartmentMember(department_id=d.id, user_id=u2.id))
    db.commit()

    svc.sync_assignment_enrollments(db, d.id, c.id)
    assert db.query(Enrollment).filter(Enrollment.course_id == c.id).count() == 2


def test_sync_member_enrolls_in_all_department_content(db):
    creator = _user(db, "creator")
    u = _user(db, "newjoiner")
    d = _dept(db)
    c1 = _course(db, creator.id, "A"); c2 = _course(db, creator.id, "B")
    db.add(DepartmentContent(department_id=d.id, course_id=c1.id))
    db.add(DepartmentContent(department_id=d.id, course_id=c2.id))
    db.add(DepartmentMember(department_id=d.id, user_id=u.id))
    db.commit()

    svc.sync_member_enrollments(db, d.id, u.id)
    assert db.query(Enrollment).filter(Enrollment.user_id == u.id).count() == 2


def test_effective_due_date_fixed_and_relative():
    fixed = DepartmentContent(mandatory=True, due_mode="fixed",
                              due_date=datetime(2026, 6, 30))
    assert svc.effective_due_date(fixed, datetime(2026, 1, 1)) == datetime(2026, 6, 30)

    rel = DepartmentContent(mandatory=True, due_mode="relative", due_days=30)
    enrolled = datetime(2026, 1, 1)
    assert svc.effective_due_date(rel, enrolled) == enrolled + timedelta(days=30)

    not_mand = DepartmentContent(mandatory=False, due_mode="fixed", due_date=datetime(2026, 6, 30))
    assert svc.effective_due_date(not_mand, enrolled) is None

    no_deadline = DepartmentContent(mandatory=True, due_mode=None)
    assert svc.effective_due_date(no_deadline, enrolled) is None


def test_status_for():
    now = datetime(2026, 5, 23)
    completed = Enrollment(user_id=1, course_id=1, completed=True, progress=100.0)
    assert svc.status_for(completed, due=datetime(2026, 1, 1), now=now) == "completed"

    overdue = Enrollment(user_id=1, course_id=1, completed=False, progress=10.0)
    assert svc.status_for(overdue, due=datetime(2026, 1, 1), now=now) == "overdue"

    in_prog = Enrollment(user_id=1, course_id=1, completed=False, progress=10.0)
    assert svc.status_for(in_prog, due=datetime(2026, 12, 1), now=now) == "in_progress"

    not_started = Enrollment(user_id=1, course_id=1, completed=False, progress=0.0)
    assert svc.status_for(not_started, due=None, now=now) == "not_started"
    assert svc.status_for(None, due=None, now=now) == "not_started"


def test_effective_due_for_user_picks_earliest_across_departments(db):
    creator = _user(db, "creator"); u = _user(db, "multi")
    c = _course(db, creator.id)
    d1 = _dept(db, "D1"); d2 = _dept(db, "D2")
    db.add(DepartmentMember(department_id=d1.id, user_id=u.id))
    db.add(DepartmentMember(department_id=d2.id, user_id=u.id))
    db.add(DepartmentContent(department_id=d1.id, course_id=c.id, mandatory=True,
                             due_mode="fixed", due_date=datetime(2026, 9, 1)))
    db.add(DepartmentContent(department_id=d2.id, course_id=c.id, mandatory=True,
                             due_mode="fixed", due_date=datetime(2026, 7, 1)))
    db.commit()
    svc.ensure_enrollment(db, u.id, c.id); db.commit()

    assert svc.is_mandatory_for_user(db, u.id, c.id) is True
    assert svc.effective_due_for_user(db, u.id, c.id) == datetime(2026, 7, 1)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_department_service.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'services.department_service'`.

- [ ] **Step 3: Implement the service**

Create `backend/services/department_service.py`:

```python
"""Business logic for departments: enrolment sync + compliance computation.

"Required" is derived from current membership + current assignments, never from the
presence of an enrolment row. Enrolments are find-or-created so progress/completion has
somewhere to live, but removing a member or unassigning content never deletes them.
"""
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from sqlalchemy.orm import Session

from models import Enrollment, DepartmentMember, DepartmentContent


def _as_naive_utc(dt: Optional[datetime]) -> Optional[datetime]:
    """Normalise a datetime to naive UTC so it compares safely with stored values."""
    if dt is None:
        return None
    if dt.tzinfo is not None:
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def ensure_enrollment(db: Session, user_id: int, course_id: int) -> Enrollment:
    """Find-or-create an enrolment for (user, course). Caller commits. Idempotent."""
    enrollment = (
        db.query(Enrollment)
        .filter(Enrollment.user_id == user_id, Enrollment.course_id == course_id)
        .first()
    )
    if enrollment is None:
        enrollment = Enrollment(user_id=user_id, course_id=course_id, course_version=1)
        db.add(enrollment)
        db.flush()
    return enrollment


def sync_assignment_enrollments(db: Session, department_id: int, course_id: int) -> None:
    """Ensure every current member of the department is enrolled in the course."""
    member_ids = [
        m.user_id
        for m in db.query(DepartmentMember)
        .filter(DepartmentMember.department_id == department_id)
        .all()
    ]
    for uid in member_ids:
        ensure_enrollment(db, uid, course_id)
    db.commit()


def sync_member_enrollments(db: Session, department_id: int, user_id: int) -> None:
    """Ensure a member is enrolled in every course assigned to the department."""
    course_ids = [
        c.course_id
        for c in db.query(DepartmentContent)
        .filter(DepartmentContent.department_id == department_id)
        .all()
    ]
    for cid in course_ids:
        ensure_enrollment(db, user_id, cid)
    db.commit()


def effective_due_date(content: DepartmentContent, enrolled_at: Optional[datetime]) -> Optional[datetime]:
    """Deadline for one assignment given a user's enrolment time (naive UTC), or None."""
    if not content.mandatory:
        return None
    if content.due_mode == "fixed":
        return _as_naive_utc(content.due_date)
    if content.due_mode == "relative" and content.due_days is not None and enrolled_at is not None:
        return _as_naive_utc(enrolled_at) + timedelta(days=content.due_days)
    return None


def status_for(enrollment: Optional[Enrollment], due: Optional[datetime],
               now: Optional[datetime] = None) -> str:
    """Return one of: not_started | in_progress | completed | overdue."""
    now = now or datetime.utcnow()
    if enrollment is not None and enrollment.completed:
        return "completed"
    if due is not None and due < now:
        return "overdue"
    if enrollment is not None and (enrollment.progress or 0) > 0:
        return "in_progress"
    return "not_started"


def mandatory_assignments_for_user(db: Session, user_id: int, course_id: int) -> List[DepartmentContent]:
    """All mandatory assignments of a course across the user's departments."""
    dept_ids = [
        m.department_id
        for m in db.query(DepartmentMember)
        .filter(DepartmentMember.user_id == user_id)
        .all()
    ]
    if not dept_ids:
        return []
    return (
        db.query(DepartmentContent)
        .filter(
            DepartmentContent.course_id == course_id,
            DepartmentContent.department_id.in_(dept_ids),
            DepartmentContent.mandatory.is_(True),
        )
        .all()
    )


def is_mandatory_for_user(db: Session, user_id: int, course_id: int) -> bool:
    return len(mandatory_assignments_for_user(db, user_id, course_id)) > 0


def effective_due_for_user(db: Session, user_id: int, course_id: int) -> Optional[datetime]:
    """Earliest deadline across the user's departments for a mandatory course."""
    enrollment = (
        db.query(Enrollment)
        .filter(Enrollment.user_id == user_id, Enrollment.course_id == course_id)
        .first()
    )
    enrolled_at = enrollment.enrolled_at if enrollment else None
    dues = [
        d
        for d in (
            effective_due_date(a, enrolled_at)
            for a in mandatory_assignments_for_user(db, user_id, course_id)
        )
        if d is not None
    ]
    return min(dues) if dues else None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_department_service.py -v`
Expected: PASS (6 tests).

- [ ] **Step 5: Commit**

```bash
cd backend && git add services/department_service.py tests/test_department_service.py
git commit -m "feat(departments): enrolment sync + due-date/status service"
```

---

## Task 4: Departments router — CRUD + register

**Files:**
- Create: `backend/routers/departments.py`
- Modify: `backend/main.py`
- Test: `backend/tests/test_departments_router.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_departments_router.py`:

```python
"""Integration tests for the departments router."""
import pytest

from models import Department


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def test_requires_admin(client, trainee_token):
    r = client.get("/api/departments", headers=_auth(trainee_token))
    assert r.status_code == 403


def test_create_list_get_update_delete(client, db, admin_token):
    # create
    r = client.post("/api/departments", json={"name": "Operations", "description": "Ops"},
                    headers=_auth(admin_token))
    assert r.status_code == 201, r.text
    dept_id = r.json()["id"]
    assert r.json()["member_count"] == 0
    assert r.json()["content_count"] == 0

    # duplicate name -> 409
    r = client.post("/api/departments", json={"name": "Operations"}, headers=_auth(admin_token))
    assert r.status_code == 409

    # list
    r = client.get("/api/departments", headers=_auth(admin_token))
    assert r.status_code == 200
    assert any(d["id"] == dept_id for d in r.json())

    # get detail
    r = client.get(f"/api/departments/{dept_id}", headers=_auth(admin_token))
    assert r.status_code == 200
    assert r.json()["members"] == []
    assert r.json()["content"] == []

    # update
    r = client.put(f"/api/departments/{dept_id}", json={"is_active": False},
                   headers=_auth(admin_token))
    assert r.status_code == 200
    assert r.json()["is_active"] is False

    # delete
    r = client.delete(f"/api/departments/{dept_id}", headers=_auth(admin_token))
    assert r.status_code == 200
    assert db.query(Department).filter(Department.id == dept_id).first() is None


def test_get_missing_department_404(client, admin_token):
    r = client.get("/api/departments/9999", headers=_auth(admin_token))
    assert r.status_code == 404
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_departments_router.py -v`
Expected: FAIL — 404s for `/api/departments` (router not registered).

- [ ] **Step 3: Create the router with schemas + CRUD**

Create `backend/routers/departments.py`:

```python
"""Department management routes (admin-only).

Departments group users; courses/podcasts are assigned to a department and optionally
made mandatory with a deadline. Adding a member or assigning content auto-enrols affected
users so progress/completion can be tracked. Removing a member or unassigning content
leaves enrolments (and audit history) intact. See
docs/superpowers/specs/2026-05-23-departments-design.md.
"""
import logging
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models import User, Course, Enrollment, Department, DepartmentMember, DepartmentContent
from middleware.auth_middleware import require_admin
from services import department_service as dept_svc

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/departments", tags=["departments"])


# --------------------------------------------------------------------------- schemas

class DepartmentCreate(BaseModel):
    name: str
    description: Optional[str] = None


class DepartmentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class DepartmentSummary(BaseModel):
    id: int
    name: str
    description: Optional[str]
    is_active: bool
    member_count: int
    content_count: int


class MemberResponse(BaseModel):
    id: int
    username: str
    email: str
    role: str


class ContentResponse(BaseModel):
    id: int
    course_id: int
    course_title: str
    is_podcast: bool
    mandatory: bool
    due_mode: Optional[str]
    due_date: Optional[datetime]
    due_days: Optional[int]


class DepartmentDetail(BaseModel):
    id: int
    name: str
    description: Optional[str]
    is_active: bool
    members: List[MemberResponse]
    content: List[ContentResponse]


class AddMembersRequest(BaseModel):
    user_ids: List[int]


class AssignContentRequest(BaseModel):
    course_id: int
    mandatory: bool = False
    due_mode: Optional[str] = None
    due_date: Optional[datetime] = None
    due_days: Optional[int] = None


class ContentUpdateRequest(BaseModel):
    mandatory: Optional[bool] = None
    due_mode: Optional[str] = None
    due_date: Optional[datetime] = None
    due_days: Optional[int] = None


class ComplianceItem(BaseModel):
    content_id: int
    course_id: int
    course_title: str
    mandatory: bool
    total_members: int
    not_started: int
    in_progress: int
    completed: int
    overdue: int


class ComplianceResponse(BaseModel):
    department_id: int
    items: List[ComplianceItem]


# --------------------------------------------------------------------------- helpers

def _get_department(db: Session, department_id: int) -> Department:
    dept = db.query(Department).filter(Department.id == department_id).first()
    if not dept:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Department not found")
    return dept


def _validate_due_config(mandatory, due_mode, due_date, due_days) -> None:
    if not mandatory or due_mode is None:
        return
    if due_mode not in ("fixed", "relative"):
        raise HTTPException(status_code=400, detail="due_mode must be 'fixed' or 'relative'")
    if due_mode == "fixed" and due_date is None:
        raise HTTPException(status_code=400, detail="due_date is required when due_mode is 'fixed'")
    if due_mode == "relative" and (due_days is None or due_days <= 0):
        raise HTTPException(status_code=400, detail="due_days must be a positive integer when due_mode is 'relative'")


def _member_response(m: DepartmentMember) -> MemberResponse:
    return MemberResponse(id=m.user.id, username=m.user.username, email=m.user.email, role=m.user.role.value)


def _content_response(c: DepartmentContent) -> ContentResponse:
    return ContentResponse(
        id=c.id,
        course_id=c.course_id,
        course_title=c.course.title if c.course else "",
        is_podcast=bool(c.course.ilb_published) if c.course else False,
        mandatory=c.mandatory,
        due_mode=c.due_mode,
        due_date=c.due_date,
        due_days=c.due_days,
    )


def _summary(d: Department) -> DepartmentSummary:
    return DepartmentSummary(
        id=d.id, name=d.name, description=d.description, is_active=d.is_active,
        member_count=len(d.members), content_count=len(d.content),
    )


# --------------------------------------------------------------------------- department CRUD

@router.get("", response_model=List[DepartmentSummary])
def list_departments(db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    return [_summary(d) for d in db.query(Department).order_by(Department.name).all()]


@router.post("", response_model=DepartmentSummary, status_code=status.HTTP_201_CREATED)
def create_department(body: DepartmentCreate, db: Session = Depends(get_db),
                      current_user: User = Depends(require_admin)):
    if db.query(Department).filter(Department.name == body.name).first():
        raise HTTPException(status_code=409, detail="A department with this name already exists")
    d = Department(name=body.name, description=body.description)
    db.add(d)
    db.commit()
    db.refresh(d)
    logger.info("Department created: %s by admin %s", d.name, current_user.id)
    return _summary(d)


@router.get("/{department_id}", response_model=DepartmentDetail)
def get_department(department_id: int, db: Session = Depends(get_db),
                   current_user: User = Depends(require_admin)):
    d = _get_department(db, department_id)
    return DepartmentDetail(
        id=d.id, name=d.name, description=d.description, is_active=d.is_active,
        members=[_member_response(m) for m in d.members if m.user],
        content=[_content_response(c) for c in d.content],
    )


@router.put("/{department_id}", response_model=DepartmentSummary)
def update_department(department_id: int, body: DepartmentUpdate, db: Session = Depends(get_db),
                      current_user: User = Depends(require_admin)):
    d = _get_department(db, department_id)
    if body.name is not None and body.name != d.name:
        if db.query(Department).filter(Department.name == body.name, Department.id != d.id).first():
            raise HTTPException(status_code=409, detail="A department with this name already exists")
        d.name = body.name
    if body.description is not None:
        d.description = body.description
    if body.is_active is not None:
        d.is_active = body.is_active
    db.commit()
    db.refresh(d)
    return _summary(d)


@router.delete("/{department_id}")
def delete_department(department_id: int, db: Session = Depends(get_db),
                      current_user: User = Depends(require_admin)):
    d = _get_department(db, department_id)
    db.delete(d)  # cascades members + content; enrolments are untouched
    db.commit()
    logger.info("Department deleted: %s by admin %s", department_id, current_user.id)
    return {"message": "Department deleted"}
```

- [ ] **Step 4: Register the router in main.py**

In `backend/main.py`, add `departments` to the routers import (line 26):

```python
from routers import admin, auth, users, courses, security, dev_tools, whitelabel, learn, creator, uploads, modules, videos, slides, blocks, quizzes, tts as tts_router_module, content_generation, ilb, departments
```

And add the include after `app.include_router(ilb.router)` (~line 215):

```python
app.include_router(ilb.router)
app.include_router(departments.router)
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_departments_router.py -v`
Expected: PASS (3 tests).

- [ ] **Step 6: Commit**

```bash
cd backend && git add routers/departments.py main.py tests/test_departments_router.py
git commit -m "feat(departments): department CRUD endpoints (admin-only)"
```

---

## Task 5: Members endpoints + auto-enroll

**Files:**
- Modify: `backend/routers/departments.py` (append member endpoints)
- Test: `backend/tests/test_departments_router.py` (append)

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_departments_router.py`:

```python
from models import Enrollment, DepartmentContent, DepartmentMember, Course, CourseStatus


def _make_dept(client, admin_token, name="Ops"):
    r = client.post("/api/departments", json={"name": name}, headers=_auth(admin_token))
    return r.json()["id"]


def _make_course(db, creator_id, title="C1"):
    c = Course(title=title, status=CourseStatus.PUBLISHED, creator_id=creator_id)
    db.add(c); db.commit(); db.refresh(c)
    return c


def test_add_and_remove_members(client, db, admin_token, admin_user, trainee_user):
    dept_id = _make_dept(client, admin_token)

    r = client.post(f"/api/departments/{dept_id}/members",
                    json={"user_ids": [trainee_user.id]}, headers=_auth(admin_token))
    assert r.status_code == 200, r.text
    assert any(m["id"] == trainee_user.id for m in r.json())

    # adding the same user again is a no-op (no duplicate)
    r = client.post(f"/api/departments/{dept_id}/members",
                    json={"user_ids": [trainee_user.id]}, headers=_auth(admin_token))
    assert r.status_code == 200
    assert db.query(DepartmentMember).filter(DepartmentMember.department_id == dept_id).count() == 1

    # unknown user -> 400
    r = client.post(f"/api/departments/{dept_id}/members",
                    json={"user_ids": [99999]}, headers=_auth(admin_token))
    assert r.status_code == 400

    # remove member; enrolments (if any) are left intact
    r = client.delete(f"/api/departments/{dept_id}/members/{trainee_user.id}",
                      headers=_auth(admin_token))
    assert r.status_code == 200
    assert db.query(DepartmentMember).filter(DepartmentMember.department_id == dept_id).count() == 0


def test_new_member_inherits_existing_assignments(client, db, admin_token, admin_user, trainee_user):
    dept_id = _make_dept(client, admin_token, name="Compliance")
    course = _make_course(db, admin_user.id)
    # assign content first
    r = client.post(f"/api/departments/{dept_id}/content",
                    json={"course_id": course.id, "mandatory": True}, headers=_auth(admin_token))
    assert r.status_code == 201, r.text
    # then add a member -> they should get auto-enrolled in the course
    r = client.post(f"/api/departments/{dept_id}/members",
                    json={"user_ids": [trainee_user.id]}, headers=_auth(admin_token))
    assert r.status_code == 200
    assert db.query(Enrollment).filter(
        Enrollment.user_id == trainee_user.id, Enrollment.course_id == course.id
    ).count() == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_departments_router.py -k members -v`
Expected: FAIL — 405/404 on `/members` (endpoints not defined). `test_new_member_inherits_existing_assignments` also fails (no `/content`).

- [ ] **Step 3: Append member endpoints to the router**

Append to `backend/routers/departments.py`:

```python
# --------------------------------------------------------------------------- members

@router.get("/{department_id}/members", response_model=List[MemberResponse])
def list_members(department_id: int, db: Session = Depends(get_db),
                 current_user: User = Depends(require_admin)):
    d = _get_department(db, department_id)
    return [_member_response(m) for m in d.members if m.user]


@router.post("/{department_id}/members", response_model=List[MemberResponse])
def add_members(department_id: int, body: AddMembersRequest, db: Session = Depends(get_db),
                current_user: User = Depends(require_admin)):
    d = _get_department(db, department_id)
    unique_ids = list(set(body.user_ids))
    users = db.query(User).filter(User.id.in_(unique_ids)).all()
    if len(users) != len(unique_ids):
        raise HTTPException(status_code=400, detail="One or more users not found")

    existing = {m.user_id for m in d.members}
    added = [u for u in users if u.id not in existing]
    for u in added:
        db.add(DepartmentMember(department_id=department_id, user_id=u.id))
    db.commit()

    for u in added:
        dept_svc.sync_member_enrollments(db, department_id, u.id)

    db.refresh(d)
    return [_member_response(m) for m in d.members if m.user]


@router.delete("/{department_id}/members/{user_id}")
def remove_member(department_id: int, user_id: int, db: Session = Depends(get_db),
                  current_user: User = Depends(require_admin)):
    _get_department(db, department_id)
    m = (
        db.query(DepartmentMember)
        .filter(DepartmentMember.department_id == department_id, DepartmentMember.user_id == user_id)
        .first()
    )
    if not m:
        raise HTTPException(status_code=404, detail="Member not found in this department")
    db.delete(m)  # enrolments are intentionally left intact
    db.commit()
    return {"message": "Member removed"}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_departments_router.py -v`
Expected: PASS (5 tests total in the file).

- [ ] **Step 5: Commit**

```bash
cd backend && git add routers/departments.py tests/test_departments_router.py
git commit -m "feat(departments): member add/remove with auto-enrol"
```

---

## Task 6: Content assignment endpoints + auto-enroll

**Files:**
- Modify: `backend/routers/departments.py` (append content endpoints)
- Test: `backend/tests/test_departments_router.py` (append)

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_departments_router.py`:

```python
def test_assign_content_enrolls_members_and_validates(client, db, admin_token, admin_user, trainee_user):
    dept_id = _make_dept(client, admin_token, name="Safety")
    course = _make_course(db, admin_user.id, "Fire Safety")
    # member first
    client.post(f"/api/departments/{dept_id}/members",
                json={"user_ids": [trainee_user.id]}, headers=_auth(admin_token))

    # assign mandatory with a fixed date -> existing member gets enrolled
    r = client.post(f"/api/departments/{dept_id}/content",
                    json={"course_id": course.id, "mandatory": True,
                          "due_mode": "fixed", "due_date": "2026-06-30T00:00:00"},
                    headers=_auth(admin_token))
    assert r.status_code == 201, r.text
    content_id = r.json()["id"]
    assert r.json()["mandatory"] is True
    assert r.json()["due_mode"] == "fixed"
    assert db.query(Enrollment).filter(
        Enrollment.user_id == trainee_user.id, Enrollment.course_id == course.id
    ).count() == 1

    # duplicate assignment -> 409
    r = client.post(f"/api/departments/{dept_id}/content",
                    json={"course_id": course.id}, headers=_auth(admin_token))
    assert r.status_code == 409

    # missing course -> 404
    r = client.post(f"/api/departments/{dept_id}/content",
                    json={"course_id": 99999}, headers=_auth(admin_token))
    assert r.status_code == 404

    # update to relative
    r = client.put(f"/api/departments/{dept_id}/content/{content_id}",
                   json={"mandatory": True, "due_mode": "relative", "due_days": 14},
                   headers=_auth(admin_token))
    assert r.status_code == 200
    assert r.json()["due_mode"] == "relative"
    assert r.json()["due_days"] == 14
    assert r.json()["due_date"] is None

    # unassign -> enrolment is left intact
    r = client.delete(f"/api/departments/{dept_id}/content/{content_id}", headers=_auth(admin_token))
    assert r.status_code == 200
    assert db.query(DepartmentContent).filter(DepartmentContent.id == content_id).first() is None
    assert db.query(Enrollment).filter(
        Enrollment.user_id == trainee_user.id, Enrollment.course_id == course.id
    ).count() == 1


def test_assign_invalid_due_config_400(client, db, admin_token, admin_user):
    dept_id = _make_dept(client, admin_token, name="BadDue")
    course = _make_course(db, admin_user.id, "X")
    # fixed without a date
    r = client.post(f"/api/departments/{dept_id}/content",
                    json={"course_id": course.id, "mandatory": True, "due_mode": "fixed"},
                    headers=_auth(admin_token))
    assert r.status_code == 400
    # relative with non-positive days
    r = client.post(f"/api/departments/{dept_id}/content",
                    json={"course_id": course.id, "mandatory": True,
                          "due_mode": "relative", "due_days": 0},
                    headers=_auth(admin_token))
    assert r.status_code == 400
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_departments_router.py -k "content or due" -v`
Expected: FAIL — `/content` endpoints not defined.

- [ ] **Step 3: Append content endpoints to the router**

Append to `backend/routers/departments.py`:

```python
# --------------------------------------------------------------------------- content

@router.get("/{department_id}/content", response_model=List[ContentResponse])
def list_content(department_id: int, db: Session = Depends(get_db),
                 current_user: User = Depends(require_admin)):
    d = _get_department(db, department_id)
    return [_content_response(c) for c in d.content]


@router.post("/{department_id}/content", response_model=ContentResponse,
             status_code=status.HTTP_201_CREATED)
def assign_content(department_id: int, body: AssignContentRequest, db: Session = Depends(get_db),
                   current_user: User = Depends(require_admin)):
    _get_department(db, department_id)
    course = db.query(Course).filter(Course.id == body.course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    if (
        db.query(DepartmentContent)
        .filter(DepartmentContent.department_id == department_id,
                DepartmentContent.course_id == body.course_id)
        .first()
    ):
        raise HTTPException(status_code=409, detail="This content is already assigned to the department")

    _validate_due_config(body.mandatory, body.due_mode, body.due_date, body.due_days)

    c = DepartmentContent(
        department_id=department_id,
        course_id=body.course_id,
        mandatory=body.mandatory,
        due_mode=body.due_mode if body.mandatory else None,
        due_date=body.due_date if body.mandatory and body.due_mode == "fixed" else None,
        due_days=body.due_days if body.mandatory and body.due_mode == "relative" else None,
        assigned_by=current_user.id,
    )
    db.add(c)
    db.commit()
    db.refresh(c)

    dept_svc.sync_assignment_enrollments(db, department_id, body.course_id)
    db.refresh(c)
    return _content_response(c)


@router.put("/{department_id}/content/{content_id}", response_model=ContentResponse)
def update_content(department_id: int, content_id: int, body: ContentUpdateRequest,
                   db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    _get_department(db, department_id)
    c = (
        db.query(DepartmentContent)
        .filter(DepartmentContent.id == content_id,
                DepartmentContent.department_id == department_id)
        .first()
    )
    if not c:
        raise HTTPException(status_code=404, detail="Assignment not found")

    mandatory = body.mandatory if body.mandatory is not None else c.mandatory
    due_mode = body.due_mode if body.due_mode is not None else c.due_mode
    due_date = body.due_date if body.due_date is not None else c.due_date
    due_days = body.due_days if body.due_days is not None else c.due_days
    _validate_due_config(mandatory, due_mode, due_date, due_days)

    c.mandatory = mandatory
    c.due_mode = due_mode if mandatory else None
    c.due_date = due_date if mandatory and due_mode == "fixed" else None
    c.due_days = due_days if mandatory and due_mode == "relative" else None
    db.commit()
    db.refresh(c)
    return _content_response(c)


@router.delete("/{department_id}/content/{content_id}")
def unassign_content(department_id: int, content_id: int, db: Session = Depends(get_db),
                     current_user: User = Depends(require_admin)):
    _get_department(db, department_id)
    c = (
        db.query(DepartmentContent)
        .filter(DepartmentContent.id == content_id,
                DepartmentContent.department_id == department_id)
        .first()
    )
    if not c:
        raise HTTPException(status_code=404, detail="Assignment not found")
    db.delete(c)  # enrolments are intentionally left intact
    db.commit()
    return {"message": "Content unassigned"}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_departments_router.py -v`
Expected: PASS (7 tests total in the file).

- [ ] **Step 5: Commit**

```bash
cd backend && git add routers/departments.py tests/test_departments_router.py
git commit -m "feat(departments): content assignment endpoints with auto-enrol + validation"
```

---

## Task 7: Compliance endpoint

**Files:**
- Modify: `backend/routers/departments.py` (append compliance endpoint)
- Test: `backend/tests/test_departments_router.py` (append)

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_departments_router.py`:

```python
from datetime import datetime, timedelta


def test_compliance_counts(client, db, admin_token, admin_user, trainee_user):
    dept_id = _make_dept(client, admin_token, name="Counts")
    course = _make_course(db, admin_user.id, "Compliance 101")
    client.post(f"/api/departments/{dept_id}/members",
                json={"user_ids": [trainee_user.id]}, headers=_auth(admin_token))
    # mandatory, fixed date already in the past -> the not-yet-started member is OVERDUE
    client.post(f"/api/departments/{dept_id}/content",
                json={"course_id": course.id, "mandatory": True,
                      "due_mode": "fixed", "due_date": "2020-01-01T00:00:00"},
                headers=_auth(admin_token))

    r = client.get(f"/api/departments/{dept_id}/compliance", headers=_auth(admin_token))
    assert r.status_code == 200, r.text
    item = r.json()["items"][0]
    assert item["total_members"] == 1
    assert item["overdue"] == 1
    assert item["completed"] == 0

    # now mark the enrolment complete -> compliance flips to completed
    enr = db.query(Enrollment).filter(
        Enrollment.user_id == trainee_user.id, Enrollment.course_id == course.id
    ).first()
    enr.completed = True
    db.commit()

    r = client.get(f"/api/departments/{dept_id}/compliance", headers=_auth(admin_token))
    item = r.json()["items"][0]
    assert item["completed"] == 1
    assert item["overdue"] == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_departments_router.py -k compliance -v`
Expected: FAIL — `/compliance` not defined (404).

- [ ] **Step 3: Append the compliance endpoint**

Append to `backend/routers/departments.py`:

```python
# --------------------------------------------------------------------------- compliance

@router.get("/{department_id}/compliance", response_model=ComplianceResponse)
def department_compliance(department_id: int, db: Session = Depends(get_db),
                          current_user: User = Depends(require_admin)):
    d = _get_department(db, department_id)
    member_ids = [m.user_id for m in d.members]
    now = datetime.utcnow()
    items: List[ComplianceItem] = []
    for c in d.content:
        counts = {"not_started": 0, "in_progress": 0, "completed": 0, "overdue": 0}
        for uid in member_ids:
            enr = (
                db.query(Enrollment)
                .filter(Enrollment.user_id == uid, Enrollment.course_id == c.course_id)
                .first()
            )
            due = dept_svc.effective_due_date(c, enr.enrolled_at if enr else None)
            counts[dept_svc.status_for(enr, due, now)] += 1
        items.append(ComplianceItem(
            content_id=c.id, course_id=c.course_id,
            course_title=c.course.title if c.course else "",
            mandatory=c.mandatory, total_members=len(member_ids), **counts,
        ))
    return ComplianceResponse(department_id=department_id, items=items)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_departments_router.py -v`
Expected: PASS (8 tests total in the file).

- [ ] **Step 5: Commit**

```bash
cd backend && git add routers/departments.py tests/test_departments_router.py
git commit -m "feat(departments): per-department compliance summary endpoint"
```

---

## Task 8: Unify completion — broadcast complete marks the enrolment

**Files:**
- Modify: `backend/routers/ilb.py` (`complete_session`, ~line 285–291)
- Test: `backend/tests/test_ilb_router.py` (append)

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_ilb_router.py`:

```python
def test_complete_marks_enrollment_completed(client, db, trainee_token, published_course, enrollment):
    r = client.post(
        "/api/ilb/sessions",
        json={"course_id": published_course.id, "mode": "interrupt"},
        headers=_auth(trainee_token),
    )
    assert r.status_code == 201, r.text
    sid = r.json()["session"]["id"]

    r = client.post(
        f"/api/ilb/sessions/{sid}/complete",
        json={"final_score": 91.0},
        headers=_auth(trainee_token),
    )
    assert r.status_code == 200, r.text

    db.refresh(enrollment)
    assert enrollment.completed is True
    assert enrollment.completed_at is not None
    assert enrollment.progress == 100.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_ilb_router.py::test_complete_marks_enrollment_completed -v`
Expected: FAIL — `enrollment.completed` is still `False` (broadcast completion doesn't touch the enrolment yet).

- [ ] **Step 3: Patch `complete_session`**

In `backend/routers/ilb.py`, inside `complete_session`, replace this block (~lines 285–290):

```python
    bs = _load_owned_session(db, session_id, current_user)
    bs.completion_status = "completed"
    bs.completed_at = datetime.utcnow()
    if body.final_score is not None:
        bs.final_score = body.final_score
    db.commit()
    db.refresh(bs)
```

with:

```python
    bs = _load_owned_session(db, session_id, current_user)
    bs.completion_status = "completed"
    bs.completed_at = datetime.utcnow()
    if body.final_score is not None:
        bs.final_score = body.final_score

    # Unify completion: finishing a broadcast also completes the enrolment, so a mandatory
    # podcast registers as done using the same signal as regular courses
    # (see courses.py update_progress, which sets completed when progress >= 100).
    enrollment = bs.enrollment
    if enrollment is not None and not enrollment.completed:
        enrollment.completed = True
        enrollment.completed_at = bs.completed_at
        enrollment.progress = 100.0

    db.commit()
    db.refresh(bs)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_ilb_router.py -v`
Expected: PASS (existing ILB tests still pass + the new one).

- [ ] **Step 5: Commit**

```bash
cd backend && git add routers/ilb.py tests/test_ilb_router.py
git commit -m "fix(ilb): completing a broadcast also marks the enrolment complete"
```

---

## Task 9: Frontend — Departments list page

**Files:**
- Create: `frontend/src/pages/admin/DepartmentsPage.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/components/layout/AdminLayout.tsx`
- Test: `frontend/src/pages/admin/__tests__/DepartmentsPage.test.tsx`

- [ ] **Step 1: Write the failing test**

Create `frontend/src/pages/admin/__tests__/DepartmentsPage.test.tsx`:

```tsx
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { DepartmentsPage } from '../DepartmentsPage'
import { api } from '@/services/api'

vi.mock('@/services/api', () => ({
  api: { get: vi.fn(), post: vi.fn(), put: vi.fn(), delete: vi.fn() },
}))
vi.mock('@/context/ToastContext', () => ({ useToast: () => ({ showToast: vi.fn() }) }))

const mockedApi = api as unknown as Record<string, ReturnType<typeof vi.fn>>

const ok = (data: unknown) => Promise.resolve({ ok: true, json: async () => data } as Response)

function renderPage() {
  return render(<MemoryRouter><DepartmentsPage /></MemoryRouter>)
}

describe('DepartmentsPage', () => {
  beforeEach(() => vi.clearAllMocks())

  it('lists departments from the API', async () => {
    mockedApi.get.mockReturnValue(ok([
      { id: 1, name: 'Operations', description: 'Ops', is_active: true, member_count: 3, content_count: 2 },
    ]))
    renderPage()
    expect(await screen.findByText('Operations')).toBeInTheDocument()
    expect(screen.getByText(/3 members/)).toBeInTheDocument()
  })

  it('creates a department', async () => {
    mockedApi.get.mockReturnValue(ok([]))
    mockedApi.post.mockReturnValue(ok({ id: 9, name: 'Sales', description: null, is_active: true, member_count: 0, content_count: 0 }))
    renderPage()

    await userEvent.click(await screen.findByText('+ New Department'))
    await userEvent.type(screen.getByPlaceholderText(/e.g. Operations/i), 'Sales')
    await userEvent.click(screen.getByText('Create'))

    expect(mockedApi.post).toHaveBeenCalledWith('/departments', { name: 'Sales', description: '' })
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/pages/admin/__tests__/DepartmentsPage.test.tsx`
Expected: FAIL — cannot resolve `../DepartmentsPage`.

- [ ] **Step 3: Create the page**

Create `frontend/src/pages/admin/DepartmentsPage.tsx`:

```tsx
import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '@/services/api'
import { useToast } from '@/context/ToastContext'
import { Modal } from '@/components/common/Modal'
import { Button } from '@/components/common/Button'
import { Card } from '@/components/common/Card'
import { Input } from '@/components/common/Input'

interface Department {
  id: number
  name: string
  description: string | null
  is_active: boolean
  member_count: number
  content_count: number
}

export const DepartmentsPage = () => {
  const [departments, setDepartments] = useState<Department[]>([])
  const [loading, setLoading] = useState(true)
  const [modalOpen, setModalOpen] = useState(false)
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [formError, setFormError] = useState('')
  const { showToast } = useToast()
  const navigate = useNavigate()

  useEffect(() => { fetchDepartments() }, [])

  const fetchDepartments = async () => {
    setLoading(true)
    try {
      const res = await api.get('/departments')
      if (res.ok) setDepartments(await res.json())
    } catch {
      showToast('Failed to load departments', 'error')
    } finally {
      setLoading(false)
    }
  }

  const handleCreate = async () => {
    setFormError('')
    if (!name.trim()) { setFormError('Name is required'); return }
    const res = await api.post('/departments', { name, description })
    if (res.ok) {
      showToast('Department created', 'success')
      setModalOpen(false); setName(''); setDescription('')
      fetchDepartments()
    } else {
      const err = await res.json().catch(() => ({}))
      setFormError(err.detail || 'Failed to create department')
    }
  }

  const handleDelete = async (id: number) => {
    if (!confirm('Delete this department? Members and assignments are removed; learner progress is kept.')) return
    const res = await api.delete(`/departments/${id}`)
    if (res.ok) { showToast('Department deleted', 'success'); fetchDepartments() }
    else showToast('Failed to delete department', 'error')
  }

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold text-brand-dark">Departments</h1>
        <Button onClick={() => setModalOpen(true)}>+ New Department</Button>
      </div>

      {loading ? (
        <p className="text-gray-500">Loading…</p>
      ) : departments.length === 0 ? (
        <Card><p className="text-gray-500 p-4">No departments yet. Create one to start assigning training.</p></Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {departments.map(d => (
            <Card key={d.id} className="p-4">
              <div className="flex justify-between items-start">
                <button className="text-left" onClick={() => navigate(`/admin/departments/${d.id}`)}>
                  <h3 className="font-semibold text-lg text-brand-dark hover:underline">{d.name}</h3>
                </button>
                <button onClick={() => handleDelete(d.id)} className="text-red-500 text-sm hover:underline">Delete</button>
              </div>
              {d.description && <p className="text-sm text-gray-600 mt-1">{d.description}</p>}
              <div className="flex gap-4 mt-3 text-sm text-gray-500">
                <span>{d.member_count} members</span>
                <span>{d.content_count} assignments</span>
              </div>
            </Card>
          ))}
        </div>
      )}

      <Modal open={modalOpen} onClose={() => setModalOpen(false)} title="New Department">
        <div className="space-y-2">
          {formError && <p className="text-red-500 text-sm">{formError}</p>}
          <Input label="Name" value={name} onChange={e => setName(e.target.value)} placeholder="e.g. Operations" />
          <Input label="Description" value={description} onChange={e => setDescription(e.target.value)} placeholder="Optional" />
          <div className="flex justify-end gap-2">
            <Button variant="secondary" onClick={() => setModalOpen(false)}>Cancel</Button>
            <Button onClick={handleCreate}>Create</Button>
          </div>
        </div>
      </Modal>
    </div>
  )
}
```

- [ ] **Step 4: Add the list route in App.tsx**

In `frontend/src/App.tsx`, add the import alongside the other admin page imports (~line 22):

```tsx
import { DepartmentsPage } from '@/pages/admin/DepartmentsPage'
```

And add the list route inside the Admin routes block (after the `/admin/courses` route, ~line 82). The detail route is added in Task 10 (after its page exists), so the build stays green between tasks:

```tsx
      <Route
        path="/admin/departments"
        element={
          <AdminLayout>
            <ProtectedRoute adminOnly>
              <DepartmentsPage />
            </ProtectedRoute>
          </AdminLayout>
        }
      />
```

- [ ] **Step 5: Add the nav item in AdminLayout.tsx**

In `frontend/src/components/layout/AdminLayout.tsx`, add to `navItems` after the Courses entry (~line 17):

```tsx
  { label: 'Departments', path: '/admin/departments', icon: '🏢' },
```

- [ ] **Step 6: Run test to verify it passes**

Run: `cd frontend && npx vitest run src/pages/admin/__tests__/DepartmentsPage.test.tsx`
Expected: PASS (2 tests).

- [ ] **Step 7: Commit**

```bash
cd frontend && git add src/pages/admin/DepartmentsPage.tsx src/App.tsx src/components/layout/AdminLayout.tsx src/pages/admin/__tests__/DepartmentsPage.test.tsx
git commit -m "feat(departments): admin departments list page + route + nav"
```

---

## Task 10: Frontend — Department detail page (members + content + compliance)

**Files:**
- Create: `frontend/src/pages/admin/DepartmentDetailPage.tsx`
- Test: `frontend/src/pages/admin/__tests__/DepartmentDetailPage.test.tsx`

- [ ] **Step 1: Write the failing test**

Create `frontend/src/pages/admin/__tests__/DepartmentDetailPage.test.tsx`:

```tsx
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { DepartmentDetailPage } from '../DepartmentDetailPage'
import { api } from '@/services/api'

vi.mock('@/services/api', () => ({
  api: { get: vi.fn(), post: vi.fn(), put: vi.fn(), delete: vi.fn() },
}))
vi.mock('@/context/ToastContext', () => ({ useToast: () => ({ showToast: vi.fn() }) }))

const mockedApi = api as unknown as Record<string, ReturnType<typeof vi.fn>>
const ok = (data: unknown) => Promise.resolve({ ok: true, json: async () => data } as Response)

const detail = {
  id: 1, name: 'Operations', description: 'Ops', is_active: true,
  members: [{ id: 5, username: 'alice', email: 'alice@x.com', role: 'trainee' }],
  content: [{ id: 7, course_id: 3, course_title: 'Fire Safety', is_podcast: false, mandatory: true, due_mode: 'fixed', due_date: '2026-06-30T00:00:00', due_days: null }],
}

function routeApi() {
  mockedApi.get.mockImplementation((path: string) => {
    if (path === '/departments/1') return ok(detail)
    if (path.startsWith('/departments/1/compliance')) return ok({ department_id: 1, items: [] })
    if (path === '/users?page=1&page_size=100') return ok({ items: [{ id: 5, username: 'alice' }, { id: 6, username: 'bob' }] })
    if (path.startsWith('/users')) return ok({ items: [{ id: 5, username: 'alice' }, { id: 6, username: 'bob' }] })
    if (path === '/courses') return ok([{ id: 3, title: 'Fire Safety' }, { id: 4, title: 'GDPR' }])
    return ok([])
  })
}

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/admin/departments/1']}>
      <Routes>
        <Route path="/admin/departments/:id" element={<DepartmentDetailPage />} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('DepartmentDetailPage', () => {
  beforeEach(() => { vi.clearAllMocks(); routeApi() })

  it('shows members and assigned content', async () => {
    renderPage()
    expect(await screen.findByText('alice')).toBeInTheDocument()
    expect(screen.getByText('Fire Safety')).toBeInTheDocument()
    // is_podcast=false -> labelled "Course"; the mandatory flag shows a badge too
    expect(screen.getByText('Course')).toBeInTheDocument()
    expect(screen.getByText('Mandatory')).toBeInTheDocument()
  })

  it('assigns content as mandatory with a fixed due date', async () => {
    mockedApi.post.mockReturnValue(ok({ id: 8, course_id: 4, course_title: 'GDPR', is_podcast: false, mandatory: true, due_mode: 'fixed', due_date: '2026-09-01T00:00:00', due_days: null }))
    renderPage()
    await screen.findByText('Fire Safety')

    await userEvent.selectOptions(await screen.findByLabelText(/course \/ podcast/i), '4')
    await userEvent.click(screen.getByLabelText(/mandatory/i))
    await userEvent.selectOptions(screen.getByLabelText(/deadline type/i), 'fixed')
    await userEvent.type(screen.getByLabelText(/due date/i), '2026-09-01')
    await userEvent.click(screen.getByText('Assign'))

    expect(mockedApi.post).toHaveBeenCalledWith(
      '/departments/1/content',
      expect.objectContaining({ course_id: 4, mandatory: true, due_mode: 'fixed', due_date: '2026-09-01' }),
    )
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/pages/admin/__tests__/DepartmentDetailPage.test.tsx`
Expected: FAIL — cannot resolve `../DepartmentDetailPage`.

- [ ] **Step 3: Create the page**

Create `frontend/src/pages/admin/DepartmentDetailPage.tsx`:

```tsx
import { useState, useEffect, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { api } from '@/services/api'
import { useToast } from '@/context/ToastContext'
import { Card } from '@/components/common/Card'
import { Button } from '@/components/common/Button'
import { Select } from '@/components/common/Select'
import { Input } from '@/components/common/Input'

interface Member { id: number; username: string; email: string; role: string }
interface Content {
  id: number; course_id: number; course_title: string; is_podcast: boolean
  mandatory: boolean; due_mode: string | null; due_date: string | null; due_days: number | null
}
interface Detail { id: number; name: string; description: string | null; is_active: boolean; members: Member[]; content: Content[] }
interface ComplianceItem {
  content_id: number; course_id: number; course_title: string; mandatory: boolean
  total_members: number; not_started: number; in_progress: number; completed: number; overdue: number
}
interface CourseOption { id: number; title: string }

export const DepartmentDetailPage = () => {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { showToast } = useToast()

  const [detail, setDetail] = useState<Detail | null>(null)
  const [allUsers, setAllUsers] = useState<{ id: number; username: string }[]>([])
  const [courses, setCourses] = useState<CourseOption[]>([])
  const [compliance, setCompliance] = useState<ComplianceItem[]>([])

  const [memberToAdd, setMemberToAdd] = useState('')
  const [courseToAssign, setCourseToAssign] = useState('')
  const [mandatory, setMandatory] = useState(false)
  const [dueMode, setDueMode] = useState('')
  const [dueDate, setDueDate] = useState('')
  const [dueDays, setDueDays] = useState('')

  const load = useCallback(async () => {
    const res = await api.get(`/departments/${id}`)
    if (res.ok) setDetail(await res.json())
    const cres = await api.get(`/departments/${id}/compliance`)
    if (cres.ok) setCompliance((await cres.json()).items || [])
  }, [id])

  useEffect(() => {
    load()
    api.get('/users?page=1&page_size=100').then(async r => {
      if (r.ok) { const d = await r.json(); setAllUsers(Array.isArray(d) ? d : d.items || []) }
    })
    api.get('/courses').then(async r => {
      if (r.ok) { const d = await r.json(); setCourses(Array.isArray(d) ? d : d.items || []) }
    })
  }, [id, load])

  const addMember = async () => {
    if (!memberToAdd) return
    const res = await api.post(`/departments/${id}/members`, { user_ids: [Number(memberToAdd)] })
    if (res.ok) { showToast('Member added', 'success'); setMemberToAdd(''); load() }
    else showToast('Failed to add member', 'error')
  }

  const removeMember = async (userId: number) => {
    const res = await api.delete(`/departments/${id}/members/${userId}`)
    if (res.ok) { showToast('Member removed', 'success'); load() }
    else showToast('Failed to remove member', 'error')
  }

  const assignContent = async () => {
    if (!courseToAssign) { showToast('Pick a course or podcast', 'error'); return }
    const payload: Record<string, unknown> = { course_id: Number(courseToAssign), mandatory }
    if (mandatory && dueMode) {
      payload.due_mode = dueMode
      if (dueMode === 'fixed') payload.due_date = dueDate
      if (dueMode === 'relative') payload.due_days = Number(dueDays)
    }
    const res = await api.post(`/departments/${id}/content`, payload)
    if (res.ok) {
      showToast('Content assigned', 'success')
      setCourseToAssign(''); setMandatory(false); setDueMode(''); setDueDate(''); setDueDays('')
      load()
    } else {
      const err = await res.json().catch(() => ({}))
      showToast(err.detail || 'Failed to assign content', 'error')
    }
  }

  const unassign = async (contentId: number) => {
    const res = await api.delete(`/departments/${id}/content/${contentId}`)
    if (res.ok) { showToast('Content unassigned', 'success'); load() }
    else showToast('Failed to unassign', 'error')
  }

  if (!detail) return <p className="text-gray-500">Loading…</p>

  const complianceFor = (contentId: number) => compliance.find(c => c.content_id === contentId)

  return (
    <div className="space-y-6">
      <div>
        <button onClick={() => navigate('/admin/departments')} className="text-sm text-blue-600 hover:underline">← All departments</button>
        <h1 className="text-2xl font-bold text-brand-dark mt-1">{detail.name}</h1>
        {detail.description && <p className="text-gray-600">{detail.description}</p>}
      </div>

      <Card className="p-4">
        <h2 className="font-semibold text-lg mb-3">Members</h2>
        <div className="flex gap-2 items-end mb-4">
          <div className="flex-1">
            <Select
              label="Add user"
              aria-label="Add user"
              value={memberToAdd}
              onChange={e => setMemberToAdd(e.target.value)}
              options={allUsers.map(u => ({ value: String(u.id), label: u.username }))}
            />
          </div>
          <div className="mb-4"><Button onClick={addMember}>Add</Button></div>
        </div>
        {detail.members.length === 0 ? (
          <p className="text-gray-500 text-sm">No members yet.</p>
        ) : (
          <ul className="divide-y">
            {detail.members.map(m => (
              <li key={m.id} className="flex justify-between items-center py-2">
                <span>{m.username} <span className="text-gray-400 text-sm">({m.email})</span></span>
                <button onClick={() => removeMember(m.id)} className="text-red-500 text-sm hover:underline">Remove</button>
              </li>
            ))}
          </ul>
        )}
      </Card>

      <Card className="p-4">
        <h2 className="font-semibold text-lg mb-3">Assigned content</h2>
        <div className="grid md:grid-cols-2 gap-2 items-end mb-4">
          <Select
            label="Course / Podcast"
            aria-label="Course / Podcast"
            value={courseToAssign}
            onChange={e => setCourseToAssign(e.target.value)}
            options={courses.map(c => ({ value: String(c.id), label: c.title }))}
          />
          <div className="flex flex-col gap-2">
            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" aria-label="Mandatory" checked={mandatory} onChange={e => setMandatory(e.target.checked)} />
              Mandatory
            </label>
            {mandatory && (
              <Select
                label="Deadline type"
                aria-label="Deadline type"
                value={dueMode}
                onChange={e => setDueMode(e.target.value)}
                options={[{ value: 'fixed', label: 'Fixed date' }, { value: 'relative', label: 'Relative (days)' }]}
              />
            )}
            {mandatory && dueMode === 'fixed' && (
              <Input label="Due date" aria-label="Due date" type="date" value={dueDate} onChange={e => setDueDate(e.target.value)} />
            )}
            {mandatory && dueMode === 'relative' && (
              <Input label="Days to complete" aria-label="Days to complete" type="number" value={dueDays} onChange={e => setDueDays(e.target.value)} />
            )}
          </div>
        </div>
        <Button onClick={assignContent}>Assign</Button>

        {detail.content.length === 0 ? (
          <p className="text-gray-500 text-sm mt-4">No content assigned yet.</p>
        ) : (
          <ul className="divide-y mt-4">
            {detail.content.map(c => {
              const stats = complianceFor(c.id)
              return (
                <li key={c.id} className="py-3">
                  <div className="flex justify-between items-start">
                    <div>
                      <span className="font-medium">{c.course_title}</span>
                      <span className="ml-2 text-xs rounded px-2 py-0.5 bg-gray-100 text-gray-600">{c.is_podcast ? 'Podcast' : 'Course'}</span>
                      {c.mandatory && <span className="ml-2 text-xs rounded px-2 py-0.5 bg-amber-100 text-amber-700">Mandatory</span>}
                      <div className="text-sm text-gray-500 mt-1">
                        {c.mandatory && c.due_mode === 'fixed' && c.due_date && <>Due {c.due_date.slice(0, 10)}</>}
                        {c.mandatory && c.due_mode === 'relative' && c.due_days != null && <>Due {c.due_days} days after joining</>}
                        {c.mandatory && !c.due_mode && <>No deadline</>}
                      </div>
                    </div>
                    <button onClick={() => unassign(c.id)} className="text-red-500 text-sm hover:underline">Unassign</button>
                  </div>
                  {stats && c.mandatory && (
                    <div className="flex gap-3 mt-2 text-xs text-gray-600">
                      <span className="text-green-600">{stats.completed} completed</span>
                      <span className="text-red-600">{stats.overdue} overdue</span>
                      <span>{stats.in_progress} in progress</span>
                      <span>{stats.not_started} not started</span>
                    </div>
                  )}
                </li>
              )
            })}
          </ul>
        )}
      </Card>
    </div>
  )
}
```

- [ ] **Step 4: Wire the detail route in App.tsx**

In `frontend/src/App.tsx`, add the import next to the `DepartmentsPage` import (~line 22):

```tsx
import { DepartmentDetailPage } from '@/pages/admin/DepartmentDetailPage'
```

And add the detail route directly after the `/admin/departments` route added in Task 9:

```tsx
      <Route
        path="/admin/departments/:id"
        element={
          <AdminLayout>
            <ProtectedRoute adminOnly>
              <DepartmentDetailPage />
            </ProtectedRoute>
          </AdminLayout>
        }
      />
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd frontend && npx vitest run src/pages/admin/__tests__/DepartmentDetailPage.test.tsx`
Expected: PASS (2 tests).

- [ ] **Step 6: Type-check the frontend**

Run: `cd frontend && npx tsc -b --noEmit`
Expected: no errors (confirms `App.tsx` imports resolve and the new pages type-check).

- [ ] **Step 7: Commit**

```bash
cd frontend && git add src/pages/admin/DepartmentDetailPage.tsx src/App.tsx src/pages/admin/__tests__/DepartmentDetailPage.test.tsx
git commit -m "feat(departments): department detail page (members, content, compliance) + route"
```

---

## Task 11: Full verification

**Files:** none (verification only)

- [ ] **Step 1: Run the full backend department + ilb suites**

Run: `cd backend && python -m pytest tests/test_departments_models.py tests/test_department_service.py tests/test_departments_router.py tests/test_ilb_router.py -v`
Expected: all PASS. (Slow on iCloud — allow several minutes.)

- [ ] **Step 2: Run the full frontend admin test set + type-check**

Run: `cd frontend && npx vitest run src/pages/admin && npx tsc -b --noEmit`
Expected: all PASS, no type errors.

- [ ] **Step 3: Manual smoke (optional, if a dev server is running)**

Log in as admin → `/admin/departments` → create a department → open it → add a user → assign a course as mandatory with a fixed date → confirm it appears with the "Mandatory" badge and a compliance row.

- [ ] **Step 4: Final commit (if any verification fixups were needed)**

```bash
git add -A && git commit -m "test(departments): full-suite verification fixups"
```

---

## Done

Departments, membership, content assignment with mandatory + fixed/relative deadlines, auto-enrolment, unified completion, a compliance summary, and the admin UI are all implemented and tested. Email reminders and a learner-facing "required training" page remain deferred per the spec.
