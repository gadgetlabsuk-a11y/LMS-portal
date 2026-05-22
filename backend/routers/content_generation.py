"""AI generation of a full relational course from uploaded documents.

No router prefix — full /api/... paths are declared per route (mirrors routers/slides.py).
"""
import json
import logging
from typing import List

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from database import get_db
from models import User, Course, CourseStatus, Module, Video, Slide, CourseSourceDocument
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


async def _extract_corpus(files: List[UploadFile]) -> str:
    """Extract + merge text from uploaded files into a capped corpus. Skips unreadable files."""
    texts: list[str] = []
    for f in files:
        name = (f.filename or "").lower()
        if not name.endswith(ALLOWED_EXTS):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported file type: {f.filename}. Allowed: .pptx, .docx, .pdf",
            )
        data = await f.read()
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
    if len(files) > MAX_FILES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Too many files. Maximum {MAX_FILES}.",
        )
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
    try:
        parsed = CourseOutline.model_validate(json.loads(outline))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid outline: {e}",
        )

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
