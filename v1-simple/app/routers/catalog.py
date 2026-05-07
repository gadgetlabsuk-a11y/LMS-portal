from datetime import datetime
from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from app.database import AsyncSessionLocal
from app.models import Course, Enrollment
import uuid

router = APIRouter(prefix="/api", tags=["catalog"])

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

def get_user(x_user_id: str = Header(default="system")) -> str:
    return x_user_id


@router.get("/catalog")
async def list_catalog(
    q: str = Query(default=""),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Public catalog — published, catalog-visible courses."""
    stmt = select(Course).where(
        Course.catalog_visible == True,
        Course.published == True,
    )
    if q:
        stmt = stmt.where(Course.title.ilike(f"%{q}%"))
    stmt = stmt.order_by(Course.created_at.desc())
    stmt = stmt.offset((page - 1) * limit).limit(limit)
    result = await db.execute(stmt)
    courses = result.scalars().all()

    out = []
    for c in courses:
        # Count enrolments
        count_result = await db.execute(
            select(func.count()).where(Enrollment.course_id == c.id)
        )
        enrolment_count = count_result.scalar() or 0
        out.append({
            "id": c.id,
            "title": c.title,
            "description": c.description,
            "price_pence": getattr(c, "price_pence", 0),
            "estimated_minutes": getattr(c, "estimated_minutes", None),
            "self_enrol_enabled": getattr(c, "self_enrol_enabled", False),
            "enrolment_count": enrolment_count,
            "created_at": c.created_at.isoformat() if hasattr(c, "created_at") and c.created_at else None,
        })
    return out


@router.post("/catalog/{course_id}/enrol")
async def self_enrol(
    course_id: str,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_user),
):
    """Self-enrol a trainee into a free published course."""
    result = await db.execute(select(Course).where(Course.id == course_id))
    course = result.scalar_one_or_none()
    if not course:
        raise HTTPException(404, "Course not found")
    if not getattr(course, "catalog_visible", False) or not course.published:
        raise HTTPException(403, "Course is not available for enrolment")
    if not getattr(course, "self_enrol_enabled", False):
        raise HTTPException(403, "Self-enrolment is not enabled for this course")

    price = getattr(course, "price_pence", 0)
    if price and price > 0:
        raise HTTPException(402, "Payment required — use /api/billing/checkout")

    # Check already enrolled
    existing = await db.execute(
        select(Enrollment).where(
            Enrollment.user_id == user_id,
            Enrollment.course_id == course_id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(409, "Already enrolled")

    enrollment = Enrollment(
        id=str(uuid.uuid4()),
        user_id=user_id,
        course_id=course_id,
    )
    db.add(enrollment)
    await db.commit()
    await db.refresh(enrollment)
    return {
        "id": enrollment.id,
        "user_id": enrollment.user_id,
        "course_id": enrollment.course_id,
        "enrolled_at": enrollment.enrolled_at.isoformat() if enrollment.enrolled_at else None,
    }


class AdminEnrolBody(BaseModel):
    user_ids: list[str]
    due_date: Optional[datetime] = None


@router.post("/courses/{course_id}/enrol")
async def admin_enrol(
    course_id: str,
    body: AdminEnrolBody,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_user),
):
    """Admin-enrol multiple users into a course with optional due date."""
    result = await db.execute(select(Course).where(Course.id == course_id))
    course = result.scalar_one_or_none()
    if not course:
        raise HTTPException(404, "Course not found")

    enrolled = []
    skipped = []
    for uid in body.user_ids:
        existing = await db.execute(
            select(Enrollment).where(
                Enrollment.user_id == uid,
                Enrollment.course_id == course_id,
            )
        )
        if existing.scalar_one_or_none():
            skipped.append(uid)
            continue
        enrollment = Enrollment(
            id=str(uuid.uuid4()),
            user_id=uid,
            course_id=course_id,
            due_date=body.due_date,
            assigned_by=user_id,
        )
        db.add(enrollment)
        enrolled.append(uid)

    await db.commit()
    return {"enrolled": enrolled, "skipped": skipped, "course_id": course_id}


@router.delete("/enrollments/{enrollment_id}")
async def unenrol(
    enrollment_id: str,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_user),
):
    result = await db.execute(select(Enrollment).where(Enrollment.id == enrollment_id))
    enrollment = result.scalar_one_or_none()
    if not enrollment:
        raise HTTPException(404, "Enrollment not found")
    await db.delete(enrollment)
    await db.commit()
    return {"status": "unenrolled"}
