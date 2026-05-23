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

from fastapi import APIRouter, Depends, HTTPException
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
)
from middleware.auth_middleware import get_current_active_user
from services.qa_service import QAService
from services.audit_service import AuditService
from services.claude_service import ClaudeService
from services.integrations import get_avatar_provider

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ilb", tags=["ilb"])

VALID_MODES = {"interrupt", "defer"}
_qa = QAService()
_audit = AuditService()
_claude = ClaudeService()


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
    is_owner = enrollment is not None and enrollment.user_id == user.id
    is_privileged = user.role in (UserRole.ADMIN, UserRole.CREATOR)
    if not (is_owner or is_privileged):
        raise HTTPException(status_code=403, detail="Not your session")
    return bs


# --------------------------------------------------------------------------- schemas

class StartSessionRequest(BaseModel):
    course_id: int
    mode: str = "interrupt"


class BroadcastSessionResponse(BaseModel):
    id: int
    enrollment_id: int
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
    """Start an ILB broadcast session for a course.

    Enrolment management isn't a full feature yet, so the ILB demo find-or-creates the
    learner's enrolment for the course on first broadcast (version-pinned to the course's
    current version).
    """
    if body.mode not in VALID_MODES:
        raise HTTPException(status_code=422, detail=f"mode must be one of {sorted(VALID_MODES)}")

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
            user_id=current_user.id,
            course_id=body.course_id,
            course_version=course.version or 1,
        )
        db.add(enrollment)
        db.commit()
        db.refresh(enrollment)

    bs = BroadcastSession(
        enrollment_id=enrollment.id,
        mode=body.mode,
        started_at=datetime.utcnow(),
        completion_status="in_progress",
    )
    db.add(bs)
    db.commit()
    db.refresh(bs)

    # Pick the course's configured avatar if a podcast video has one; else a demo default.
    avatar_id = "demo_avatar"
    first_video = (
        db.query(Video)
        .join(Module, Video.module_id == Module.id)
        .filter(Module.course_id == enrollment.course_id, Video.heygen_avatar_id.isnot(None))
        .first()
    )
    if first_video and first_video.heygen_avatar_id:
        avatar_id = first_video.heygen_avatar_id

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

    course_id = bs.enrollment.course_id
    source = _assemble_course_source(db, course_id)

    result = await _qa.answer(body.question, source)

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

    return AskResponse(**result.to_dict())


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
    enrollment = bs.enrollment
    learner = db.query(User).filter(User.id == enrollment.user_id).first()
    course = db.query(Course).filter(Course.id == enrollment.course_id).first()

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
        course={
            "id": getattr(course, "id", None),
            "title": getattr(course, "title", None),
            "version": enrollment.course_version,
        },
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
    segments: Optional[List[str]] = None
    published: bool = False


class PodcastConfigRequest(BaseModel):
    script: str
    host_persona: Optional[str] = None
    avatar_id: Optional[str] = None


class PublishRequest(BaseModel):
    published: bool = True


def _podcast_config(course: Course) -> PodcastConfig:
    return PodcastConfig(
        course_id=course.id,
        script=course.ilb_script,
        host_persona=course.ilb_host_persona,
        avatar_id=course.ilb_avatar_id,
        segments=course.ilb_segments,
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
    course.ilb_segments = _segments_from_script(body.script)
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
