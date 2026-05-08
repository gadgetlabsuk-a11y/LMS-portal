"""
Creator-facing endpoints for stats and learner management.
Available to creator and admin roles only.
"""

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List, Optional
import logging

from database import get_db
from models import User, Course, CourseStatus, Enrollment
from middleware.auth_middleware import require_creator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/creator", tags=["creator"])


class CreatorStatsResponse(BaseModel):
    total_courses: int
    published_courses: int
    draft_courses: int
    total_enrollments: int


class LearnerEnrollmentResponse(BaseModel):
    learner_name: str
    email: str
    course_id: int
    course_title: str
    enrolled_at: datetime

    class Config:
        from_attributes = True


@router.get("/stats", response_model=CreatorStatsResponse)
def get_creator_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_creator),
) -> CreatorStatsResponse:
    """Return course and enrollment stats for the current creator."""
    courses = db.query(Course).filter(Course.creator_id == current_user.id).all()

    total = len(courses)
    published = sum(1 for c in courses if c.status == CourseStatus.PUBLISHED)
    draft = sum(1 for c in courses if c.status == CourseStatus.DRAFT)

    course_ids = [c.id for c in courses]
    enrollments = (
        db.query(Enrollment).filter(Enrollment.course_id.in_(course_ids)).count()
        if course_ids
        else 0
    )

    logger.info(f"Creator stats: user={current_user.id}, courses={total}, enrollments={enrollments}")
    return CreatorStatsResponse(
        total_courses=total,
        published_courses=published,
        draft_courses=draft,
        total_enrollments=enrollments,
    )


@router.get("/learners", response_model=List[LearnerEnrollmentResponse])
def get_creator_learners(
    course_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_creator),
) -> List[LearnerEnrollmentResponse]:
    """Return all learners enrolled in the current creator's courses."""
    course_query = db.query(Course).filter(Course.creator_id == current_user.id)
    if course_id is not None:
        course_query = course_query.filter(Course.id == course_id)
    courses = course_query.all()
    course_map = {c.id: c.title for c in courses}

    if not course_map:
        return []

    enrollments = (
        db.query(Enrollment)
        .filter(Enrollment.course_id.in_(course_map.keys()))
        .all()
    )

    result = []
    for e in enrollments:
        user = db.query(User).filter(User.id == e.user_id).first()
        if user:
            result.append(
                LearnerEnrollmentResponse(
                    learner_name=user.username,
                    email=user.email,
                    course_id=e.course_id,
                    course_title=course_map[e.course_id],
                    enrolled_at=e.enrolled_at,
                )
            )

    logger.info(f"Creator learners: user={current_user.id}, count={len(result)}")
    return result
