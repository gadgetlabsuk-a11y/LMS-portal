"""
Course management routes.
Provides CRUD operations for courses and enrollment management.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, Request, UploadFile, File, Form
from fastapi.responses import StreamingResponse, HTMLResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from pathlib import Path
import io
import logging
from sse_starlette.sse import EventSourceResponse

from database import get_db
from models import User, Course, CourseStatus, Enrollment, AuditLog, ApiUsage
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
    content: Optional[Dict[str, Any]] = None
    status: Optional[CourseStatus] = None


class CourseGenerateRequest(BaseModel):
    """Course generation request model."""

    topic: str
    num_modules: int = 3
    difficulty: str = "intermediate"
    additional_instructions: Optional[str] = None
    videos_per_module: int = 1
    video_duration: str = "medium"
    tone: str = "formal"
    target_audience: str = "general"
    include_assessment: bool = True


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
    """Detailed course response with content."""

    content: Optional[Dict[str, Any]]


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
        item.has_content = bool(c.content)
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

    if course_data.content is not None:
        course.content = course_data.content

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


@router.post("/generate-from-document")
async def generate_course_from_document(
    request: Request,
    file: UploadFile = File(...),
    difficulty: str = Form("intermediate"),
    additional_instructions: Optional[str] = Form(None),
    videos_per_module: int = Form(1),
    video_duration: str = Form("medium"),
    tone: str = Form("formal"),
    target_audience: str = Form("general"),
    include_assessment: bool = Form(True),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_creator),
) -> dict:
    """
    Generate course content from uploaded document file.

    Args:
        request: HTTP request
        file: Uploaded document file (.docx, .pptx, or .pdf)
        difficulty: Difficulty level (beginner, intermediate, advanced)
        additional_instructions: Custom instructions for generation
        videos_per_module: Number of video segments per module
        video_duration: Target video duration (short, medium, long)
        tone: Presentation tone (formal, conversational, technical)
        target_audience: Target audience (new_starters, experienced, management, general)
        include_assessment: Whether to include final quiz assessment
        db: Database session
        current_user: Current creator/admin user

    Returns:
        Generated course content

    Raises:
        HTTPException: If file is invalid, unsupported, too large, or generation fails
    """
    try:
        # Validate file type
        allowed_extensions = {".docx", ".pptx", ".pdf"}
        file_ext = "." + file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""

        if file_ext not in allowed_extensions:
            logger.warning(
                f"Unsupported file type attempted: {file_ext} by user {current_user.id}"
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported file type. Allowed types: {', '.join(allowed_extensions)}",
            )

        # Read file bytes
        file_bytes = await file.read()

        # Validate file size (10MB max)
        max_file_size = 10 * 1024 * 1024  # 10MB
        if len(file_bytes) > max_file_size:
            logger.warning(
                f"File size exceeded: {len(file_bytes)} bytes by user {current_user.id}"
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File too large. Maximum size: 10MB",
            )

        # Extract text from document
        try:
            document_service = DocumentService()
            document_text = document_service.extract_text(file_bytes, file.filename)
        except ValueError as e:
            logger.warning(f"Document extraction failed: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            )

        # Generate course using Claude
        claude_service = ClaudeService()
        generated_content = await claude_service.generate_course_from_document(
            document_text=document_text,
            filename=file.filename,
            difficulty=difficulty,
            additional_instructions=additional_instructions,
            videos_per_module=videos_per_module,
            video_duration=video_duration,
            tone=tone,
            target_audience=target_audience,
            include_assessment=include_assessment,
        )

        # Save course to database
        course_data = generated_content.get("course", {})
        course = Course(
            title=course_data.get("title", file.filename),
            description=course_data.get("description", ""),
            content=course_data,
            creator_id=current_user.id,
            status=CourseStatus.DRAFT,
        )
        db.add(course)

        # Track API usage
        api_usage = ApiUsage(
            endpoint="/generate-from-document",
            tokens_used=generated_content.get("tokens_used", 0),
            cost_estimate=generated_content.get("cost_estimate", 0.0),
        )
        db.add(api_usage)
        db.commit()
        db.refresh(course)

        logger.info(
            f"Course generated from document and saved (id={course.id}): {file.filename} by user {current_user.id}"
        )

        return {
            "course_id": course.id,
            "content": generated_content,
            "tokens_used": generated_content.get("tokens_used", 0),
            "filename": file.filename,
        }

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"Course generation from document failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Course generation failed: {str(e)}",
        )


@router.post("/generate")
async def generate_course(
    generate_data: CourseGenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_creator),
) -> dict:
    """
    Generate course content using Claude API.

    Args:
        generate_data: Generation parameters
        db: Database session
        current_user: Current creator/admin user

    Returns:
        Generated course content

    Raises:
        HTTPException: If generation fails
    """
    try:
        # Generate course using Claude
        claude_service = ClaudeService()
        generated_content = await claude_service.generate_course(
            topic=generate_data.topic,
            num_modules=generate_data.num_modules,
            difficulty=generate_data.difficulty,
            additional_instructions=generate_data.additional_instructions,
            videos_per_module=generate_data.videos_per_module,
            video_duration=generate_data.video_duration,
            tone=generate_data.tone,
            target_audience=generate_data.target_audience,
            include_assessment=generate_data.include_assessment,
        )

        # Save course to database
        course_data = generated_content.get("course", {})
        course = Course(
            title=course_data.get("title", generate_data.topic),
            description=course_data.get("description", ""),
            content=course_data,
            creator_id=current_user.id,
            status=CourseStatus.DRAFT,
        )
        db.add(course)

        # Track API usage
        api_usage = ApiUsage(
            endpoint="/generate_course",
            tokens_used=generated_content.get("tokens_used", 0),
            cost_estimate=generated_content.get("cost_estimate", 0.0),
        )
        db.add(api_usage)
        db.commit()
        db.refresh(course)

        logger.info(f"Course generated and saved (id={course.id}): {generate_data.topic} by user {current_user.id}")

        return {
            "course_id": course.id,
            "content": generated_content,
            "tokens_used": generated_content.get("tokens_used", 0),
        }

    except Exception as e:
        logger.error(f"Course generation failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Course generation failed: {str(e)}",
        )


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

    Requires the course to have generated content (course.content must not be None).
    """
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")

    if current_user.role.value != "admin" and course.creator_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    if not course.content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Course has no generated content. Generate the course content first.",
        )

    try:
        service = ScriptService()
        docx_bytes = await service.generate_script(course.content)

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

    Requires the course to have generated content (course.content must not be None).
    """
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")

    if current_user.role.value != "admin" and course.creator_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    if not course.content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Course has no generated content. Generate the course content first.",
        )

    try:
        service = SlideService()
        pptx_bytes = service.generate_slides(course.content)

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

    Requires the course to have generated content (course.content must not be None).
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

    if not course.content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Course has no generated content. Generate the course content first.",
        )

    try:
        service = TTSService()
        audio_urls = await service.generate_audio_for_course(course.content, course_id)

        # Store audio_urls in course.content
        # Must use flag_modified so SQLAlchemy detects the JSON mutation
        updated_content = dict(course.content)
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

    if not course.content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Course has no generated content. Generate the course content first.",
        )

    try:
        service = PlayerService()
        audio_urls = course.content.get("audio_urls", {})
        html = service.generate_player(course.content, audio_urls, course_id)

        logger.info(f"Player accessed for course {course_id}")

        return html

    except Exception as e:
        logger.error(f"Player generation failed for course {course_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Player generation failed: {str(e)}",
        )
