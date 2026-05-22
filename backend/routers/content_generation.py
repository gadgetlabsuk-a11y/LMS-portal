"""AI generation of a full relational course from uploaded documents.

No router prefix — full /api/... paths are declared per route (mirrors routers/slides.py).
"""
import logging
from typing import List

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from database import get_db
from models import User
from middleware.auth_middleware import require_creator
from services.claude_service import ClaudeService
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
