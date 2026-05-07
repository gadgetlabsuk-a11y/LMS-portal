from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone
from app.database import AsyncSessionLocal
from app.models import Notification

router = APIRouter(prefix="/api", tags=["notifications"])

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

def get_user(x_user_id: str = Header(default="system")) -> str:
    return x_user_id


@router.get("/notifications")
async def list_notifications(db: AsyncSession = Depends(get_db), user_id: str = Depends(get_user)):
    result = await db.execute(
        select(Notification)
        .where(Notification.user_id == user_id)
        .order_by(Notification.created_at.desc())
        .limit(50)
    )
    notifs = result.scalars().all()
    return [
        {
            "id": n.id,
            "kind": n.kind,
            "course_id": n.course_id,
            "payload": n.payload,
            "read": n.read_at is not None,
            "sent_email_at": n.sent_email_at.isoformat() if n.sent_email_at else None,
            "created_at": n.created_at.isoformat() if n.created_at else None,
        }
        for n in notifs
    ]


@router.patch("/notifications/{notification_id}/read")
async def mark_read(notification_id: int, db: AsyncSession = Depends(get_db), user_id: str = Depends(get_user)):
    result = await db.execute(
        select(Notification).where(Notification.id == notification_id, Notification.user_id == user_id)
    )
    notif = result.scalar_one_or_none()
    if not notif:
        raise HTTPException(404, "Notification not found")
    notif.read_at = datetime.now(timezone.utc).replace(tzinfo=None)
    await db.commit()
    return {"status": "read"}
