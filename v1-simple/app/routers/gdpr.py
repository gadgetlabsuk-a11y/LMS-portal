import asyncio
import json
import logging
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import AsyncSessionLocal
from app.models import (
    DataDeletionRequest, Enrollment, Notification,
    Course, TraineeProgress,
)
from app.services.storage import get_storage

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["gdpr"])

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

def get_user(x_user_id: str = Header(default="system")) -> str:
    return x_user_id


@router.post("/users/me/data-export")
async def request_data_export(
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_user),
):
    """Collect all user data and store as JSON. Returns a download URL."""
    # Collect data synchronously for now (async job in prod)
    data: dict = {"user_id": user_id, "exported_at": datetime.now(timezone.utc).isoformat()}

    # Enrollments
    enroll_result = await db.execute(select(Enrollment).where(Enrollment.user_id == user_id))
    enrollments = enroll_result.scalars().all()
    data["enrollments"] = [
        {
            "id": e.id, "course_id": e.course_id,
            "enrolled_at": e.enrolled_at.isoformat() if e.enrolled_at else None,
            "completed": e.completed, "progress_pct": e.progress_pct,
            "score": e.score, "due_date": e.due_date.isoformat() if e.due_date else None,
        }
        for e in enrollments
    ]

    # Notifications
    notif_result = await db.execute(select(Notification).where(Notification.user_id == user_id))
    notifications = notif_result.scalars().all()
    data["notifications"] = [
        {"id": n.id, "kind": n.kind, "course_id": n.course_id, "created_at": n.created_at.isoformat() if n.created_at else None}
        for n in notifications
    ]

    # TraineeProgress (legacy)
    prog_result = await db.execute(select(TraineeProgress).where(TraineeProgress.trainee_id == user_id))
    progress = prog_result.scalars().all()
    data["progress"] = [
        {"lesson_id": p.lesson_id, "completed": p.completed, "quiz_score": p.quiz_score}
        for p in progress
    ]

    # Store export
    storage = get_storage()
    export_key = f"gdpr/exports/{user_id}/{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}.json"
    storage.put(export_key, json.dumps(data, indent=2).encode(), "application/json")
    download_url = storage.signed_url(export_key, expires_s=604800)  # 7 days

    logger.info("Data export created for user %s -> %s", user_id, export_key)
    return {"status": "ready", "download_url": download_url, "expires_in_days": 7}


@router.post("/users/me/delete")
async def request_deletion(
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_user),
):
    """Create a data deletion request (GDPR right to erasure)."""
    # Check for existing pending request
    existing = await db.execute(
        select(DataDeletionRequest).where(
            DataDeletionRequest.user_id == user_id,
            DataDeletionRequest.status == "pending",
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(409, "A deletion request is already pending")

    req = DataDeletionRequest(user_id=user_id)
    db.add(req)
    await db.commit()
    await db.refresh(req)
    return {
        "id": req.id,
        "status": req.status,
        "requested_at": req.requested_at.isoformat() if req.requested_at else None,
        "message": "Your deletion request has been received. It will be processed within 30 days.",
    }


@router.get("/admin/data-deletion-requests")
async def list_deletion_requests(db: AsyncSession = Depends(get_db)):
    """Admin: list all pending deletion requests."""
    result = await db.execute(
        select(DataDeletionRequest)
        .where(DataDeletionRequest.status == "pending")
        .order_by(DataDeletionRequest.requested_at.asc())
    )
    reqs = result.scalars().all()
    return [
        {
            "id": r.id, "user_id": r.user_id, "status": r.status,
            "requested_at": r.requested_at.isoformat() if r.requested_at else None,
        }
        for r in reqs
    ]


@router.post("/admin/data-deletion-requests/{request_id}/process")
async def process_deletion(
    request_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Admin: hard-delete user data."""
    result = await db.execute(select(DataDeletionRequest).where(DataDeletionRequest.id == request_id))
    req = result.scalar_one_or_none()
    if not req:
        raise HTTPException(404, "Deletion request not found")
    if req.status != "pending":
        raise HTTPException(409, f"Request is already {req.status}")

    user_id = req.user_id
    req.status = "processing"
    await db.commit()

    try:
        # Delete enrollments
        await db.execute(delete(Enrollment).where(Enrollment.user_id == user_id))
        # Delete notifications
        await db.execute(delete(Notification).where(Notification.user_id == user_id))
        # Delete progress
        await db.execute(delete(TraineeProgress).where(TraineeProgress.trainee_id == user_id))
        # Anonymise deletion request itself
        req.status = "completed"
        req.completed_at = datetime.now(timezone.utc).replace(tzinfo=None)
        await db.commit()
        logger.info("Data deletion completed for user_id=%s", user_id)
    except Exception as e:
        req.status = "pending"
        await db.commit()
        logger.error("Deletion failed for user %s: %s", user_id, e)
        raise HTTPException(500, "Deletion failed — will retry")

    return {"status": "completed", "user_id": user_id}
