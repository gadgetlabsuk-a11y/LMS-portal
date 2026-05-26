"""
Course management routes.
Provides CRUD operations for courses and enrollment management.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, Request, UploadFile, File, Form
from fastapi.responses import StreamingResponse, HTMLResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session, selectinload
from sqlalchemy.orm.attributes import flag_modified
from datetime import datetime, timezone
from typing import List, Literal, Optional, Dict, Any
from pathlib import Path
import io
import logging
from sse_starlette.sse import EventSourceResponse

from database import get_db
from models import User, Course, CourseStatus, Enrollment, AuditLog, ApiUsage, Module, Quiz, Question
from models.models import CourseVersion
from middleware.auth_middleware import require_creator, get_current_active_user, get_client_ip
from services.claude_service import ClaudeService
from services.document_service import DocumentService
from services.script_service import ScriptService
from services.slide_service import SlideService
from services.tts_service import TTSService
from services.player_service import PlayerService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/courses", tags=["courses"])


claude_service = ClaudeService()


class CourseCreate(BaseModel):
    """Course creation model."""

    title: str
    description: Optional[str] = None
    status: CourseStatus = CourseStatus.DRAFT
    # Phase 12 identity fields (all optional — backward compatible)
    audience_level: Optional[str] = None
    learning_objectives: Optional[List[str]] = None  # max 5; validated client-side
    ai_tone_preset: Optional[str] = None
    ai_custom_prompt: Optional[str] = None
    summary: Optional[str] = None


class CourseUpdate(BaseModel):
    """Course update model."""

    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[CourseStatus] = None


class AiDescriptionRequest(BaseModel):
    """Request body for AI description generation."""

    topic: str
    tone_preset: Optional[str] = "professional"


class AiObjectivesRequest(BaseModel):
    """Request body for AI objectives generation."""

    course_title: str
    description: Optional[str] = None
    tone_preset: Optional[str] = "professional"


class CourseResponse(BaseModel):
    """Course response model."""

    id: int
    title: str
    description: Optional[str]
    status: CourseStatus
    creator_id: int
    created_at: datetime
    updated_at: datetime
    has_content: bool = False
    # Phase 12 additions
    audience_level: Optional[str] = None
    learning_objectives: Optional[List[str]] = None
    ai_tone_preset: Optional[str] = None

    class Config:
        from_attributes = True


class CourseDetailResponse(CourseResponse):
    """Detailed course response.

    The legacy ``content`` JSON blob was retired in v1.0 (course content now
    lives in relational Module/Video/Slide/Block tables), so this no longer
    exposes a ``content`` field.
    """


class EnrollmentResponse(BaseModel):
    """Enrollment response model."""

    id: int
    user_id: int
    course_id: int
    progress: float
    completed: bool
    enrolled_at: datetime
    completed_at: Optional[datetime]

    class Config:
        from_attributes = True


class CourseListResponse(BaseModel):
    """Course list response with pagination."""

    total: int
    page: int
    page_size: int
    items: List[CourseResponse]


class PreflightResult(BaseModel):
    """Single preflight check result."""
    rule: str
    status: Literal["pass", "warn", "fail"]
    message: str
    fix_url: Optional[str] = None


class PreflightResponse(BaseModel):
    """Preflight check response."""
    can_publish: bool
    results: List[PreflightResult]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_owned_course_or_404(course_id: int, current_user, db: Session) -> Course:
    """Fetch course, raise 404 if missing, 403 if not owner."""
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")
    if current_user.role.value != "admin" and course.creator_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return course


def _run_preflight(course: Course, db: Session) -> List[PreflightResult]:
    """Run publish readiness checks; return list of PreflightResult."""
    results = []

    # Rule: course_has_title
    if not course.title or not course.title.strip():
        results.append(PreflightResult(
            rule="course_has_title",
            status="fail",
            message="Course title is required.",
            fix_url=f"/creator/courses/{course.id}/builder",
        ))
    else:
        results.append(PreflightResult(
            rule="course_has_title",
            status="pass",
            message="Course has a title.",
        ))

    # Rule: thumbnail_uploaded
    if not course.thumbnail_url:
        results.append(PreflightResult(
            rule="thumbnail_uploaded",
            status="warn",
            message="No thumbnail uploaded. Learners will see a placeholder.",
            fix_url=f"/creator/courses/{course.id}/builder",
        ))
    else:
        results.append(PreflightResult(
            rule="thumbnail_uploaded",
            status="pass",
            message="Thumbnail uploaded.",
        ))

    # Rule: has_at_least_one_module
    modules = db.query(Module).filter(Module.course_id == course.id).all()
    if not modules:
        results.append(PreflightResult(
            rule="has_at_least_one_module",
            status="fail",
            message="Course must have at least one module.",
            fix_url=f"/creator/courses/{course.id}/builder",
        ))
    else:
        results.append(PreflightResult(
            rule="has_at_least_one_module",
            status="pass",
            message=f"Course has {len(modules)} module(s).",
        ))

    # Rule: each_quiz_has_minimum_questions
    quizzes = (
        db.query(Quiz)
        .join(Module, Quiz.module_id == Module.id)
        .filter(Module.course_id == course.id)
        .all()
    )
    for quiz in quizzes:
        q_count = db.query(Question).filter(Question.quiz_id == quiz.id).count()
        if q_count < 3:
            results.append(PreflightResult(
                rule="each_quiz_has_minimum_questions",
                status="fail",
                message=f"Quiz '{quiz.title}' has {q_count} question(s). Minimum is 3.",
                fix_url=f"/creator/courses/{course.id}/quizzes/{quiz.id}",
            ))
        else:
            results.append(PreflightResult(
                rule="each_quiz_has_minimum_questions",
                status="pass",
                message=f"Quiz '{quiz.title}' has {q_count} questions.",
            ))

    return results


def _serialize_course_tree(course_id: int, db: Session, for_player: bool = False) -> dict:
    """Eager-load full course tree and return as serialisable dict.

    for_player=False (default, used by the publish snapshot): module-level
    quizzes are serialized WITH correct_answer so the snapshot can grade.
    for_player=True (used by the creator preview that feeds the React player):
    module-level quizzes are serialized in the learner player shape (mirrors
    _quiz_json in learn_player.py) — NO correct_answer / explanation leaked.
    """
    from models import Video, Slide, Block
    course = (
        db.query(Course)
        .options(
            selectinload(Course.modules).selectinload(Module.videos).selectinload(
                Video.slides
            ).selectinload(Slide.blocks),
            selectinload(Course.modules).selectinload(Module.quizzes).selectinload(
                Quiz.questions
            ),
            selectinload(Course.modules).selectinload(Module.videos).selectinload(
                Video.quizzes
            ).selectinload(Quiz.questions),
        )
        .filter(Course.id == course_id)
        .first()
    )
    if not course:
        return {}

    modules_data = []
    for mod in course.modules:
        videos_data = []
        for vid in mod.videos:
            slides_data = []
            for slide in vid.slides:
                blocks_data = [
                    {
                        "id": b.id,
                        "type": b.type,
                        "content": b.content,
                        "order_index": b.order_index,
                    }
                    for b in slide.blocks
                ]
                slides_data.append({
                    "id": slide.id,
                    "order_index": slide.order_index,
                    "narration_script": slide.narration_script,
                    "narration_audio_url": slide.narration_audio_url,
                    "layout_id": slide.layout_id,
                    "blocks": blocks_data,
                })
            # Video-level quizzes in the LEARNER player shape (mirrors
            # _quiz_json in learn_player.py) — read-only, NO correct_answer /
            # explanation leaked. The React player reads quizzes here.
            video_quizzes = []
            for quiz in sorted(vid.quizzes, key=lambda q: q.order_index):
                video_quizzes.append({
                    "id": quiz.id,
                    "title": quiz.title,
                    "pass_rate": quiz.pass_rate,
                    "attempts_allowed": quiz.attempts_allowed,
                    "attempts_used": 0,
                    "attempts_remaining": quiz.attempts_allowed,
                    "passed": False,
                    "last_score": None,
                    "questions": [
                        {
                            "id": q.id,
                            "type": q.type,
                            "prompt": q.prompt,
                            "options": q.options,
                            "points": q.points,
                            "order_index": q.order_index,
                        }
                        for q in sorted(quiz.questions, key=lambda x: x.order_index)
                    ],
                })
            videos_data.append({
                "id": vid.id,
                "title": vid.title,
                "order_index": vid.order_index,
                "slides": slides_data,
                "quizzes": video_quizzes,
            })
        quizzes_data = []
        if for_player:
            # Module-level quizzes in the LEARNER player shape (mirrors
            # _quiz_json in learn_player.py) — read-only, NO correct_answer /
            # explanation leaked. The React player reads quizzes here.
            for quiz in sorted(mod.quizzes, key=lambda q: q.order_index):
                quizzes_data.append({
                    "id": quiz.id,
                    "title": quiz.title,
                    "pass_rate": quiz.pass_rate,
                    "attempts_allowed": quiz.attempts_allowed,
                    "attempts_used": 0,
                    "attempts_remaining": quiz.attempts_allowed,
                    "passed": False,
                    "last_score": None,
                    "questions": [
                        {
                            "id": q.id,
                            "type": q.type,
                            "prompt": q.prompt,
                            "options": q.options,
                            "points": q.points,
                            "order_index": q.order_index,
                        }
                        for q in sorted(quiz.questions, key=lambda x: x.order_index)
                    ],
                })
        else:
            # Publish-snapshot shape: keep correct_answer for grading.
            for quiz in mod.quizzes:
                questions_data = [
                    {
                        "id": q.id,
                        "type": q.type,
                        "prompt": q.prompt,
                        "options": q.options,
                        "correct_answer": q.correct_answer,
                        "order_index": q.order_index,
                    }
                    for q in quiz.questions
                ]
                quizzes_data.append({
                    "id": quiz.id,
                    "title": quiz.title,
                    "questions": questions_data,
                })
        modules_data.append({
            "id": mod.id,
            "title": mod.title,
            "order_index": mod.order_index,
            "videos": videos_data,
            "quizzes": quizzes_data,
        })

    return {
        "id": course.id,
        "title": course.title,
        "description": course.description,
        "modules": modules_data,
    }


def _mark_course_changed(course_id: int, db: Session) -> None:
    """Set HAS_UNPUBLISHED_CHANGES on a PUBLISHED course.

    Only transitions when status == PUBLISHED — no-op for DRAFT or ARCHIVED.
    Caller is responsible for db.commit().
    """
    course = db.query(Course).filter(Course.id == course_id).first()
    if course and course.status == CourseStatus.PUBLISHED:
        course.status = CourseStatus.HAS_UNPUBLISHED_CHANGES
        db.add(course)


@router.get("", response_model=CourseListResponse)
def list_courses(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    status: Optional[CourseStatus] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_creator),
) -> dict:
    """
    List courses with pagination and filtering.

    Args:
        page: Page number
        page_size: Items per page
        status: Filter by course status
        search: Search by title or description
        db: Database session
        current_user: Current creator/admin user

    Returns:
        Paginated course list
    """
    query = db.query(Course)

    # Filter by creator (non-admins only see their own courses)
    if current_user.role.value != "admin":
        query = query.filter(Course.creator_id == current_user.id)

    # Status filter
    if status:
        query = query.filter(Course.status == status)

    # Search filter
    if search:
        query = query.filter(
            (Course.title.ilike(f"%{search}%"))
            | (Course.description.ilike(f"%{search}%"))
        )

    # Count total
    total = query.count()

    # Pagination
    courses = query.order_by(Course.created_at.desc()).offset(
        (page - 1) * page_size
    ).limit(page_size).all()

    logger.info(f"Listed courses: user={current_user.id}, page={page}")

    # Build items with has_content flag
    items = []
    for c in courses:
        item = CourseResponse.model_validate(c)
        item.has_content = bool(c.modules)
        items.append(item)

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": items,
    }


@router.post("", response_model=CourseResponse, status_code=status.HTTP_201_CREATED)
def create_course(
    request: Request,
    course_data: CourseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_creator),
) -> Course:
    """
    Create a new course.

    Args:
        course_data: Course creation data
        db: Database session
        current_user: Current creator/admin user

    Returns:
        Created course

    Raises:
        HTTPException: If creation fails
    """
    course = Course(
        title=course_data.title,
        description=course_data.description,
        status=course_data.status,
        creator_id=current_user.id,
    )
    course.audience_level = course_data.audience_level
    course.learning_objectives = course_data.learning_objectives
    course.ai_tone_preset = course_data.ai_tone_preset
    course.ai_custom_prompt = course_data.ai_custom_prompt
    course.summary = course_data.summary

    db.add(course)
    db.commit()
    db.refresh(course)

    # Log audit
    audit_log = AuditLog(
        user_id=current_user.id,
        action="CREATE",
        resource_type="Course",
        resource_id=course.id,
        ip_address=get_client_ip(request),
    )
    db.add(audit_log)
    db.commit()

    logger.info(f"Course created: {course.id} by user {current_user.id}")

    return course


@router.post("/ai/generate-description")
async def generate_description_stream(
    request: Request,
    body: AiDescriptionRequest,
    current_user: User = Depends(require_creator),
):
    """Stream AI-generated course description tokens via SSE."""

    async def generator():
        async for token in claude_service.stream_course_description(body.topic, body.tone_preset):
            if await request.is_disconnected():
                break
            yield {"data": token}

    return EventSourceResponse(generator())


@router.post("/ai/generate-objectives")
async def generate_objectives_stream(
    request: Request,
    body: AiObjectivesRequest,
    current_user: User = Depends(require_creator),
):
    """Stream AI-generated learning objectives tokens via SSE."""

    async def generator():
        async for token in claude_service.stream_learning_objectives(
            body.course_title, body.description, body.tone_preset
        ):
            if await request.is_disconnected():
                break
            yield {"data": token}

    return EventSourceResponse(generator())


@router.get("/{course_id}/preview")
def preview_course(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_creator),
) -> dict:
    """Return full course tree for creator preview — bypasses PUBLISHED filter (PREVIEW-01, PREVIEW-02)."""
    _get_owned_course_or_404(course_id, current_user, db)
    tree = _serialize_course_tree(course_id, db, for_player=True)
    return tree


@router.get("/{course_id}/preflight", response_model=PreflightResponse)
def preflight_course(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_creator),
) -> PreflightResponse:
    """Run publish readiness checks and return structured results (PUBLISH-02, PUBLISH-03, PUBLISH-04)."""
    course = _get_owned_course_or_404(course_id, current_user, db)
    results = _run_preflight(course, db)
    can_publish = all(r.status != "fail" for r in results)
    return PreflightResponse(can_publish=can_publish, results=results)


@router.post("/{course_id}/publish", response_model=CourseResponse)
def publish_course(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_creator),
) -> Course:
    """Transition course DRAFT→PUBLISHED, create CourseVersion snapshot (PUBLISH-05, PUBLISH-06)."""
    course = _get_owned_course_or_404(course_id, current_user, db)
    results = _run_preflight(course, db)
    fail_results = [r for r in results if r.status == "fail"]
    if fail_results:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Preflight failed: {fail_results[0].message}",
        )

    # Build snapshot
    snapshot = _serialize_course_tree(course_id, db)

    # Create version row
    version_number = course.version or 1
    version_row = CourseVersion(
        course_id=course.id,
        version_number=version_number,
        snapshot=snapshot,
        published_at=datetime.now(timezone.utc),
    )
    db.add(version_row)

    # Update course
    course.version = version_number + 1
    course.status = CourseStatus.PUBLISHED
    course.published_at = datetime.now(timezone.utc)
    db.add(course)
    db.commit()
    db.refresh(course)

    logger.info(f"Course published: {course.id} v{version_number} by user {current_user.id}")
    return course


@router.post("/{course_id}/archive", response_model=CourseResponse)
def archive_course(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_creator),
) -> Course:
    """Transition course to ARCHIVED status (PUBLISH-08)."""
    course = _get_owned_course_or_404(course_id, current_user, db)
    course.status = CourseStatus.ARCHIVED
    db.add(course)
    db.commit()
    db.refresh(course)

    logger.info(f"Course archived: {course.id} by user {current_user.id}")
    return course


@router.get("/{course_id}", response_model=CourseDetailResponse)
def get_course(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_creator),
) -> Course:
    """
    Get course details by ID.

    Args:
        course_id: Course ID
        db: Database session
        current_user: Current creator/admin user

    Returns:
        Course details

    Raises:
        HTTPException: If course not found or access denied
    """
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        logger.warning(f"Course not found: {course_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found",
        )

    # Check access (creator or admin)
    if current_user.role.value != "admin" and course.creator_id != current_user.id:
        logger.warning(f"Access denied to course {course_id} for user {current_user.id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    return course


@router.put("/{course_id}", response_model=CourseResponse)
def update_course(
    request: Request,
    course_id: int,
    course_data: CourseUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_creator),
) -> Course:
    """
    Update course details.

    Args:
        course_id: Course ID
        course_data: Update data
        db: Database session
        current_user: Current creator/admin user

    Returns:
        Updated course

    Raises:
        HTTPException: If course not found or access denied
    """
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        logger.warning(f"Course update failed: course not found: {course_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found",
        )

    # Check access
    if current_user.role.value != "admin" and course.creator_id != current_user.id:
        logger.warning(f"Access denied to update course {course_id} for user {current_user.id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    # Update fields
    if course_data.title is not None:
        course.title = course_data.title

    if course_data.description is not None:
        course.description = course_data.description

    if course_data.status is not None:
        course.status = course_data.status

    course.updated_at = datetime.now(timezone.utc)

    db.add(course)
    db.commit()
    db.refresh(course)

    # Log audit
    audit_log = AuditLog(
        user_id=current_user.id,
        action="UPDATE",
        resource_type="Course",
        resource_id=course.id,
        ip_address=get_client_ip(request),
    )
    db.add(audit_log)
    db.commit()

    logger.info(f"Course updated: {course.id} by user {current_user.id}")

    return course


@router.delete("/{course_id}")
def delete_course(
    request: Request,
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_creator),
) -> dict:
    """
    Delete a course.

    Args:
        course_id: Course ID
        db: Database session
        current_user: Current creator/admin user

    Returns:
        Success message

    Raises:
        HTTPException: If course not found or access denied
    """
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        logger.warning(f"Course delete failed: course not found: {course_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found",
        )

    # Check access
    if current_user.role.value != "admin" and course.creator_id != current_user.id:
        logger.warning(f"Access denied to delete course {course_id} for user {current_user.id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    db.delete(course)
    db.commit()

    # Log audit
    audit_log = AuditLog(
        user_id=current_user.id,
        action="DELETE",
        resource_type="Course",
        resource_id=course.id,
        ip_address=get_client_ip(request),
    )
    db.add(audit_log)
    db.commit()

    logger.info(f"Course deleted: {course.id} by user {current_user.id}")

    return {"message": "Course deleted successfully"}


@router.post("/{course_id}/enroll", response_model=EnrollmentResponse, status_code=status.HTTP_201_CREATED)
def enroll_in_course(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Enrollment:
    """
    Enroll user in a course.

    Args:
        course_id: Course ID
        db: Database session
        current_user: Current user

    Returns:
        Created enrollment

    Raises:
        HTTPException: If course not found or user already enrolled
    """
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found",
        )

    # Check if already enrolled
    existing = db.query(Enrollment).filter(
        (Enrollment.user_id == current_user.id) & (Enrollment.course_id == course_id)
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Already enrolled in this course",
        )

    # Create enrollment
    enrollment = Enrollment(
        user_id=current_user.id,
        course_id=course_id,
        progress=0.0,
        completed=False,
    )

    db.add(enrollment)
    db.commit()
    db.refresh(enrollment)

    logger.info(f"User {current_user.id} enrolled in course {course_id}")

    return enrollment


@router.put("/{course_id}/progress")
def update_progress(
    course_id: int,
    progress: float = Query(..., ge=0, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> EnrollmentResponse:
    """
    Update course progress for enrolled user.

    Args:
        course_id: Course ID
        progress: Progress percentage (0-100)
        db: Database session
        current_user: Current user

    Returns:
        Updated enrollment

    Raises:
        HTTPException: If enrollment not found
    """
    enrollment = db.query(Enrollment).filter(
        (Enrollment.user_id == current_user.id) & (Enrollment.course_id == course_id)
    ).first()

    if not enrollment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Enrollment not found",
        )

    enrollment.progress = progress

    # Mark as completed if progress is 100
    if progress >= 100:
        enrollment.completed = True
        enrollment.completed_at = datetime.now(timezone.utc)

    db.add(enrollment)
    db.commit()
    db.refresh(enrollment)

    logger.info(f"Progress updated: user={current_user.id}, course={course_id}, progress={progress}")

    return enrollment


@router.post("/{course_id}/generate-script")
async def generate_script(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_creator),
) -> StreamingResponse:
    """
    Generate a presenter script (.docx) for a course.

    Legacy export: targets the retired course.content JSON blob. Returns HTTP 400
    for slide-based courses (which have no such blob) until the export is rebuilt.
    """
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")

    if current_user.role.value != "admin" and course.creator_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    legacy_content = getattr(course, "content", None)
    if not legacy_content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Script export isn't available for courses built with the slide editor. "
                "It targets the retired course-content format and is pending a rebuild."
            ),
        )

    try:
        service = ScriptService()
        docx_bytes = await service.generate_script(legacy_content)

        safe_title = "".join(c if c.isalnum() or c in " -_" else "_" for c in course.title)
        filename = f"{safe_title}_script.docx"

        logger.info(f"Script generated for course {course_id} by user {current_user.id}")

        return StreamingResponse(
            io.BytesIO(docx_bytes),
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    except Exception as e:
        logger.error(f"Script generation failed for course {course_id}: {type(e).__name__}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Script generation failed: {type(e).__name__}: {str(e)}",
        )


@router.post("/{course_id}/generate-slides")
def generate_slides(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_creator),
) -> StreamingResponse:
    """
    Generate a PowerPoint presentation (.pptx) for a course.

    Legacy export: targets the retired course.content JSON blob. Returns HTTP 400
    for slide-based courses (which have no such blob) until the export is rebuilt.
    """
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")

    if current_user.role.value != "admin" and course.creator_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    legacy_content = getattr(course, "content", None)
    if not legacy_content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "PowerPoint export isn't available for courses built with the slide editor. "
                "It targets the retired course-content format and is pending a rebuild."
            ),
        )

    try:
        service = SlideService()
        pptx_bytes = service.generate_slides(legacy_content)

        safe_title = "".join(c if c.isalnum() or c in " -_" else "_" for c in course.title)
        filename = f"{safe_title}_slides.pptx"

        logger.info(f"Slides generated for course {course_id} by user {current_user.id}")

        return StreamingResponse(
            io.BytesIO(pptx_bytes),
            media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    except Exception as e:
        logger.error(f"Slide generation failed for course {course_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Slide generation failed: {str(e)}",
        )


@router.post("/{course_id}/generate-voiceover")
async def generate_voiceover(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_creator),
) -> dict:
    """
    Generate text-to-speech audio for all lessons in a course.

    Legacy export: targets the retired course.content JSON blob. Returns HTTP 400
    for slide-based courses (which have no such blob) until the export is rebuilt.
    Uses ElevenLabs API to create MP3 audio files.

    Args:
        course_id: Course ID
        db: Database session
        current_user: Current creator/admin user

    Returns:
        Dictionary with audio_urls mapping lesson keys to audio URLs

    Raises:
        HTTPException: If course not found, access denied, or generation fails
    """
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")

    if current_user.role.value != "admin" and course.creator_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    legacy_content = getattr(course, "content", None)
    if not legacy_content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Course-level voiceover isn't available for courses built with the slide editor. "
                "Per-slide narration is generated from the editor instead."
            ),
        )

    try:
        service = TTSService()
        audio_urls = await service.generate_audio_for_course(legacy_content, course_id)

        # Store audio_urls back into the legacy content blob.
        # Must use flag_modified so SQLAlchemy detects the JSON mutation.
        updated_content = dict(legacy_content)
        updated_content["audio_urls"] = audio_urls
        course.content = updated_content
        course.updated_at = datetime.now(timezone.utc)
        flag_modified(course, "content")

        db.add(course)
        db.commit()

        logger.info(f"Voiceover generated for course {course_id} by user {current_user.id}")

        return {
            "message": "Voiceover generated",
            "audio_urls": audio_urls,
        }

    except ValueError as e:
        logger.error(f"TTS configuration error for course {course_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Voiceover generation failed for course {course_id}: {type(e).__name__}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Voiceover generation failed: {type(e).__name__}: {str(e)}",
        )


@router.post("/{course_id}/lessons/{module_id}/{lesson_id}/upload-clip")
async def upload_video_clip(
    request: Request,
    course_id: int,
    module_id: str,
    lesson_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_creator),
) -> dict:
    """
    Upload a video clip for a course lesson.

    Args:
        request: HTTP request
        course_id: Course ID
        module_id: Module ID
        lesson_id: Lesson ID
        file: Video file to upload (.mp4, .mov, .webm, .avi)
        db: Database session
        current_user: Current creator/admin user

    Returns:
        Dictionary with message, video_url, course_id, module_id, lesson_id

    Raises:
        HTTPException: If file validation fails, size limit exceeded, or update fails
    """
    try:
        # Validate course exists and access
        course = db.query(Course).filter(Course.id == course_id).first()
        if not course:
            logger.warning(f"Course not found: {course_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Course not found",
            )

        if current_user.role.value != "admin" and course.creator_id != current_user.id:
            logger.warning(f"Access denied to course {course_id} for user {current_user.id}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied",
            )

        # Legacy clip upload wrote into the retired ``course.content`` JSON blob.
        # Slide-based courses attach video through the slide editor, so this path is
        # disabled (before any file is read/written) rather than 500-ing on the
        # missing attribute.
        if getattr(course, "content", None) is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "This upload route is for legacy courses only. Upload video for "
                    "slide-based courses through the slide editor."
                ),
            )

        # Validate file extension
        allowed_extensions = {".mp4", ".mov", ".webm", ".avi"}
        file_ext = "." + file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""

        if file_ext not in allowed_extensions:
            logger.warning(
                f"Invalid video extension attempted: {file_ext} by user {current_user.id}"
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported file type. Allowed types: {', '.join(allowed_extensions)}",
            )

        # Check Content-Length header
        content_length = request.headers.get("content-length")
        max_size = 500 * 1024 * 1024  # 500MB

        if content_length and int(content_length) > max_size:
            logger.warning(
                f"Video file size exceeded: {content_length} bytes by user {current_user.id}"
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File too large. Maximum size: 500MB",
            )

        # Read file bytes and check size
        file_bytes = await file.read()
        if len(file_bytes) > max_size:
            logger.warning(
                f"Video file size exceeded: {len(file_bytes)} bytes by user {current_user.id}"
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File too large. Maximum size: 500MB",
            )

        # Create upload directory
        upload_dir = Path(f"uploads/videos/course_{course_id}")
        upload_dir.mkdir(parents=True, exist_ok=True)

        # Save file as .mp4
        filename = f"lesson_{module_id}_{lesson_id}.mp4"
        file_path = upload_dir / filename

        with open(file_path, "wb") as f:
            f.write(file_bytes)

        # Build video URL
        video_url = f"/uploads/videos/course_{course_id}/{filename}"

        # Update course content
        if not course.content:
            course.content = {"modules": []}

        # Find module and lesson, then update video_url
        modules = course.content.get("modules", [])
        found = False

        for module in modules:
            if module.get("id") == module_id:
                lessons = module.get("lessons", [])
                for lesson in lessons:
                    if lesson.get("id") == lesson_id:
                        lesson["video_url"] = video_url
                        found = True
                        break
                if found:
                    break

        if not found:
            logger.warning(
                f"Module or lesson not found: course={course_id}, module={module_id}, lesson={lesson_id}"
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Module or lesson not found in course content",
            )

        # Persist changes
        course.content = course.content
        flag_modified(course, "content")
        db.add(course)
        db.commit()

        logger.info(
            f"Video clip uploaded: course={course_id}, module={module_id}, lesson={lesson_id} by user {current_user.id}"
        )

        return {
            "message": "Clip uploaded",
            "video_url": video_url,
            "course_id": course_id,
            "module_id": module_id,
            "lesson_id": lesson_id,
        }

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"Video clip upload failed: {type(e).__name__}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Video clip upload failed: {type(e).__name__}: {str(e)}",
        )


def _player_placeholder_html(course_title: str) -> str:
    """Friendly placeholder shown when a course has no legacy player content.

    The interactive HTML player was built for the retired ``course.content`` JSON
    blob. Courses authored with the relational slide editor have no such blob, so
    the embedded preview/player shows this clean message (HTTP 200) instead of
    erroring. The full relational player is tracked as a separate rebuild.
    """
    safe_title = (
        (course_title or "This course")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{safe_title}</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
html,body{{height:100%}}
body{{
  font-family:Arial,Helvetica,sans-serif;
  display:flex;align-items:center;justify-content:center;
  min-height:100vh;padding:2rem;
  background:linear-gradient(-45deg,#007BC0,#0B3F75);
  color:#fff;text-align:center;
}}
.card{{max-width:32rem}}
.card h1{{font-size:1.5rem;font-weight:700;margin-bottom:0.75rem}}
.card p{{font-size:1rem;line-height:1.6;color:#F0F7FE;opacity:0.92}}
.badge{{
  display:inline-block;margin-bottom:1.25rem;padding:0.35rem 0.9rem;
  border-radius:999px;background:rgba(255,255,255,0.15);
  font-size:0.8rem;letter-spacing:0.04em;text-transform:uppercase;
}}
</style>
</head>
<body>
<div class="card">
<span class="badge">Preview</span>
<h1>{safe_title}</h1>
<p>This course doesn't have a playable preview yet. Build slides in the editor and publish the course to generate the learner experience.</p>
</div>
</body>
</html>"""


@router.get("/{course_id}/player", response_class=HTMLResponse)
def get_player(
    course_id: int,
    db: Session = Depends(get_db),
) -> str:
    """
    Get the interactive HTML course player.

    No authentication required — learners access the player directly.
    The player displays all course slides and handles audio playback.

    Args:
        course_id: Course ID
        db: Database session

    Returns:
        Complete HTML string for the player

    Raises:
        HTTPException: If course not found or has no content
    """
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")

    # The legacy JSON ``course.content`` blob was retired in favour of the relational
    # Module/Video/Slide/Block model. This player still expects the old shape, so it
    # has no playable data for slide-based courses. Degrade gracefully with a clean
    # placeholder page (HTTP 200) rather than 500-ing on the missing attribute.
    legacy_content = getattr(course, "content", None)
    if not legacy_content:
        return _player_placeholder_html(course.title)

    try:
        service = PlayerService()
        audio_urls = legacy_content.get("audio_urls", {})
        html = service.generate_player(legacy_content, audio_urls, course_id)

        logger.info(f"Player accessed for course {course_id}")

        return html

    except Exception as e:
        logger.error(f"Player generation failed for course {course_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Player generation failed: {str(e)}",
        )
