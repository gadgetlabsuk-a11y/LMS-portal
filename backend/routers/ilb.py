"""ILB (Interactive Learning Broadcast) endpoints.

Exposes the broadcast-session lifecycle + grounded Q&A + regulator audit pack built in
services/qa_service.py and services/audit_service.py, for the ILB player frontend.
See docs/superpowers/specs/2026-05-21-ilb-design.md.

Note: avatar/STT/live-TTS are stubbed (services/integrations.py) until HeyGen/Deepgram/
ElevenLabs keys are configured.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
import logging

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models import (
    User,
    UserRole,
    Course,
    Enrollment,
    Module,
    Video,
    Slide,
    Block,
    BroadcastSession,
    Interaction,
    SessionAttestation,
    Broadcast,
)
from middleware.auth_middleware import get_current_active_user
from services.qa_service import QAService
from services.audit_service import AuditService
from services.claude_service import ClaudeService
from services.tts_service import TTSService
from services.document_service import DocumentService
from services.integrations import get_avatar_provider, get_stt_provider, DEFAULT_HEYGEN_AVATAR_ID
from config import settings
import httpx

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ilb", tags=["ilb"])

VALID_MODES = {"interrupt", "defer"}
_qa = QAService()
_audit = AuditService()
_claude = ClaudeService()
_tts = TTSService()


# --------------------------------------------------------------------------- helpers

def _assemble_course_source(db: Session, course_id: int) -> str:
    """Gather the course's text content to ground Q&A (long-context, no vector store)."""
    parts: List[str] = []
    course = db.query(Course).filter(Course.id == course_id).first()
    if course:
        parts.append(f"# {course.title}")
        if course.description:
            parts.append(course.description)
    modules = (
        db.query(Module).filter(Module.course_id == course_id).order_by(Module.order_index).all()
    )
    for m in modules:
        parts.append(f"## {m.title}")
        if m.description:
            parts.append(m.description)
        for v in sorted(m.videos, key=lambda x: x.order_index):
            parts.append(f"### {v.title}")
            for s in sorted(v.slides, key=lambda x: x.order_index):
                if s.narration_script:
                    parts.append(s.narration_script)
                for b in sorted(s.blocks, key=lambda x: x.order_index):
                    content = b.content or {}
                    text = content.get("text") or content.get("html") or content.get("body")
                    if text:
                        parts.append(str(text))
    return "\n\n".join(p for p in parts if p)


def _load_owned_session(db: Session, session_id: int, user: User) -> BroadcastSession:
    """Load a broadcast session, enforcing that it belongs to the current learner
    (admins and creators may also access it)."""
    bs = db.query(BroadcastSession).filter(BroadcastSession.id == session_id).first()
    if not bs:
        raise HTTPException(status_code=404, detail="Broadcast session not found")
    enrollment = bs.enrollment
    is_owner = (enrollment is not None and enrollment.user_id == user.id) or (bs.learner_id == user.id)
    is_privileged = user.role in (UserRole.ADMIN, UserRole.CREATOR)
    if not (is_owner or is_privileged):
        raise HTTPException(status_code=403, detail="Not your session")
    return bs


def _session_context(db: Session, bs: BroadcastSession) -> Dict[str, Any]:
    """Resolve grounding source / voice / content title / learner for either session type."""
    if bs.broadcast_id:
        b = db.query(Broadcast).filter(Broadcast.id == bs.broadcast_id).first()
        return {
            "source": (b.source_text or "") if b else "",
            "voice_id": b.voice_id if b else None,
            "title": b.title if b else "Broadcast",
            "version": None,
            "learner_id": bs.learner_id,
        }
    enrollment = bs.enrollment
    course = db.query(Course).filter(Course.id == enrollment.course_id).first() if enrollment else None
    return {
        "source": _assemble_course_source(db, enrollment.course_id) if enrollment else "",
        "voice_id": course.ilb_voice_id if course else None,
        "title": course.title if course else "Course",
        "version": enrollment.course_version if enrollment else None,
        "learner_id": enrollment.user_id if enrollment else None,
    }


async def _maybe_voice_answer(answer_text: str, voice_id: Optional[str], interaction_id: int) -> Optional[str]:
    """Render a Q&A answer to speech (ElevenLabs) using the given voice, if configured."""
    if not (answer_text and _tts.api_key):
        return None
    from pathlib import Path
    from config import settings

    try:
        audio = await _tts.synthesize(answer_text, voice_id or TTSService.DEFAULT_VOICE_ID)
        audio_dir = Path(settings.UPLOAD_DIR) / "audio"
        audio_dir.mkdir(parents=True, exist_ok=True)
        filename = f"ilb_answer_{interaction_id}.mp3"
        (audio_dir / filename).write_bytes(audio)
        return f"/api/media/audio/{filename}"
    except Exception:
        logger.warning("Answer TTS failed for interaction %s", interaction_id, exc_info=True)
        return None


# --------------------------------------------------------------------------- schemas

class StartSessionRequest(BaseModel):
    course_id: Optional[int] = None
    broadcast_id: Optional[int] = None
    mode: str = "interrupt"


class BroadcastSessionResponse(BaseModel):
    id: int
    enrollment_id: Optional[int] = None
    broadcast_id: Optional[int] = None
    mode: str
    completion_status: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    final_score: Optional[float] = None

    class Config:
        from_attributes = True


class StartSessionResponse(BaseModel):
    session: BroadcastSessionResponse
    live: Dict[str, Any]  # stub live-avatar transport (HeyGen/LiveKit when keys configured)


class AskRequest(BaseModel):
    question: str
    input_mode: str = "text"  # text | voice


class AskResponse(BaseModel):
    answer: str
    source_refs: List[str]
    confidence: float
    covered: bool
    escalated: bool
    disclaimer: str
    answer_audio_url: Optional[str] = None


class CompleteRequest(BaseModel):
    final_score: Optional[float] = None


class CompleteResponse(BaseModel):
    session: BroadcastSessionResponse
    attestation: Dict[str, Any]


# --------------------------------------------------------------------------- routes

@router.post("/sessions", response_model=StartSessionResponse, status_code=201)
def start_session(
    body: StartSessionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> StartSessionResponse:
    """Start an ILB session backed by EITHER a course (course_id) or a standalone broadcast.

    For courses, enrolment management isn't a full feature yet, so the demo find-or-creates the
    learner's enrolment. For standalone broadcasts, the session links directly to the broadcast.
    """
    if body.mode not in VALID_MODES:
        raise HTTPException(status_code=422, detail=f"mode must be one of {sorted(VALID_MODES)}")
    if bool(body.course_id) == bool(body.broadcast_id):
        raise HTTPException(status_code=422, detail="Provide exactly one of course_id or broadcast_id")

    avatar_id = "demo_avatar"

    if body.broadcast_id is not None:
        broadcast = db.query(Broadcast).filter(Broadcast.id == body.broadcast_id).first()
        if not broadcast:
            raise HTTPException(status_code=404, detail="Broadcast not found")
        privileged = current_user.role in (UserRole.CREATOR, UserRole.ADMIN)
        if not privileged and not broadcast.published:
            raise HTTPException(status_code=404, detail="Broadcast not published")
        bs = BroadcastSession(
            broadcast_id=broadcast.id,
            learner_id=current_user.id,
            mode=body.mode,
            started_at=datetime.utcnow(),
            completion_status="in_progress",
        )
        if broadcast.avatar_id:
            avatar_id = broadcast.avatar_id
    else:
        course = db.query(Course).filter(Course.id == body.course_id).first()
        if not course:
            raise HTTPException(status_code=404, detail="Course not found")
        enrollment = (
            db.query(Enrollment)
            .filter(Enrollment.user_id == current_user.id, Enrollment.course_id == body.course_id)
            .first()
        )
        if not enrollment:
            enrollment = Enrollment(
                user_id=current_user.id, course_id=body.course_id, course_version=course.version or 1,
            )
            db.add(enrollment)
            db.commit()
            db.refresh(enrollment)
        bs = BroadcastSession(
            enrollment_id=enrollment.id, mode=body.mode,
            started_at=datetime.utcnow(), completion_status="in_progress",
        )
        first_video = (
            db.query(Video)
            .join(Module, Video.module_id == Module.id)
            .filter(Module.course_id == body.course_id, Video.heygen_avatar_id.isnot(None))
            .first()
        )
        if first_video and first_video.heygen_avatar_id:
            avatar_id = first_video.heygen_avatar_id

    db.add(bs)
    db.commit()
    db.refresh(bs)
    live = get_avatar_provider().create_live_session(avatar_id)
    logger.info("ILB session started: id=%s user=%s mode=%s", bs.id, current_user.id, bs.mode)
    return StartSessionResponse(session=BroadcastSessionResponse.model_validate(bs), live=live)


@router.get("/sessions/{session_id}", response_model=BroadcastSessionResponse)
def get_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> BroadcastSessionResponse:
    bs = _load_owned_session(db, session_id, current_user)
    return BroadcastSessionResponse.model_validate(bs)


@router.post("/sessions/{session_id}/ask", response_model=AskResponse)
async def ask(
    session_id: int,
    body: AskRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> AskResponse:
    """Answer a learner question grounded in the course source, with guardrails.

    The answer is a learning aid — comprehension is assessed by the knowledge-check quiz,
    not by this Q&A. Every exchange is logged as an Interaction for audit.
    """
    bs = _load_owned_session(db, session_id, current_user)
    if not body.question.strip():
        raise HTTPException(status_code=422, detail="question must not be empty")

    ctx = _session_context(db, bs)

    result = await _qa.answer(body.question, ctx["source"])

    interaction = Interaction(
        broadcast_session_id=bs.id,
        ts=datetime.utcnow(),
        type="answer",
        input_mode=body.input_mode,
        question_text=body.question,
        answer_text=result.answer,
        source_refs=result.source_refs,
        confidence=result.confidence,
        escalated=result.escalated,
    )
    db.add(interaction)
    db.commit()
    db.refresh(interaction)

    answer_audio_url = await _maybe_voice_answer(result.answer, ctx["voice_id"], interaction.id)
    return AskResponse(**result.to_dict(), answer_audio_url=answer_audio_url)


@router.post("/sessions/{session_id}/complete", response_model=CompleteResponse)
def complete_session(
    session_id: int,
    body: CompleteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> CompleteResponse:
    """Mark a session complete and seal it into the learner's audit hash chain."""
    bs = _load_owned_session(db, session_id, current_user)
    bs.completion_status = "completed"
    bs.completed_at = datetime.utcnow()
    if body.final_score is not None:
        bs.final_score = body.final_score

    # Unify completion for course-attached broadcasts: a finished enrolment-backed session
    # also completes the enrolment (same signal regular courses use — see courses.py
    # update_progress, which sets completed when progress >= 100). Standalone broadcast
    # sessions have no enrolment, so this is skipped; their completion is the session itself.
    enrollment = bs.enrollment
    if enrollment is not None and not enrollment.completed:
        enrollment.completed = True
        enrollment.completed_at = bs.completed_at
        enrollment.progress = 100.0

    db.commit()
    db.refresh(bs)

    attestation = _audit.attest(db, bs)
    logger.info("ILB session completed: id=%s seq=%s", bs.id, attestation.sequence)

    return CompleteResponse(
        session=BroadcastSessionResponse.model_validate(bs),
        attestation={
            "sequence": attestation.sequence,
            "content_hash": attestation.content_hash,
            "prev_hash": attestation.prev_hash,
            "timestamp_token": attestation.timestamp_token,
            "anchor_ref": attestation.anchor_ref,
        },
    )


@router.get("/sessions/{session_id}/audit-pack")
def audit_pack(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """Generate the regulator audit pack (machine JSON + human HTML) for a session."""
    bs = _load_owned_session(db, session_id, current_user)
    ctx = _session_context(db, bs)
    learner = db.query(User).filter(User.id == ctx["learner_id"]).first() if ctx["learner_id"] else None

    interactions = [
        {
            "ts": i.ts,
            "type": i.type,
            "input_mode": i.input_mode,
            "question_text": i.question_text,
            "answer_text": i.answer_text,
            "source_refs": i.source_refs,
            "confidence": i.confidence,
            "escalated": i.escalated,
        }
        for i in bs.interactions
    ]

    record = _audit.build_session_record(
        session=bs,
        learner={"id": getattr(learner, "id", None), "username": getattr(learner, "username", None)},
        course={"id": None, "title": ctx["title"], "version": ctx["version"]},
        interactions=interactions,
    )

    attestation = (
        db.query(SessionAttestation)
        .filter(SessionAttestation.broadcast_session_id == bs.id)
        .order_by(SessionAttestation.sequence.desc())
        .first()
    )
    pack = _audit.generate_pack(record, attestation) if attestation else {"json": None, "html": None}

    return {
        "record": record,
        "attestation": {
            "sequence": getattr(attestation, "sequence", None),
            "content_hash": getattr(attestation, "content_hash", None),
            "prev_hash": getattr(attestation, "prev_hash", None),
            "timestamp_token": getattr(attestation, "timestamp_token", None),
            "anchor_ref": getattr(attestation, "anchor_ref", None),
        } if attestation else None,
        "html": pack["html"],
    }


# --------------------------------------------------------------------------- authoring

class PodcastScriptRequest(BaseModel):
    host_persona: str = "a warm, clear, professional training host"
    target_minutes: int = 10


class PodcastScriptResponse(BaseModel):
    script: str
    segments: List[str]


@router.post("/courses/{course_id}/podcast-script", response_model=PodcastScriptResponse)
async def make_podcast_script(
    course_id: int,
    body: PodcastScriptRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> PodcastScriptResponse:
    """Generate a host-persona podcast narration script grounded in the course content.

    Creator/admin authoring step. Faithful to the source — no invented facts (qa-style grounding).
    """
    if current_user.role not in (UserRole.CREATOR, UserRole.ADMIN):
        raise HTTPException(status_code=403, detail="Creator or admin only")

    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    source = _assemble_course_source(db, course_id)
    if not source.strip():
        raise HTTPException(status_code=422, detail="Course has no content to base a script on")

    result = await _claude.generate_podcast_script(
        source_text=source,
        host_persona=body.host_persona,
        target_minutes=body.target_minutes,
        title=course.title,
    )
    return PodcastScriptResponse(script=result["script"], segments=result["segments"])


# --------------------------------------------------------------------------- persist / publish

def _segments_from_script(script: str) -> List[str]:
    return [s.strip() for s in (script or "").split("[SEGMENT BREAK]") if s.strip()]


class PodcastConfig(BaseModel):
    course_id: int
    script: Optional[str] = None
    host_persona: Optional[str] = None
    avatar_id: Optional[str] = None
    voice_id: Optional[str] = None
    segments: Optional[List[str]] = None
    segment_audio: Optional[List[str]] = None
    published: bool = False


class PodcastConfigRequest(BaseModel):
    script: str
    host_persona: Optional[str] = None
    avatar_id: Optional[str] = None
    voice_id: Optional[str] = None


class PublishRequest(BaseModel):
    published: bool = True


def _podcast_config(course: Course) -> PodcastConfig:
    return PodcastConfig(
        course_id=course.id,
        script=course.ilb_script,
        host_persona=course.ilb_host_persona,
        avatar_id=course.ilb_avatar_id,
        voice_id=course.ilb_voice_id,
        segments=course.ilb_segments,
        segment_audio=course.ilb_segment_audio,
        published=bool(course.ilb_published),
    )


@router.get("/courses/{course_id}/podcast", response_model=PodcastConfig)
def get_podcast_config(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> PodcastConfig:
    """Get a course's broadcast config. Learners only see it once published."""
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    privileged = current_user.role in (UserRole.CREATOR, UserRole.ADMIN)
    if not privileged and not course.ilb_published:
        raise HTTPException(status_code=404, detail="No published broadcast for this course")
    return _podcast_config(course)


@router.put("/courses/{course_id}/podcast", response_model=PodcastConfig)
def save_podcast_config(
    course_id: int,
    body: PodcastConfigRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> PodcastConfig:
    """Persist the broadcast script + avatar config onto the course (creator/admin)."""
    if current_user.role not in (UserRole.CREATOR, UserRole.ADMIN):
        raise HTTPException(status_code=403, detail="Creator or admin only")
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    course.ilb_script = body.script
    course.ilb_host_persona = body.host_persona
    course.ilb_avatar_id = body.avatar_id
    course.ilb_voice_id = body.voice_id
    course.ilb_segments = _segments_from_script(body.script)
    course.ilb_segment_audio = None  # script/voice changed — invalidate stale rendered audio
    db.commit()
    db.refresh(course)
    logger.info("ILB podcast saved: course=%s by user=%s", course_id, current_user.id)
    return _podcast_config(course)


@router.post("/courses/{course_id}/podcast/publish", response_model=PodcastConfig)
def publish_podcast(
    course_id: int,
    body: PublishRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> PodcastConfig:
    """Publish (or unpublish) a course's broadcast (creator/admin)."""
    if current_user.role not in (UserRole.CREATOR, UserRole.ADMIN):
        raise HTTPException(status_code=403, detail="Creator or admin only")
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    if body.published and not (course.ilb_script and course.ilb_script.strip()):
        raise HTTPException(status_code=422, detail="Nothing to publish — save a script first")
    course.ilb_published = body.published
    db.commit()
    db.refresh(course)
    logger.info("ILB podcast %s: course=%s", "published" if body.published else "unpublished", course_id)
    return _podcast_config(course)


# --------------------------------------------------------------------------- voice / audio

class Voice(BaseModel):
    voice_id: str
    name: str
    description: str = ""


@router.get("/voices", response_model=List[Voice])
async def list_voices(current_user: User = Depends(get_current_active_user)) -> List[Voice]:
    """ElevenLabs voice catalogue for the authoring voice picker (curated fallback if no key)."""
    voices = await _tts.list_voices()
    return [Voice(voice_id=v["voice_id"], name=v.get("name", ""), description=v.get("description", "")) for v in voices]


@router.post("/courses/{course_id}/podcast/render-audio")
async def render_podcast_audio(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """Render each saved script segment to narration audio (ElevenLabs) and store the URLs."""
    from pathlib import Path
    from config import settings

    if current_user.role not in (UserRole.CREATOR, UserRole.ADMIN):
        raise HTTPException(status_code=403, detail="Creator or admin only")
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    segments = course.ilb_segments or []
    if not segments:
        raise HTTPException(status_code=422, detail="Save a script first")
    if not _tts.api_key:
        raise HTTPException(status_code=503, detail="TTS not configured (ELEVENLABS_API_KEY)")

    voice_id = course.ilb_voice_id or TTSService.DEFAULT_VOICE_ID
    audio_dir = Path(settings.UPLOAD_DIR) / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)

    urls: List[str] = []
    for i, segment in enumerate(segments):
        audio = await _tts.synthesize(segment, voice_id)
        filename = f"ilb_course_{course_id}_seg_{i}.mp3"
        (audio_dir / filename).write_bytes(audio)
        urls.append(f"/api/media/audio/{filename}")

    course.ilb_segment_audio = urls
    db.commit()
    db.refresh(course)
    logger.info("ILB audio rendered: course=%s segments=%s", course_id, len(urls))
    return {"segment_audio": urls}


@router.post("/stt")
async def transcribe_audio(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """Transcribe a recorded question (push-to-talk) to text via Deepgram."""
    from config import settings
    if not settings.DEEPGRAM_API_KEY:
        raise HTTPException(status_code=503, detail="Speech-to-text not configured (DEEPGRAM_API_KEY)")
    audio = await file.read()
    if not audio:
        raise HTTPException(status_code=422, detail="Empty audio")
    transcript = await get_stt_provider().transcribe(audio, file.content_type or "audio/webm")
    return {"transcript": transcript}


# --------------------------------------------------------------------------- standalone broadcasts

class BroadcastCreate(BaseModel):
    title: str
    description: Optional[str] = None
    source_text: Optional[str] = None


class BroadcastUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    source_text: Optional[str] = None
    host_persona: Optional[str] = None
    voice_id: Optional[str] = None
    avatar_id: Optional[str] = None
    script: Optional[str] = None


class BroadcastOut(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    source_text: Optional[str] = None
    host_persona: Optional[str] = None
    avatar_id: Optional[str] = None
    voice_id: Optional[str] = None
    script: Optional[str] = None
    segments: Optional[List[str]] = None
    segment_audio: Optional[List[str]] = None
    segment_video: Optional[List[Optional[str]]] = None  # per-segment MP4 URL or None (un-rendered)
    published: bool = False

    class Config:
        from_attributes = True


class BroadcastSummary(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    published: bool = False


def _require_creator(user: User) -> None:
    if user.role not in (UserRole.CREATOR, UserRole.ADMIN):
        raise HTTPException(status_code=403, detail="Creator or admin only")


def _get_broadcast(db: Session, broadcast_id: int) -> Broadcast:
    b = db.query(Broadcast).filter(Broadcast.id == broadcast_id).first()
    if not b:
        raise HTTPException(status_code=404, detail="Broadcast not found")
    return b


async def _download_bytes(url: str) -> bytes:
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, timeout=120.0)
    resp.raise_for_status()
    return resp.content


@router.post("/broadcasts", response_model=BroadcastOut, status_code=201)
def create_broadcast(
    body: BroadcastCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> BroadcastOut:
    """Create a standalone broadcast (team brief, company news, etc.)."""
    _require_creator(current_user)
    b = Broadcast(
        title=body.title, description=body.description,
        source_text=body.source_text, creator_id=current_user.id,
    )
    db.add(b)
    db.commit()
    db.refresh(b)
    return BroadcastOut.model_validate(b)


@router.get("/broadcasts", response_model=List[BroadcastSummary])
def list_broadcasts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> List[BroadcastSummary]:
    """List broadcasts — learners see only published ones."""
    q = db.query(Broadcast)
    if current_user.role not in (UserRole.CREATOR, UserRole.ADMIN):
        q = q.filter(Broadcast.published.is_(True))
    items = q.order_by(Broadcast.created_at.desc()).all()
    return [BroadcastSummary(id=b.id, title=b.title, description=b.description, published=bool(b.published)) for b in items]


@router.get("/broadcasts/{broadcast_id}", response_model=BroadcastOut)
def get_broadcast(
    broadcast_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> BroadcastOut:
    b = _get_broadcast(db, broadcast_id)
    if current_user.role not in (UserRole.CREATOR, UserRole.ADMIN) and not b.published:
        raise HTTPException(status_code=404, detail="Broadcast not published")
    return BroadcastOut.model_validate(b)


@router.put("/broadcasts/{broadcast_id}", response_model=BroadcastOut)
def update_broadcast(
    broadcast_id: int,
    body: BroadcastUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> BroadcastOut:
    _require_creator(current_user)
    b = _get_broadcast(db, broadcast_id)
    data = body.model_dump(exclude_unset=True)
    for field in ("title", "description", "source_text", "host_persona", "voice_id", "avatar_id"):
        if field in data:
            setattr(b, field, data[field])
    if "script" in data:
        b.script = data["script"]
        b.segments = _segments_from_script(data["script"] or "")
        b.segment_audio = None  # invalidate stale audio
    db.commit()
    db.refresh(b)
    return BroadcastOut.model_validate(b)


@router.post("/broadcasts/{broadcast_id}/source-upload", response_model=BroadcastOut)
async def broadcast_source_upload(
    broadcast_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> BroadcastOut:
    """Set a broadcast's source by extracting text from an uploaded PDF/DOCX/PPTX."""
    _require_creator(current_user)
    b = _get_broadcast(db, broadcast_id)
    raw = await file.read()
    try:
        text = DocumentService.extract_text_from_file_sync(raw, file.content_type or "")
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Could not extract text: {e}")
    if not text.strip():
        raise HTTPException(status_code=422, detail="No text extracted from the document")
    b.source_text = text
    db.commit()
    db.refresh(b)
    return BroadcastOut.model_validate(b)


@router.post("/broadcasts/{broadcast_id}/generate-script", response_model=PodcastScriptResponse)
async def broadcast_generate_script(
    broadcast_id: int,
    body: PodcastScriptRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> PodcastScriptResponse:
    """Generate a host-persona script from the broadcast's source (paste / doc / topic)."""
    _require_creator(current_user)
    b = _get_broadcast(db, broadcast_id)
    if not (b.source_text and b.source_text.strip()):
        raise HTTPException(status_code=422, detail="Add source content first (paste, upload, or a topic)")
    result = await _claude.generate_podcast_script(
        source_text=b.source_text, host_persona=body.host_persona,
        target_minutes=body.target_minutes, title=b.title,
    )
    b.script = result["script"]
    b.segments = result["segments"]
    b.segment_audio = None
    db.commit()
    db.refresh(b)
    return PodcastScriptResponse(script=result["script"], segments=result["segments"])


@router.post("/broadcasts/{broadcast_id}/render-audio")
async def broadcast_render_audio(
    broadcast_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """Render the broadcast's script segments to narration audio (ElevenLabs)."""
    _require_creator(current_user)
    b = _get_broadcast(db, broadcast_id)
    segments = b.segments or []
    if not segments:
        raise HTTPException(status_code=422, detail="Generate a script first")
    if not _tts.api_key:
        raise HTTPException(status_code=503, detail="TTS not configured (ELEVENLABS_API_KEY)")
    from pathlib import Path
    from config import settings

    voice_id = b.voice_id or TTSService.DEFAULT_VOICE_ID
    audio_dir = Path(settings.UPLOAD_DIR) / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)
    urls: List[str] = []
    for i, segment in enumerate(segments):
        audio = await _tts.synthesize(segment, voice_id)
        filename = f"ilb_bcast_{broadcast_id}_seg_{i}.mp3"
        (audio_dir / filename).write_bytes(audio)
        urls.append(f"/api/media/audio/{filename}")
    b.segment_audio = urls
    db.commit()
    db.refresh(b)
    return {"segment_audio": urls}


@router.post("/broadcasts/{broadcast_id}/publish", response_model=BroadcastOut)
def publish_broadcast(
    broadcast_id: int,
    body: PublishRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> BroadcastOut:
    _require_creator(current_user)
    b = _get_broadcast(db, broadcast_id)
    if body.published and not (b.script and b.script.strip()):
        raise HTTPException(status_code=422, detail="Nothing to publish — generate a script first")
    b.published = body.published
    db.commit()
    db.refresh(b)
    return BroadcastOut.model_validate(b)


@router.post("/broadcasts/{broadcast_id}/render-avatar")
async def render_broadcast_avatar(
    broadcast_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """Submit one HeyGen avatar-video job per segment (lip-synced to its narration audio)."""
    _require_creator(current_user)
    b = _get_broadcast(db, broadcast_id)
    if not settings.HEYGEN_API_KEY:
        raise HTTPException(status_code=503, detail="Avatar video not configured (HEYGEN_API_KEY)")
    segs = b.segments or []
    audio = b.segment_audio or []
    if not segs or not audio:
        raise HTTPException(status_code=422, detail="Render the narration audio first")

    from pathlib import Path
    avatar_id = b.avatar_id or DEFAULT_HEYGEN_AVATAR_ID
    provider = get_avatar_provider()
    jobs: List[Dict[str, Any]] = []
    seg_video: List[Optional[str]] = list(b.segment_video or [])
    while len(seg_video) < len(segs):
        seg_video.append(None)
    for i, _seg in enumerate(segs):
        url = audio[i] if i < len(audio) else None
        if not url:
            jobs.append({"seg_index": i, "heygen_video_id": None, "status": "failed"})
            continue
        fname = url.rsplit("/", 1)[-1]
        path = Path(settings.UPLOAD_DIR) / "audio" / fname
        if not path.exists():
            jobs.append({"seg_index": i, "heygen_video_id": None, "status": "failed"})
            continue
        try:
            vid = await provider.submit_segment(path.read_bytes(), "audio/mpeg", avatar_id)
            jobs.append({"seg_index": i, "heygen_video_id": vid, "status": "processing"})
        except Exception as e:
            logger.error(f"HeyGen submit failed seg {i}: {e}")
            jobs.append({"seg_index": i, "heygen_video_id": None, "status": "failed"})

    b.video_render_jobs = jobs
    b.segment_video = seg_video
    db.commit()
    return {"jobs": jobs}


@router.get("/broadcasts/{broadcast_id}/avatar-status")
async def broadcast_avatar_status(
    broadcast_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """Poll HeyGen for each processing job; download completed MP4s and store the URL."""
    _require_creator(current_user)
    b = _get_broadcast(db, broadcast_id)
    jobs = list(b.video_render_jobs or [])
    seg_video = list(b.segment_video or [None] * len(b.segments or []))
    provider = get_avatar_provider()

    from pathlib import Path
    video_dir = Path(settings.UPLOAD_DIR) / "video"
    video_dir.mkdir(parents=True, exist_ok=True)

    changed = False
    for job in jobs:
        if job.get("status") != "processing":
            continue
        vid = job.get("heygen_video_id")
        i = job["seg_index"]
        try:
            status, url = await provider.poll(vid)
        except Exception as e:
            logger.error(f"HeyGen poll failed seg {i}: {e}")
            continue
        if status == "completed" and url:
            try:
                data = await _download_bytes(url)
                fname = f"ilb_bcast_{broadcast_id}_seg_{i}.mp4"
                (video_dir / fname).write_bytes(data)
                while len(seg_video) <= i:
                    seg_video.append(None)
                seg_video[i] = f"/api/media/video/{fname}"
                job["status"] = "completed"
                changed = True
            except Exception as e:
                logger.error(f"Avatar MP4 download failed seg {i}: {e}")
                job["status"] = "failed"
                changed = True
        elif status == "failed":
            job["status"] = "failed"
            changed = True

    if changed:
        b.video_render_jobs = jobs
        b.segment_video = seg_video
        db.commit()

    statuses = [j.get("status") for j in jobs]
    overall = "complete" if all(s in ("completed", "failed") for s in statuses) else "processing"
    return {"overall": overall, "segments": jobs, "segment_video": seg_video}
