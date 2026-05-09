"""
Block CRUD router.
Available to creator and admin roles only.
No reorder endpoint — order_index is a grid z-order, updated via PUT.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List, Optional
import logging

from database import get_db
from models import Course, Module, Video, Slide, Block
from middleware.auth_middleware import require_creator

logger = logging.getLogger(__name__)

router = APIRouter(tags=["blocks"])


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

class BlockCreate(BaseModel):
    type: str
    content: Optional[dict] = None
    style: Optional[dict] = None
    alt_text: Optional[str] = None
    grid_position: Optional[dict] = None
    order_index: Optional[int] = 0


class BlockUpdate(BaseModel):
    type: Optional[str] = None
    content: Optional[dict] = None
    style: Optional[dict] = None
    alt_text: Optional[str] = None
    grid_position: Optional[dict] = None
    order_index: Optional[int] = None


class BlockResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    slide_id: int
    order_index: int
    type: str
    content: Optional[dict]
    style: Optional[dict]
    alt_text: Optional[str]
    grid_position: Optional[dict]
    created_at: datetime
    updated_at: Optional[datetime]


# ---------------------------------------------------------------------------
# Ownership helper
# ---------------------------------------------------------------------------

def _get_slide_or_404(slide_id: int, db: Session, current_user) -> Slide:
    """Fetch slide (with full parent chain join), raise 404 if missing, 403 if not owner."""
    slide = (
        db.query(Slide)
        .join(Video, Slide.video_id == Video.id)
        .join(Module, Video.module_id == Module.id)
        .join(Course, Module.course_id == Course.id)
        .filter(Slide.id == slide_id)
        .first()
    )
    if not slide:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Slide not found")
    # Load course via ORM relationships for ownership check
    course = slide.video.module.course
    if current_user.role.value != "admin" and course.creator_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return slide


def _get_block_or_404(block_id: int, db: Session, current_user) -> Block:
    """Fetch block (with full parent chain join), raise 404 if missing, 403 if not owner."""
    block = (
        db.query(Block)
        .join(Slide, Block.slide_id == Slide.id)
        .join(Video, Slide.video_id == Video.id)
        .join(Module, Video.module_id == Module.id)
        .join(Course, Module.course_id == Course.id)
        .filter(Block.id == block_id)
        .first()
    )
    if not block:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Block not found")
    course = block.slide.video.module.course
    if current_user.role.value != "admin" and course.creator_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return block


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post(
    "/api/slides/{slide_id}/blocks",
    response_model=BlockResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_block(
    slide_id: int,
    body: BlockCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_creator),
) -> Block:
    """Create a new block on the given slide."""
    slide = _get_slide_or_404(slide_id, db, current_user)

    block = Block(
        slide_id=slide.id,
        order_index=body.order_index or 0,
        type=body.type,
        content=body.content,
        style=body.style,
        alt_text=body.alt_text,
        grid_position=body.grid_position,
    )
    db.add(block)
    db.commit()
    db.refresh(block)

    logger.info(f"Block created: {block.id} on slide {slide_id} by user {current_user.id}")
    return block


@router.get(
    "/api/slides/{slide_id}/blocks",
    response_model=List[BlockResponse],
)
def list_blocks(
    slide_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_creator),
) -> List[Block]:
    """List all blocks for a slide, ordered by order_index."""
    slide = _get_slide_or_404(slide_id, db, current_user)
    blocks = (
        db.query(Block)
        .filter(Block.slide_id == slide.id)
        .order_by(Block.order_index)
        .all()
    )
    return blocks


@router.get(
    "/api/blocks/{block_id}",
    response_model=BlockResponse,
)
def get_block(
    block_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_creator),
) -> Block:
    """Get a single block by id."""
    return _get_block_or_404(block_id, db, current_user)


@router.put(
    "/api/blocks/{block_id}",
    response_model=BlockResponse,
)
def update_block(
    block_id: int,
    body: BlockUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_creator),
) -> Block:
    """Partial update of a block (type, content, style, alt_text, grid_position, order_index)."""
    block = _get_block_or_404(block_id, db, current_user)

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(block, field, value)

    block.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(block)

    logger.info(f"Block updated: {block.id} by user {current_user.id}")
    return block


@router.delete("/api/blocks/{block_id}")
def delete_block(
    block_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_creator),
) -> dict:
    """Delete a block."""
    block = _get_block_or_404(block_id, db, current_user)

    db.delete(block)
    db.commit()

    logger.info(f"Block deleted: {block_id} by user {current_user.id}")
    return {"message": "Block deleted"}
