"""
TTS narration audio generation endpoints.
- POST /api/slides/{slide_id}/tts/generate    — per-slide (TTS-01, TTS-05)
- POST /api/videos/{video_id}/tts/bulk-generate — bulk (TTS-02, TTS-03, TTS-04)
"""
import asyncio
import hashlib
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models import Slide, Video, Module, Course
from middleware.auth_middleware import require_creator
from services.tts_service import TTSService, _bulk_semaphore

logger = logging.getLogger(__name__)

router = APIRouter(tags=["tts"])

# Module-level singleton — enables patching in tests
tts_service = TTSService()


class TTSGenerateRequest(BaseModel):
    voice_id: Optional[str] = None


def _get_slide_or_404(slide_id: int, db: Session, current_user):
    """Copy of slides.py helper — avoids cross-router import coupling."""
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
    course = slide.video.module.course
    if current_user.role.value != "admin" and course.creator_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return slide


def _get_video_or_404(video_id: int, db: Session, current_user):
    video = db.query(Video).join(Module).join(Course).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video not found")
    if current_user.role.value != "admin" and video.module.course.creator_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return video


@router.post("/api/slides/{slide_id}/tts/generate")
async def generate_slide_audio(
    slide_id: int,
    body: TTSGenerateRequest,
    db: Session = Depends(get_db),
    current_user=Depends(require_creator),
):
    """Generate ElevenLabs narration audio for a single slide."""
    if not tts_service.api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="TTS not configured — set ELEVENLABS_API_KEY",
        )

    slide = _get_slide_or_404(slide_id, db, current_user)

    if not slide.narration_script:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Slide has no narration script")

    voice_id = (
        body.voice_id
        or (slide.video.narration_voice_id if slide.video else None)
        or TTSService.DEFAULT_VOICE_ID
    )

    try:
        audio_url = await tts_service.generate_for_slide(slide, voice_id, db)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="TTS not configured — set ELEVENLABS_API_KEY",
        )

    return {"audio_url": audio_url, "slide_id": slide_id}


@router.post("/api/videos/{video_id}/tts/bulk-generate")
async def bulk_generate_audio(
    video_id: int,
    body: TTSGenerateRequest,
    db: Session = Depends(get_db),
    current_user=Depends(require_creator),
):
    """Bulk generate ElevenLabs narration for all slides in a video."""
    if not tts_service.api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="TTS not configured — set ELEVENLABS_API_KEY",
        )

    video = _get_video_or_404(video_id, db, current_user)
    slides = (
        db.query(Slide)
        .filter(Slide.video_id == video_id)
        .order_by(Slide.order_index)
        .all()
    )

    voice_id = body.voice_id or video.narration_voice_id or TTSService.DEFAULT_VOICE_ID
    results = {"generated": 0, "skipped_no_script": 0, "skipped_cached": 0, "errors": 0}

    async def process_slide(slide):
        if not slide.narration_script:
            results["skipped_no_script"] += 1
            return
        new_hash = hashlib.sha256(slide.narration_script.encode()).hexdigest()
        if slide.narration_script_hash == new_hash and slide.narration_audio_url:
            results["skipped_cached"] += 1
            return
        async with _bulk_semaphore:
            try:
                await tts_service.generate_for_slide(slide, voice_id, db)
                results["generated"] += 1
            except Exception as e:
                logger.error(f"Bulk TTS failed for slide {slide.id}: {e}")
                results["errors"] += 1

    await asyncio.gather(*[process_slide(s) for s in slides])
    return results
