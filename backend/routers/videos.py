"""
Video CRUD + reorder router.
Available to creator and admin roles only.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List, Optional
import logging

from database import get_db
from models import Course, Module, Video, CourseStatus
from middleware.auth_middleware import require_creator

logger = logging.getLogger(__name__)

router = APIRouter(tags=["videos"])


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

class VideoCreate(BaseModel):
    title: str
    description: Optional[str] = None
    video_type: Optional[str] = "slideshow_narrated"
    estimated_duration_seconds: Optional[int] = None
    source_video_url: Optional[str] = None
    status: Optional[str] = "draft"


class VideoUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    video_type: Optional[str] = None
    estimated_duration_seconds: Optional[int] = None
    narration_voice_id: Optional[str] = None
    source_video_url: Optional[str] = None
    status: Optional[str] = None


class VideoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    module_id: int
    order_index: int
    title: str
    description: Optional[str]
    video_type: Optional[str]
    estimated_duration_seconds: Optional[int]
    source_video_url: Optional[str]
    status: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]


class VideoReorderRequest(BaseModel):
    video_ids: List[int]


# ---------------------------------------------------------------------------
# Ownership helper
# ---------------------------------------------------------------------------

def _get_module_or_404(module_id: int, db: Session, current_user) -> Module:
    """Fetch module by id (with course join), raise 404 if missing, 403 if not owner."""
    module = db.query(Module).join(Course).filter(Module.id == module_id).first()
    if not module:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Module not found")
    if current_user.role.value != "admin" and module.course.creator_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return module


def _mark_course_changed(course_id: int, db: Session) -> None:
    """Set HAS_UNPUBLISHED_CHANGES on a PUBLISHED course.

    Only transitions when status == PUBLISHED. Caller is responsible for db.commit().
    """
    course = db.query(Course).filter(Course.id == course_id).first()
    if course and course.status == CourseStatus.PUBLISHED:
        course.status = CourseStatus.HAS_UNPUBLISHED_CHANGES
        db.add(course)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post(
    "/api/modules/{module_id}/videos",
    response_model=VideoResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_video(
    module_id: int,
    body: VideoCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_creator),
) -> Video:
    """Create a new video in the given module."""
    module = _get_module_or_404(module_id, db, current_user)

    # Assign next order_index
    max_index = (
        db.query(Video)
        .filter(Video.module_id == module_id)
        .count()
    )

    video = Video(
        module_id=module.id,
        order_index=max_index,
        title=body.title,
        description=body.description,
        video_type=body.video_type or "slideshow_narrated",
        estimated_duration_seconds=body.estimated_duration_seconds,
        source_video_url=body.source_video_url,
        status=body.status or "draft",
    )
    db.add(video)
    _mark_course_changed(module.course_id, db)
    db.commit()
    db.refresh(video)

    logger.info(f"Video created: {video.id} in module {module_id} by user {current_user.id}")
    return video


@router.get(
    "/api/modules/{module_id}/videos",
    response_model=List[VideoResponse],
)
def list_videos(
    module_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_creator),
) -> List[Video]:
    """List all videos for a module, ordered by order_index."""
    module = _get_module_or_404(module_id, db, current_user)
    videos = (
        db.query(Video)
        .filter(Video.module_id == module.id)
        .order_by(Video.order_index)
        .all()
    )
    return videos


@router.get(
    "/api/videos/{video_id}",
    response_model=VideoResponse,
)
def get_video(
    video_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_creator),
) -> Video:
    """Get a single video by id."""
    video = db.query(Video).join(Module).join(Course).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video not found")
    if current_user.role.value != "admin" and video.module.course.creator_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return video


@router.put(
    "/api/videos/{video_id}",
    response_model=VideoResponse,
)
def update_video(
    video_id: int,
    body: VideoUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_creator),
) -> Video:
    """Partial update of a video."""
    video = db.query(Video).join(Module).join(Course).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video not found")
    if current_user.role.value != "admin" and video.module.course.creator_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(video, field, value)

    video.updated_at = datetime.utcnow()
    _mark_course_changed(video.module.course_id, db)
    db.commit()
    db.refresh(video)

    logger.info(f"Video updated: {video.id} by user {current_user.id}")
    return video


@router.delete("/api/videos/{video_id}")
def delete_video(
    video_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_creator),
) -> dict:
    """Delete a video (cascade deletes slides)."""
    video = db.query(Video).join(Module).join(Course).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video not found")
    if current_user.role.value != "admin" and video.module.course.creator_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    course_id = video.module.course_id
    db.delete(video)
    _mark_course_changed(course_id, db)
    db.commit()

    logger.info(f"Video deleted: {video_id} by user {current_user.id}")
    return {"message": "Video deleted"}


@router.post("/api/modules/{module_id}/videos/reorder")
def reorder_videos(
    module_id: int,
    body: VideoReorderRequest,
    db: Session = Depends(get_db),
    current_user=Depends(require_creator),
) -> dict:
    """Atomically reassign order_index for all siblings in a single transaction."""
    module = _get_module_or_404(module_id, db, current_user)

    # Validate all ids belong to this module in one query
    videos = (
        db.query(Video)
        .filter(
            Video.id.in_(body.video_ids),
            Video.module_id == module_id,
        )
        .all()
    )
    if len(videos) != len(body.video_ids):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Some video IDs do not belong to this module",
        )

    id_to_video = {v.id: v for v in videos}
    for idx, vid in enumerate(body.video_ids):
        id_to_video[vid].order_index = idx

    db.commit()  # single transaction — no order_index drift

    logger.info(f"Videos reordered in module {module_id} by user {current_user.id}")
    return {"message": "Reordered"}
