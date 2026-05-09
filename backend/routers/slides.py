"""
Slide CRUD + reorder router.
Available to creator and admin roles only.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List, Optional
import logging

from database import get_db
from models import Course, Module, Video, Slide
from middleware.auth_middleware import require_creator

logger = logging.getLogger(__name__)

router = APIRouter(tags=["slides"])


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

class SlideCreate(BaseModel):
    layout_id: Optional[str] = None
    narration_script: Optional[str] = None
    transition: Optional[str] = "none"
    status: Optional[str] = "draft"
    duration_seconds: Optional[int] = None


class SlideUpdate(BaseModel):
    layout_id: Optional[str] = None
    narration_script: Optional[str] = None
    transition: Optional[str] = None
    status: Optional[str] = None
    duration_seconds: Optional[int] = None


class SlideResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    video_id: int
    order_index: int
    layout_id: Optional[str]
    narration_script: Optional[str]
    narration_audio_url: Optional[str]
    transition: Optional[str]
    status: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]


class SlideReorderRequest(BaseModel):
    slide_ids: List[int]


# ---------------------------------------------------------------------------
# Ownership helper
# ---------------------------------------------------------------------------

def _get_video_or_404(video_id: int, db: Session, current_user) -> Video:
    """Fetch video by id (with module/course join), raise 404 if missing, 403 if not owner."""
    video = db.query(Video).join(Module).join(Course).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video not found")
    if current_user.role.value != "admin" and video.module.course.creator_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return video


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post(
    "/api/videos/{video_id}/slides",
    response_model=SlideResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_slide(
    video_id: int,
    body: SlideCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_creator),
) -> Slide:
    """Create a new slide in the given video."""
    video = _get_video_or_404(video_id, db, current_user)

    # Assign next order_index
    max_index = (
        db.query(Slide)
        .filter(Slide.video_id == video_id)
        .count()
    )

    slide = Slide(
        video_id=video.id,
        order_index=max_index,
        layout_id=body.layout_id,
        narration_script=body.narration_script,
        transition=body.transition or "none",
        status=body.status or "draft",
        duration_seconds=body.duration_seconds,
    )
    db.add(slide)
    db.commit()
    db.refresh(slide)

    logger.info(f"Slide created: {slide.id} in video {video_id} by user {current_user.id}")
    return slide


@router.get(
    "/api/videos/{video_id}/slides",
    response_model=List[SlideResponse],
)
def list_slides(
    video_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_creator),
) -> List[Slide]:
    """List all slides for a video, ordered by order_index."""
    video = _get_video_or_404(video_id, db, current_user)
    slides = (
        db.query(Slide)
        .filter(Slide.video_id == video.id)
        .order_by(Slide.order_index)
        .all()
    )
    return slides


@router.get(
    "/api/slides/{slide_id}",
    response_model=SlideResponse,
)
def get_slide(
    slide_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_creator),
) -> Slide:
    """Get a single slide by id."""
    slide = (
        db.query(Slide)
        .join(Video)
        .join(Module)
        .join(Course)
        .filter(Slide.id == slide_id)
        .first()
    )
    if not slide:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Slide not found")
    if current_user.role.value != "admin" and slide.video.module.course.creator_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return slide


@router.put(
    "/api/slides/{slide_id}",
    response_model=SlideResponse,
)
def update_slide(
    slide_id: int,
    body: SlideUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_creator),
) -> Slide:
    """Partial update of a slide."""
    slide = (
        db.query(Slide)
        .join(Video)
        .join(Module)
        .join(Course)
        .filter(Slide.id == slide_id)
        .first()
    )
    if not slide:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Slide not found")
    if current_user.role.value != "admin" and slide.video.module.course.creator_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(slide, field, value)

    slide.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(slide)

    logger.info(f"Slide updated: {slide.id} by user {current_user.id}")
    return slide


@router.delete("/api/slides/{slide_id}")
def delete_slide(
    slide_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_creator),
) -> dict:
    """Delete a slide (cascade deletes blocks)."""
    slide = (
        db.query(Slide)
        .join(Video)
        .join(Module)
        .join(Course)
        .filter(Slide.id == slide_id)
        .first()
    )
    if not slide:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Slide not found")
    if current_user.role.value != "admin" and slide.video.module.course.creator_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    db.delete(slide)
    db.commit()

    logger.info(f"Slide deleted: {slide_id} by user {current_user.id}")
    return {"message": "Slide deleted"}


@router.post("/api/videos/{video_id}/slides/reorder")
def reorder_slides(
    video_id: int,
    body: SlideReorderRequest,
    db: Session = Depends(get_db),
    current_user=Depends(require_creator),
) -> dict:
    """Atomically reassign order_index for all siblings in a single transaction."""
    video = _get_video_or_404(video_id, db, current_user)

    # Validate all ids belong to this video in one query
    slides = (
        db.query(Slide)
        .filter(
            Slide.id.in_(body.slide_ids),
            Slide.video_id == video_id,
        )
        .all()
    )
    if len(slides) != len(body.slide_ids):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Some slide IDs do not belong to this video",
        )

    id_to_slide = {s.id: s for s in slides}
    for idx, sid in enumerate(body.slide_ids):
        id_to_slide[sid].order_index = idx

    db.commit()  # single transaction — no order_index drift

    logger.info(f"Slides reordered in video {video_id} by user {current_user.id}")
    return {"message": "Reordered"}
