"""Department management routes (admin-only).

Departments group users; courses/standalone broadcasts are assigned to a department and
optionally made mandatory with a deadline. Adding a member auto-enrols them in the
department's COURSE assignments (broadcasts have no enrolment). Removing a member or
deleting a department leaves enrolments/sessions intact. See
docs/superpowers/specs/2026-05-23-departments-design.md.
"""
import logging
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models import User, Course, Broadcast, Enrollment, Department, DepartmentMember, DepartmentContent
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
    content_type: str  # 'course' | 'broadcast'
    course_id: Optional[int]
    broadcast_id: Optional[int]
    title: str
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
    course_id: Optional[int] = None
    broadcast_id: Optional[int] = None
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
    content_type: str
    course_id: Optional[int]
    broadcast_id: Optional[int]
    title: str
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


def _member_response(m: DepartmentMember) -> MemberResponse:
    return MemberResponse(id=m.user.id, username=m.user.username, email=m.user.email, role=m.user.role.value)


def _content_response(c: DepartmentContent) -> ContentResponse:
    if c.broadcast_id is not None:
        return ContentResponse(
            id=c.id, content_type="broadcast", course_id=None, broadcast_id=c.broadcast_id,
            title=(c.broadcast.title if c.broadcast else ""), is_podcast=True,
            mandatory=c.mandatory, due_mode=c.due_mode, due_date=c.due_date, due_days=c.due_days,
        )
    return ContentResponse(
        id=c.id, content_type="course", course_id=c.course_id, broadcast_id=None,
        title=(c.course.title if c.course else ""),
        is_podcast=bool(c.course.ilb_published) if c.course else False,
        mandatory=c.mandatory, due_mode=c.due_mode, due_date=c.due_date, due_days=c.due_days,
    )


def _summary(d: Department) -> DepartmentSummary:
    return DepartmentSummary(
        id=d.id, name=d.name, description=d.description, is_active=d.is_active,
        member_count=len(d.members), content_count=len(d.content),
    )


def _validate_due_config(mandatory, due_mode, due_date, due_days) -> None:
    if not mandatory or due_mode is None:
        return
    if due_mode not in ("fixed", "relative"):
        raise HTTPException(status_code=400, detail="due_mode must be 'fixed' or 'relative'")
    if due_mode == "fixed" and due_date is None:
        raise HTTPException(status_code=400, detail="due_date is required when due_mode is 'fixed'")
    if due_mode == "relative" and (due_days is None or due_days <= 0):
        raise HTTPException(status_code=400, detail="due_days must be a positive integer when due_mode is 'relative'")


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
    db.add(d); db.commit(); db.refresh(d)
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
    db.commit(); db.refresh(d)
    return _summary(d)


@router.delete("/{department_id}")
def delete_department(department_id: int, db: Session = Depends(get_db),
                      current_user: User = Depends(require_admin)):
    d = _get_department(db, department_id)
    db.delete(d)  # cascades members + content; enrolments/sessions untouched
    db.commit()
    logger.info("Department deleted: %s by admin %s", department_id, current_user.id)
    return {"message": "Department deleted"}


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
    m = db.query(DepartmentMember).filter(
        DepartmentMember.department_id == department_id, DepartmentMember.user_id == user_id
    ).first()
    if not m:
        raise HTTPException(status_code=404, detail="Member not found in this department")
    db.delete(m)  # enrolments intentionally left intact
    db.commit()
    return {"message": "Member removed"}


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
    if bool(body.course_id) == bool(body.broadcast_id):
        raise HTTPException(status_code=400, detail="Provide exactly one of course_id or broadcast_id")

    if body.course_id is not None:
        if not db.query(Course).filter(Course.id == body.course_id).first():
            raise HTTPException(status_code=404, detail="Course not found")
        if (
            db.query(DepartmentContent)
            .filter(DepartmentContent.department_id == department_id,
                    DepartmentContent.course_id == body.course_id)
            .first()
        ):
            raise HTTPException(status_code=409, detail="This content is already assigned to the department")
    else:
        if not db.query(Broadcast).filter(Broadcast.id == body.broadcast_id).first():
            raise HTTPException(status_code=404, detail="Broadcast not found")
        if (
            db.query(DepartmentContent)
            .filter(DepartmentContent.department_id == department_id,
                    DepartmentContent.broadcast_id == body.broadcast_id)
            .first()
        ):
            raise HTTPException(status_code=409, detail="This content is already assigned to the department")

    _validate_due_config(body.mandatory, body.due_mode, body.due_date, body.due_days)

    c = DepartmentContent(
        department_id=department_id,
        course_id=body.course_id,
        broadcast_id=body.broadcast_id,
        mandatory=body.mandatory,
        due_mode=body.due_mode if body.mandatory else None,
        due_date=body.due_date if body.mandatory and body.due_mode == "fixed" else None,
        due_days=body.due_days if body.mandatory and body.due_mode == "relative" else None,
        assigned_by=current_user.id,
    )
    db.add(c)
    db.commit()
    db.refresh(c)

    if c.course_id is not None:
        dept_svc.sync_assignment_enrollments(db, department_id, c.course_id)
        db.refresh(c)
    return _content_response(c)


@router.put("/{department_id}/content/{content_id}", response_model=ContentResponse)
def update_content(department_id: int, content_id: int, body: ContentUpdateRequest,
                   db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    _get_department(db, department_id)
    c = (
        db.query(DepartmentContent)
        .filter(DepartmentContent.id == content_id, DepartmentContent.department_id == department_id)
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
        .filter(DepartmentContent.id == content_id, DepartmentContent.department_id == department_id)
        .first()
    )
    if not c:
        raise HTTPException(status_code=404, detail="Assignment not found")
    db.delete(c)  # enrolments / sessions intentionally left intact
    db.commit()
    return {"message": "Content unassigned"}


# --------------------------------------------------------------------------- compliance

@router.get("/{department_id}/compliance", response_model=ComplianceResponse)
def department_compliance(department_id: int, db: Session = Depends(get_db),
                          current_user: User = Depends(require_admin)):
    d = _get_department(db, department_id)
    members = [(m.user_id, m.added_at) for m in d.members]
    now = datetime.utcnow()
    items: List[ComplianceItem] = []
    for c in d.content:
        counts = {"not_started": 0, "in_progress": 0, "completed": 0, "overdue": 0}
        for uid, added_at in members:
            due = dept_svc.effective_due_date(c, added_at)
            completed = dept_svc.content_completed(db, uid, c)
            started = dept_svc.content_started(db, uid, c)
            counts[dept_svc.status_for(completed, started, due, now)] += 1
        resp = _content_response(c)
        items.append(ComplianceItem(
            content_id=c.id, content_type=resp.content_type,
            course_id=c.course_id, broadcast_id=c.broadcast_id, title=resp.title,
            mandatory=c.mandatory, total_members=len(members), **counts,
        ))
    return ComplianceResponse(department_id=department_id, items=items)
