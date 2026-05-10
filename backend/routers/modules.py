"""
Module CRUD + reorder router.
Available to creator and admin roles only.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List, Optional
import logging

from database import get_db
from models import Course, Module, CourseStatus
from middleware.auth_middleware import require_creator
from sse_starlette.sse import EventSourceResponse
from services.claude_service import ClaudeService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["modules"])

# Module-level singleton (avoids function-local re-instantiation — Phase 12/13 pattern)
claude_service = ClaudeService()


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

class ModuleCreate(BaseModel):
    title: str
    description: Optional[str] = None
    learning_objectives: Optional[list] = None
    estimated_duration_minutes: Optional[int] = None
    unlock_rule: Optional[str] = "after_previous"
    status: Optional[str] = "draft"


class ModuleUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    learning_objectives: Optional[list] = None
    estimated_duration_minutes: Optional[int] = None
    unlock_rule: Optional[str] = None
    unlock_days_after_enrolment: Optional[int] = None
    status: Optional[str] = None
    pass_rate_override: Optional[int] = None


class ModuleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    course_id: int
    order_index: int
    title: str
    description: Optional[str]
    learning_objectives: Optional[list]
    estimated_duration_minutes: Optional[int]
    unlock_rule: Optional[str]
    status: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]


class ReorderRequest(BaseModel):
    module_ids: List[int]


class AiModuleDescriptionRequest(BaseModel):
    prompt: str
    tone_preset: Optional[str] = "professional"
    document_url: Optional[str] = None  # pre-uploaded doc URL, passed as context string


# ---------------------------------------------------------------------------
# Ownership helper
# ---------------------------------------------------------------------------

def _get_course_or_404(course_id: int, db: Session, current_user) -> Course:
    """Fetch course by id, raise 404 if missing, 403 if not owner."""
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")
    _check_course_ownership(course, current_user)
    return course


def _mark_course_changed(course_id: int, db: Session) -> None:
    """Set HAS_UNPUBLISHED_CHANGES on a PUBLISHED course.

    Only transitions when status == PUBLISHED. Caller is responsible for db.commit().
    """
    course = db.query(Course).filter(Course.id == course_id).first()
    if course and course.status == CourseStatus.PUBLISHED:
        course.status = CourseStatus.HAS_UNPUBLISHED_CHANGES
        db.add(course)


def _check_course_ownership(course: Course, current_user) -> None:
    """Raise 403 if the current_user is not the course owner (admin bypasses)."""
    if current_user.role.value != "admin" and course.creator_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post(
    "/api/courses/{course_id}/modules",
    response_model=ModuleResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_module(
    course_id: int,
    body: ModuleCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_creator),
) -> Module:
    """Create a new module in the given course."""
    course = _get_course_or_404(course_id, db, current_user)

    # Assign next order_index
    max_index = (
        db.query(Module)
        .filter(Module.course_id == course_id)
        .count()
    )

    module = Module(
        course_id=course.id,
        order_index=max_index,
        title=body.title,
        description=body.description,
        learning_objectives=body.learning_objectives,
        estimated_duration_minutes=body.estimated_duration_minutes,
        unlock_rule=body.unlock_rule or "after_previous",
        status=body.status or "draft",
    )
    db.add(module)
    _mark_course_changed(course_id, db)
    db.commit()
    db.refresh(module)

    logger.info(f"Module created: {module.id} in course {course_id} by user {current_user.id}")
    return module


@router.get(
    "/api/courses/{course_id}/modules",
    response_model=List[ModuleResponse],
)
def list_modules(
    course_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_creator),
) -> List[Module]:
    """List all modules for a course, ordered by order_index."""
    course = _get_course_or_404(course_id, db, current_user)
    modules = (
        db.query(Module)
        .filter(Module.course_id == course.id)
        .order_by(Module.order_index)
        .all()
    )
    return modules


@router.post("/api/modules/{module_id}/ai/generate-description")
async def generate_module_description_stream(
    module_id: int,
    request: Request,
    body: AiModuleDescriptionRequest,
    db: Session = Depends(get_db),
    current_user=Depends(require_creator),
):
    """Stream AI-generated module description tokens via SSE.

    CRITICAL: This route is registered BEFORE /{module_id} routes to prevent
    FastAPI path collision — /ai/generate-description would otherwise match
    the /{module_id} wildcard (same fix as Phase 12 SSE routes in courses.py).
    """
    module = db.query(Module).filter(Module.id == module_id).first()
    if not module:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Module not found")
    _check_course_ownership(module.course, current_user)

    doc_context = f"\nReference document available at: {body.document_url}" if body.document_url else ""
    full_prompt = (
        f"Generate a concise, engaging module description for an online course module titled "
        f"'{module.title}'. Topic context: {body.prompt}.{doc_context} "
        f"Tone: {body.tone_preset}. Write 2-4 sentences. No headings or bullet points."
    )

    async def generator():
        async for token in claude_service._stream_text(full_prompt):
            if await request.is_disconnected():
                break
            yield {"data": token}

    return EventSourceResponse(generator())


@router.get(
    "/api/modules/{module_id}",
    response_model=ModuleResponse,
)
def get_module(
    module_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_creator),
) -> Module:
    """Get a single module by id."""
    module = db.query(Module).filter(Module.id == module_id).first()
    if not module:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Module not found")
    _check_course_ownership(module.course, current_user)
    return module


@router.put(
    "/api/modules/{module_id}",
    response_model=ModuleResponse,
)
def update_module(
    module_id: int,
    body: ModuleUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_creator),
) -> Module:
    """Partial update of a module."""
    module = db.query(Module).filter(Module.id == module_id).first()
    if not module:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Module not found")
    _check_course_ownership(module.course, current_user)

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(module, field, value)

    module.updated_at = datetime.utcnow()
    _mark_course_changed(module.course_id, db)
    db.commit()
    db.refresh(module)

    logger.info(f"Module updated: {module.id} by user {current_user.id}")
    return module


@router.delete("/api/modules/{module_id}")
def delete_module(
    module_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_creator),
) -> dict:
    """Delete a module (cascade deletes videos)."""
    module = db.query(Module).filter(Module.id == module_id).first()
    if not module:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Module not found")
    _check_course_ownership(module.course, current_user)

    course_id = module.course_id
    db.delete(module)
    _mark_course_changed(course_id, db)
    db.commit()

    logger.info(f"Module deleted: {module_id} by user {current_user.id}")
    return {"message": "Module deleted"}


@router.post("/api/courses/{course_id}/modules/reorder")
def reorder_modules(
    course_id: int,
    body: ReorderRequest,
    db: Session = Depends(get_db),
    current_user=Depends(require_creator),
) -> dict:
    """Atomically reassign order_index for all siblings in a single transaction."""
    course = _get_course_or_404(course_id, db, current_user)

    # Validate all ids belong to this course in one query
    modules = (
        db.query(Module)
        .filter(
            Module.id.in_(body.module_ids),
            Module.course_id == course_id,
        )
        .all()
    )
    if len(modules) != len(body.module_ids):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Some module IDs do not belong to this course",
        )

    id_to_module = {m.id: m for m in modules}
    for idx, mid in enumerate(body.module_ids):
        id_to_module[mid].order_index = idx

    db.commit()  # single transaction — no order_index drift

    logger.info(f"Modules reordered in course {course_id} by user {current_user.id}")
    return {"message": "Reordered"}
