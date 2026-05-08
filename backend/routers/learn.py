"""
Learner-facing course endpoints.
Read-only. Returns only PUBLISHED courses. Available to any authenticated user.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List, Optional, Dict, Any
import logging

from database import get_db
from models import User, Course, CourseStatus
from middleware.auth_middleware import get_current_active_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/learn", tags=["learn"])


class LearnCourseResponse(BaseModel):
    id: int
    title: str
    description: Optional[str]
    has_content: bool
    created_at: datetime

    class Config:
        from_attributes = True


class LearnCourseDetailResponse(LearnCourseResponse):
    content: Optional[Dict[str, Any]]


class LearnCourseListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: List[LearnCourseResponse]


@router.get("/courses", response_model=LearnCourseListResponse)
def list_learn_courses(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    q: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> dict:
    """List published courses for learners."""
    query = db.query(Course).filter(Course.status == CourseStatus.PUBLISHED)

    if q:
        query = query.filter(
            (Course.title.ilike(f"%{q}%")) | (Course.description.ilike(f"%{q}%"))
        )

    total = query.count()
    courses = (
        query.order_by(Course.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    items = [
        LearnCourseResponse(
            id=c.id,
            title=c.title,
            description=c.description,
            has_content=bool(c.content),
            created_at=c.created_at,
        )
        for c in courses
    ]

    logger.info(f"Learner catalogue: user={current_user.id}, total={total}")
    return {"total": total, "page": page, "page_size": page_size, "items": items}


@router.get("/courses/{course_id}", response_model=LearnCourseDetailResponse)
def get_learn_course(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> LearnCourseDetailResponse:
    """Get a single published course for learners."""
    course = db.query(Course).filter(
        Course.id == course_id,
        Course.status == CourseStatus.PUBLISHED,
    ).first()

    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    logger.info(f"Learner course detail: user={current_user.id}, course={course_id}")
    return LearnCourseDetailResponse(
        id=course.id,
        title=course.title,
        description=course.description,
        has_content=bool(course.content),
        content=course.content,
        created_at=course.created_at,
    )
