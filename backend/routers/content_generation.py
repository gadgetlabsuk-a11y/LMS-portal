"""AI generation of a full relational course from uploaded documents.

No router prefix — full /api/... paths are declared per route (mirrors routers/slides.py).
"""
import json
import logging
from typing import List

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from sqlalchemy.orm import Session
from sse_starlette.sse import EventSourceResponse

from config import settings
from database import get_db
from models import User, Course, CourseStatus, Module, Video, Slide, Block, CourseSourceDocument
from middleware.auth_middleware import require_creator
from services.claude_service import ClaudeService, CourseOutline
from services.document_service import DocumentService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["content-generation"])

claude_service = ClaudeService()
document_service = DocumentService()

# Guardrails
MAX_FILES = 10
MAX_MODULES = 8
MAX_VIDEOS_PER_MODULE = 6
MAX_SLIDES_PER_VIDEO = 8
CORPUS_MAX_CHARS = 60000
ALLOWED_EXTS = (".pptx", ".docx", ".pdf")


def _clamp(value: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, value))


def _validate_upload_files(files: List[UploadFile]) -> None:
    """Validate file count and extension before any heavy work."""
    if len(files) > MAX_FILES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Too many files. Maximum {MAX_FILES}.",
        )
    for f in files:
        name = (f.filename or "").lower()
        if not name.endswith(ALLOWED_EXTS):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported file type: {f.filename}. Allowed: .pptx, .docx, .pdf",
            )


async def _extract_corpus(files: List[UploadFile]) -> str:
    """Extract + merge text from uploaded files into a capped corpus. Skips unreadable files."""
    texts: list[str] = []
    for f in files:
        data = await f.read()
        if len(data) > settings.MAX_UPLOAD_SIZE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File too large: {f.filename}. Max {settings.MAX_UPLOAD_SIZE // (1024 * 1024)}MB per file.",
            )
        try:
            texts.append(document_service.extract_text(data, f.filename))
        except Exception as e:
            logger.warning(f"Skipping unreadable file {f.filename}: {e}")
    corpus = DocumentService.build_corpus(texts, max_chars=CORPUS_MAX_CHARS)
    if not corpus.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No readable text could be extracted from the uploaded files.",
        )
    return corpus


@router.post("/api/courses/ai/outline-from-content")
async def outline_from_content(
    files: List[UploadFile] = File(...),
    modules: int = Form(...),
    videos_per_module: int = Form(...),
    slides_per_video: int = Form(...),
    tone: str = Form("formal"),
    difficulty: str = Form("intermediate"),
    current_user: User = Depends(require_creator),
):
    """Phase 1: extract corpus + return a validated, reviewable course outline (no persistence)."""
    _validate_upload_files(files)
    n_modules = _clamp(modules, 1, MAX_MODULES)
    vpm = _clamp(videos_per_module, 1, MAX_VIDEOS_PER_MODULE)
    spv = _clamp(slides_per_video, 1, MAX_SLIDES_PER_VIDEO)

    corpus = await _extract_corpus(files)
    try:
        outline = await claude_service.generate_course_outline(
            corpus=corpus, n_modules=n_modules, videos_per_module=vpm,
            slides_per_video=spv, tone=tone, difficulty=difficulty,
        )
    except Exception as e:
        logger.error(f"Outline generation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI could not generate an outline from this content. Try different files or settings.",
        )
    return outline


@router.post("/api/courses/from-outline", status_code=status.HTTP_201_CREATED)
async def create_from_outline(
    outline: str = Form(...),
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_creator),
):
    """Phase 2a: persist the (edited) outline as a Draft course + stored source text."""
    _validate_upload_files(files)

    try:
        parsed = CourseOutline.model_validate(json.loads(outline))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid outline: {e}",
        )

    # Fix 3: bound hand-edited outline dimensions
    if len(parsed.modules) > MAX_MODULES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Too many modules (max {MAX_MODULES}).")
    for m in parsed.modules:
        if len(m.videos) > MAX_VIDEOS_PER_MODULE:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail=f"Too many videos in a module (max {MAX_VIDEOS_PER_MODULE}).")
        for v in m.videos:
            if len(v.slides) > MAX_SLIDES_PER_VIDEO:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                    detail=f"Too many slides in a video (max {MAX_SLIDES_PER_VIDEO}).")

    course = Course(
        title=parsed.title or "Generated Course",
        description=parsed.description or "",
        creator_id=current_user.id,
        status=CourseStatus.DRAFT,
    )
    db.add(course)
    db.flush()  # assign course.id

    for f in files:
        data = await f.read()
        if len(data) > settings.MAX_UPLOAD_SIZE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File too large: {f.filename}. Max {settings.MAX_UPLOAD_SIZE // (1024 * 1024)}MB per file.",
            )
        try:
            text = document_service.extract_text(data, f.filename)
        except Exception as e:
            logger.warning(f"Skipping unreadable source file {f.filename}: {e}")
            text = ""
        db.add(CourseSourceDocument(
            course_id=course.id,
            filename=f.filename or "upload",
            content_type=f.content_type,
            char_count=len(text),
            extracted_text=text,
        ))

    video_map = []
    for mi, m in enumerate(parsed.modules):
        module = Module(course_id=course.id, order_index=mi, title=m.title,
                        description=m.description, status="draft")
        db.add(module)
        db.flush()
        for vi, v in enumerate(m.videos):
            video = Video(module_id=module.id, order_index=vi, title=v.title,
                          description=v.description, status="draft")
            db.add(video)
            db.flush()
            slide_ids = []
            for si, s in enumerate(v.slides):
                slide = Slide(video_id=video.id, order_index=si,
                              narration_script=s.brief or "", status="draft")
                db.add(slide)
                db.flush()
                slide_ids.append(slide.id)
            video_map.append({"video_id": video.id, "slide_ids": slide_ids})

    db.commit()
    db.refresh(course)
    return {"course_id": course.id, "videos": video_map}


def _get_video_or_404(video_id: int, db: Session, current_user: User) -> Video:
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video not found")
    module = db.query(Module).filter(Module.id == video.module_id).first()
    course = db.query(Course).filter(Course.id == module.course_id).first() if module else None
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")
    if current_user.role.value != "admin" and course.creator_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return video


def _course_corpus(course_id: int, db: Session) -> str:
    docs = db.query(CourseSourceDocument).filter(
        CourseSourceDocument.course_id == course_id).all()
    return DocumentService.build_corpus([d.extracted_text or "" for d in docs],
                                        max_chars=CORPUS_MAX_CHARS)


@router.post("/api/videos/{video_id}/ai/generate-content")
async def generate_video_content(
    video_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_creator),
):
    """Phase 2b: fill each slide of a video with blocks + narration, streaming per-slide progress."""
    video = _get_video_or_404(video_id, db, current_user)
    module = db.query(Module).filter(Module.id == video.module_id).first()
    course = db.query(Course).filter(Course.id == module.course_id).first()
    corpus = _course_corpus(course.id, db)
    slides = db.query(Slide).filter(Slide.video_id == video.id).order_by(Slide.order_index).all()
    slide_ids = [s.id for s in slides]
    # Fix 4: capture plain strings before the generator so db.commit() expiry can't cause silent reloads
    module_title = module.title
    video_title = video.title

    async def event_generator():
        for sid in slide_ids:
            if await request.is_disconnected():
                break
            slide = db.query(Slide).filter(Slide.id == sid).first()
            try:
                content = await claude_service.generate_slide_blocks(
                    corpus=corpus, module_title=module_title, video_title=video_title,
                    slide_title=slide.narration_script or "", brief=slide.narration_script or "",
                )
                for bi, b in enumerate(content["blocks"]):
                    db.add(Block(
                        slide_id=slide.id, order_index=bi, type=b["type"],
                        content=b.get("content") or {},
                        grid_position={"x": 0, "y": bi * 4, "w": 12, "h": 4},
                    ))
                if content.get("narration_script"):
                    slide.narration_script = content["narration_script"]
                slide.status = "draft"
                db.commit()
                yield {"data": "slide"}
            except Exception as e:
                db.rollback()
                logger.warning(f"Slide {sid} content generation failed: {e}")
                yield {"data": "error"}

    return EventSourceResponse(event_generator())
