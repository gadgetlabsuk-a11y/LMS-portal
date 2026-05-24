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
from models import User, Course, CourseStatus, Enrollment
from models.models import CourseVersion
from middleware.auth_middleware import get_current_active_user
from services import department_service as dept_svc

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
            has_content=False,
            created_at=c.created_at,
        )
        for c in courses
    ]

    logger.info(f"Learner catalogue: user={current_user.id}, total={total}")
    return {"total": total, "page": page, "page_size": page_size, "items": items}


class RequiredTrainingItem(BaseModel):
    content_type: str
    course_id: Optional[int]
    broadcast_id: Optional[int]
    title: str
    is_podcast: bool
    due_date: Optional[datetime]
    status: str


@router.get("/required-training", response_model=List[RequiredTrainingItem])
def my_required_training(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """The current learner's mandatory training (courses + standalone broadcasts) across
    their departments, with effective due dates and status."""
    return dept_svc.required_training_for_user(db, current_user.id)


@router.get("/courses/{course_id}", response_model=LearnCourseDetailResponse)
def get_learn_course(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> LearnCourseDetailResponse:
    """Get a single published course for learners.

    If learner has a course_version pin from enrollment, serve the snapshot
    from CourseVersion table (PUBLISH-07). Falls back to live course if no
    version row found (Pitfall 6).
    """
    course = db.query(Course).filter(
        Course.id == course_id,
        Course.status == CourseStatus.PUBLISHED,
    ).first()

    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    # Version pinning: check if the learner has a specific version enrolled
    enrollment = db.query(Enrollment).filter(
        Enrollment.user_id == current_user.id,
        Enrollment.course_id == course_id,
    ).first()

    if enrollment and enrollment.course_version is not None:
        version_row = db.query(CourseVersion).filter(
            CourseVersion.course_id == course_id,
            CourseVersion.version_number == enrollment.course_version,
        ).first()
        if version_row:
            snapshot = version_row.snapshot
            logger.info(
                f"Learner course detail (versioned): user={current_user.id}, "
                f"course={course_id}, version={enrollment.course_version}"
            )
            return LearnCourseDetailResponse(
                id=course.id,
                title=snapshot.get("title", course.title),
                description=snapshot.get("description", course.description),
                has_content=True,
                content=snapshot,
                created_at=course.created_at,
            )
        # Pitfall 6: no row found — fall through to live course

    logger.info(f"Learner course detail: user={current_user.id}, course={course_id}")
    return LearnCourseDetailResponse(
        id=course.id,
        title=course.title,
        description=course.description,
        has_content=False,
        content=None,
        created_at=course.created_at,
    )
