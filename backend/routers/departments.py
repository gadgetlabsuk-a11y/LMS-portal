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
from models import User, Department, DepartmentMember, DepartmentContent
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
