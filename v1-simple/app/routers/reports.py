"""Phase 10 — CSV / JSON reporting endpoints for admins."""

import csv
import io
from typing import Iterator
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import AsyncSessionLocal

router = APIRouter(prefix="/api", tags=["reports"])


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


def _csv_escape(value) -> str:
    """Escape a value for CSV output."""
    if value is None:
        return ""
    s = str(value)
    if any(c in s for c in (',', '"', '\n', '\r')):
        s = '"' + s.replace('"', '""') + '"'
    return s


def _stream_csv(headers: list[str], rows: Iterator[dict]):
    def generate():
        yield ",".join(headers) + "\r\n"
        for row in rows:
            yield ",".join(_csv_escape(row.get(h)) for h in headers) + "\r\n"
    return StreamingResponse(
        generate(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=report.csv"},
    )


def _enrollment_status(e) -> str:
    if getattr(e, "completed", False):
        return "completed"
    due = getattr(e, "due_date", None)
    if due:
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        if due < now:
            return "overdue"
    prog = getattr(e, "progress_pct", 0) or 0
    if prog > 0:
        return "in_progress"
    return "not_started"


def _fmt_dt(dt) -> str:
    return dt.isoformat() if dt else ""


@router.get("/reports/learner/{user_id}.csv")
async def learner_csv(user_id: str, db: AsyncSession = Depends(get_db)):
    try:
        from app.models import Enrollment, Course
        stmt = (
            select(Enrollment, Course)
            .join(Course, Enrollment.course_id == Course.id)
            .where(Enrollment.user_id == user_id)
            .order_by(Enrollment.enrolled_at.desc())
        )
        result = await db.execute(stmt)
        rows = result.all()
    except Exception:
        rows = []

    headers = ["course_title", "enrolled_at", "completed_at", "progress_pct", "score", "time_spent_s", "due_date", "status"]

    def gen():
        for e, c in rows:
            yield {
                "course_title": c.title,
                "enrolled_at": _fmt_dt(getattr(e, "enrolled_at", None)),
                "completed_at": _fmt_dt(getattr(e, "completed_at", None)),
                "progress_pct": getattr(e, "progress_pct", 0),
                "score": getattr(e, "score", ""),
                "time_spent_s": getattr(e, "time_spent_s", 0),
                "due_date": _fmt_dt(getattr(e, "due_date", None)),
                "status": _enrollment_status(e),
            }

    return _stream_csv(headers, gen())


@router.get("/reports/course/{course_id}.csv")
async def course_csv(course_id: str, db: AsyncSession = Depends(get_db)):
    try:
        from app.models import Enrollment, Course
        # Verify course exists
        c_result = await db.execute(select(Course).where(Course.id == course_id))
        course = c_result.scalar_one_or_none()
        if not course:
            raise HTTPException(404, "Course not found")

        stmt = (
            select(Enrollment)
            .where(Enrollment.course_id == course_id)
            .order_by(Enrollment.enrolled_at.desc())
        )
        result = await db.execute(stmt)
        enrollments = result.scalars().all()
    except HTTPException:
        raise
    except Exception:
        enrollments = []

    headers = ["learner_email", "learner_name", "enrolled_at", "completed_at", "progress_pct", "score", "time_spent_s", "status"]

    def gen():
        for e in enrollments:
            uid = getattr(e, "user_id", "")
            yield {
                "learner_email": uid,
                "learner_name": uid,
                "enrolled_at": _fmt_dt(getattr(e, "enrolled_at", None)),
                "completed_at": _fmt_dt(getattr(e, "completed_at", None)),
                "progress_pct": getattr(e, "progress_pct", 0),
                "score": getattr(e, "score", ""),
                "time_spent_s": getattr(e, "time_spent_s", 0),
                "status": _enrollment_status(e),
            }

    return _stream_csv(headers, gen())


@router.get("/reports/learner/{user_id}")
async def learner_json(user_id: str, db: AsyncSession = Depends(get_db)):
    try:
        from app.models import Enrollment, Course
        stmt = (
            select(Enrollment, Course)
            .join(Course, Enrollment.course_id == Course.id)
            .where(Enrollment.user_id == user_id)
            .order_by(Enrollment.enrolled_at.desc())
        )
        result = await db.execute(stmt)
        rows = result.all()
        return [
            {
                "course_id": c.id,
                "course_title": c.title,
                "enrolled_at": _fmt_dt(getattr(e, "enrolled_at", None)),
                "completed_at": _fmt_dt(getattr(e, "completed_at", None)),
                "progress_pct": getattr(e, "progress_pct", 0),
                "score": getattr(e, "score", None),
                "time_spent_s": getattr(e, "time_spent_s", 0),
                "due_date": _fmt_dt(getattr(e, "due_date", None)),
                "status": _enrollment_status(e),
            }
            for e, c in rows
        ]
    except Exception:
        return []


@router.get("/reports/course/{course_id}")
async def course_json(course_id: str, db: AsyncSession = Depends(get_db)):
    try:
        from app.models import Enrollment, Course
        c_result = await db.execute(select(Course).where(Course.id == course_id))
        course = c_result.scalar_one_or_none()
        if not course:
            raise HTTPException(404, "Course not found")
        stmt = (
            select(Enrollment)
            .where(Enrollment.course_id == course_id)
            .order_by(Enrollment.enrolled_at.desc())
        )
        result = await db.execute(stmt)
        enrollments = result.scalars().all()
        return {
            "course_id": course_id,
            "course_title": course.title,
            "learners": [
                {
                    "user_id": e.user_id,
                    "enrolled_at": _fmt_dt(getattr(e, "enrolled_at", None)),
                    "completed_at": _fmt_dt(getattr(e, "completed_at", None)),
                    "progress_pct": getattr(e, "progress_pct", 0),
                    "score": getattr(e, "score", None),
                    "time_spent_s": getattr(e, "time_spent_s", 0),
                    "status": _enrollment_status(e),
                }
                for e in enrollments
            ],
        }
    except HTTPException:
        raise
    except Exception:
        return {"course_id": course_id, "learners": []}
