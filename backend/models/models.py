"""
SQLAlchemy models for LMS Course Builder.
Defines all database tables and relationships.
"""

from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    Boolean,
    Float,
    Enum,
    JSON,
    ForeignKey,
    UniqueConstraint,
    Index,
)
from sqlalchemy.orm import relationship, declarative_base
from datetime import datetime
import enum

Base = declarative_base()


class UserRole(str, enum.Enum):
    """User role enumeration."""

    ADMIN = "admin"
    CREATOR = "creator"
    TRAINEE = "trainee"


class CourseStatus(str, enum.Enum):
    """Course status enumeration."""

    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"
    HAS_UNPUBLISHED_CHANGES = "has_unpublished_changes"


class User(Base):
    """User model for authentication and authorization."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(255), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), default=UserRole.TRAINEE, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    mfa_enabled = Column(Boolean, default=False, nullable=False)
    mfa_secret = Column(String(255), nullable=True)
    failed_login_attempts = Column(Integer, default=0, nullable=False)
    locked_until = Column(DateTime, nullable=True)
    last_login = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    sessions = relationship("Session", back_populates="user", cascade="all, delete-orphan")
    courses_created = relationship("Course", back_populates="creator")
    enrollments = relationship("Enrollment", back_populates="user")
    audit_logs = relationship("AuditLog", back_populates="user")
    login_attempts = relationship("LoginAttempt", back_populates="user")

    __table_args__ = (Index("idx_username_active", "username", "is_active"),)


class Session(Base):
    """User session tracking."""

    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token = Column(String(500), unique=True, nullable=False)
    ip_address = Column(String(45), nullable=False)
    user_agent = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    # Relationships
    user = relationship("User", back_populates="sessions")

    __table_args__ = (Index("idx_user_active", "user_id", "is_active"),)


class Course(Base):
    """Course model for course management."""

    __tablename__ = "courses"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    creator_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(Enum(CourseStatus), default=CourseStatus.DRAFT, nullable=False)
    slug = Column(String(200), nullable=True, unique=True, index=True)
    summary = Column(Text, nullable=True)
    thumbnail_url = Column(String(500), nullable=True)
    audience_level = Column(String(50), nullable=True)
    learning_objectives = Column(JSON, nullable=True)
    category = Column(String(100), nullable=True)
    tags = Column(JSON, nullable=True)
    estimated_duration_minutes = Column(Integer, nullable=True)
    ai_tone_preset = Column(String(50), nullable=True)
    ai_custom_prompt = Column(Text, nullable=True)
    navigation_mode = Column(String(20), nullable=True, server_default='sequential')
    default_pass_rate = Column(Integer, nullable=True, server_default='80')
    default_quiz_attempts = Column(Integer, nullable=True, server_default='3')
    default_quiz_time_limit_seconds = Column(Integer, nullable=True)
    certificate_enabled = Column(Boolean, nullable=True, server_default='1')
    published_at = Column(DateTime, nullable=True)
    version = Column(Integer, nullable=True, server_default='1')
    # ILB (Interactive Learning Broadcast) config — one broadcast per course (demo).
    ilb_script = Column(Text, nullable=True)
    ilb_host_persona = Column(String(255), nullable=True)
    ilb_avatar_id = Column(String(100), nullable=True)
    ilb_voice_id = Column(String(100), nullable=True)
    ilb_segments = Column(JSON, nullable=True)
    ilb_segment_audio = Column(JSON, nullable=True)  # rendered narration audio URLs, per segment
    ilb_published = Column(Boolean, nullable=False, server_default='0')
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    creator = relationship("User", back_populates="courses_created")
    enrollments = relationship("Enrollment", back_populates="course", cascade="all, delete-orphan")
    modules = relationship("Module", back_populates="course", cascade="all, delete-orphan", order_by="Module.order_index")

    __table_args__ = (Index("idx_creator_status", "creator_id", "status"),)


class Enrollment(Base):
    """Enrollment model tracking user course progress."""

    __tablename__ = "enrollments"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    progress = Column(Float, default=0.0, nullable=False)
    completed = Column(Boolean, default=False, nullable=False)
    enrolled_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    course_version = Column(Integer, nullable=True, default=1)

    # Relationships
    user = relationship("User", back_populates="enrollments")
    course = relationship("Course", back_populates="enrollments")
    broadcast_sessions = relationship("BroadcastSession", back_populates="enrollment", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("user_id", "course_id", name="uq_user_course"),
        Index("idx_user_course", "user_id", "course_id"),
    )


class AuditLog(Base):
    """Audit logging for compliance and security."""

    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    action = Column(String(255), nullable=False)
    resource_type = Column(String(100), nullable=False)
    resource_id = Column(Integer, nullable=True)
    details = Column(JSON, nullable=True)
    ip_address = Column(String(45), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    user = relationship("User", back_populates="audit_logs")

    __table_args__ = (Index("idx_user_timestamp", "user_id", "timestamp"),)


class ErrorLog(Base):
    """Error logging for debugging and monitoring."""

    __tablename__ = "error_logs"

    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(String(100), unique=True, nullable=False)
    error_type = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    stack_trace = Column(Text, nullable=True)
    endpoint = Column(String(255), nullable=True)
    method = Column(String(10), nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    __table_args__ = (Index("idx_error_timestamp", "timestamp"),)


class ApiUsage(Base):
    """Track Claude API usage for cost management."""

    __tablename__ = "api_usage"

    id = Column(Integer, primary_key=True, index=True)
    endpoint = Column(String(255), nullable=False)
    tokens_used = Column(Integer, nullable=False)
    cost_estimate = Column(Float, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    __table_args__ = (Index("idx_usage_timestamp", "timestamp"),)


class FeatureFlag(Base):
    """Feature flags for gradual rollout and A/B testing."""

    __tablename__ = "feature_flags"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, nullable=False, index=True)
    enabled = Column(Boolean, default=False, nullable=False)
    description = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)


class WhiteLabelConfig(Base):
    """White label configuration for theming."""

    __tablename__ = "whitelabel_config"

    id = Column(Integer, primary_key=True, index=True)
    brand_name = Column(String(255), nullable=False, default="LMS Course Builder")
    logo_path = Column(String(500), nullable=True)
    favicon_path = Column(String(500), nullable=True)
    primary_color = Column(String(7), nullable=False, default="#1F2937")
    secondary_color = Column(String(7), nullable=False, default="#6366F1")
    accent_color = Column(String(7), nullable=False, default="#F59E0B")
    bg_color = Column(String(7), nullable=False, default="#FFFFFF")
    text_color = Column(String(7), nullable=False, default="#1F2937")
    font_family = Column(String(255), nullable=False, default="Inter, system-ui, sans-serif")
    heading_font = Column(String(255), nullable=False, default="Poppins, system-ui, sans-serif")
    border_radius = Column(String(50), nullable=False, default="0.5rem")
    button_style = Column(String(50), nullable=False, default="rounded")
    custom_css = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class LoginAttempt(Base):
    """Track login attempts for security monitoring."""

    __tablename__ = "login_attempts"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(255), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    ip_address = Column(String(45), nullable=False)
    success = Column(Boolean, default=False, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    user = relationship("User", back_populates="login_attempts")

    __table_args__ = (Index("idx_username_timestamp", "username", "timestamp"),)


class IpAllowlist(Base):
    """IP allowlist for additional security."""

    __tablename__ = "ip_allowlist"

    id = Column(Integer, primary_key=True, index=True)
    ip_address = Column(String(45), unique=True, nullable=False)
    description = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (Index("idx_ip_address", "ip_address"),)


class Module(Base):
    """Course module — top-level content grouping."""
    __tablename__ = "modules"

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    order_index = Column(Integer, nullable=False, server_default="0")
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    learning_objectives = Column(JSON, nullable=True)
    estimated_duration_minutes = Column(Integer, nullable=True)
    pass_rate_override = Column(Integer, nullable=True)
    unlock_rule = Column(String(50), nullable=True, server_default="after_previous")
    unlock_days_after_enrolment = Column(Integer, nullable=True)
    status = Column(String(20), nullable=True, server_default="draft")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=True)

    course = relationship("Course", back_populates="modules")
    videos = relationship("Video", back_populates="module", cascade="all, delete-orphan", order_by="Video.order_index")
    quizzes = relationship("Quiz", back_populates="module", cascade="all, delete-orphan")
    resources = relationship("Resource", back_populates="module", cascade="all, delete-orphan")

    __table_args__ = (Index("idx_module_course_order", "course_id", "order_index"),)


class Video(Base):
    """Video lesson within a module."""
    __tablename__ = "videos"

    id = Column(Integer, primary_key=True, index=True)
    module_id = Column(Integer, ForeignKey("modules.id", ondelete="CASCADE"), nullable=False)
    order_index = Column(Integer, nullable=False, server_default="0")
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    video_type = Column(String(50), nullable=False, server_default="slideshow_narrated")
    estimated_duration_seconds = Column(Integer, nullable=True)
    narration_voice_id = Column(String(100), nullable=True)
    source_video_url = Column(String(500), nullable=True)
    # ILB (podcast/avatar) config — used when video_type='podcast'
    heygen_avatar_id = Column(String(100), nullable=True)
    prerendered_video_url = Column(String(500), nullable=True)
    status = Column(String(20), nullable=True, server_default="draft")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=True)

    module = relationship("Module", back_populates="videos")
    slides = relationship("Slide", back_populates="video", cascade="all, delete-orphan", order_by="Slide.order_index")
    quizzes = relationship("Quiz", back_populates="video", cascade="all, delete-orphan")

    __table_args__ = (Index("idx_video_module_order", "module_id", "order_index"),)


class Slide(Base):
    """Slide within a video lesson."""
    __tablename__ = "slides"

    id = Column(Integer, primary_key=True, index=True)
    video_id = Column(Integer, ForeignKey("videos.id", ondelete="CASCADE"), nullable=False)
    order_index = Column(Integer, nullable=False, server_default="0")
    layout_id = Column(String(50), nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    narration_script = Column(Text, nullable=True)
    narration_audio_url = Column(String(500), nullable=True)
    narration_script_hash = Column(String(64), nullable=True)
    transition = Column(String(20), nullable=True, server_default="none")
    status = Column(String(20), nullable=True, server_default="draft")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=True)

    video = relationship("Video", back_populates="slides")
    blocks = relationship("Block", back_populates="slide", cascade="all, delete-orphan", order_by="Block.order_index")

    __table_args__ = (Index("idx_slide_video_order", "video_id", "order_index"),)


class Block(Base):
    """Content block on a slide — the drag-drop canvas unit."""
    __tablename__ = "blocks"

    id = Column(Integer, primary_key=True, index=True)
    slide_id = Column(Integer, ForeignKey("slides.id", ondelete="CASCADE"), nullable=False)
    order_index = Column(Integer, nullable=False, server_default="0")
    type = Column(String(50), nullable=False)
    content = Column(JSON, nullable=True)
    style = Column(JSON, nullable=True)
    alt_text = Column(String(500), nullable=True)
    grid_position = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=True)

    slide = relationship("Slide", back_populates="blocks")

    __table_args__ = (Index("idx_block_slide_order", "slide_id", "order_index"),)


class CourseSourceDocument(Base):
    """Extracted text from a file uploaded for AI course generation.

    Stores per-file source text used (a) as provenance ("generated from these
    files") and (b) as the grounding corpus for per-video slide-content generation.
    """
    __tablename__ = "course_source_documents"

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    filename = Column(String(500), nullable=False)
    content_type = Column(String(200), nullable=True)
    char_count = Column(Integer, nullable=False, server_default="0")
    extracted_text = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    course = relationship("Course")

    __table_args__ = (Index("idx_source_doc_course", "course_id"),)


class Quiz(Base):
    """Quiz — can be attached to a module (assessment) or video (knowledge check)."""
    __tablename__ = "quizzes"

    id = Column(Integer, primary_key=True, index=True)
    module_id = Column(Integer, ForeignKey("modules.id", ondelete="CASCADE"), nullable=True)
    video_id = Column(Integer, ForeignKey("videos.id", ondelete="CASCADE"), nullable=True)
    order_index = Column(Integer, nullable=False, server_default="0")
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    quiz_type = Column(String(50), nullable=False, server_default="knowledge_check")
    pass_rate = Column(Integer, nullable=False, server_default="80")
    attempts_allowed = Column(Integer, nullable=False, server_default="3")
    time_limit_seconds = Column(Integer, nullable=True)
    shuffle_questions = Column(Boolean, nullable=False, server_default="0")
    show_feedback = Column(String(20), nullable=False, server_default="immediate")
    on_fail_action = Column(String(20), nullable=False, server_default="retake")
    status = Column(String(20), nullable=True, server_default="draft")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=True)

    module = relationship("Module", back_populates="quizzes")
    video = relationship("Video", back_populates="quizzes")
    questions = relationship("Question", back_populates="quiz", cascade="all, delete-orphan", order_by="Question.order_index")

    __table_args__ = (Index("idx_quiz_module", "module_id"),)


class Question(Base):
    """Question within a quiz."""
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, index=True)
    quiz_id = Column(Integer, ForeignKey("quizzes.id", ondelete="CASCADE"), nullable=False)
    order_index = Column(Integer, nullable=False, server_default="0")
    type = Column(String(50), nullable=False)
    prompt = Column(Text, nullable=False)
    points = Column(Integer, nullable=False, server_default="1")
    explanation = Column(Text, nullable=True)
    options = Column(JSON, nullable=True)
    correct_answer = Column(JSON, nullable=True)
    linked_objective_id = Column(Integer, nullable=True)
    difficulty = Column(String(20), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=True)

    quiz = relationship("Quiz", back_populates="questions")

    __table_args__ = (Index("idx_question_quiz_order", "quiz_id", "order_index"),)


class Resource(Base):
    """Downloadable resource attached to a module."""
    __tablename__ = "resources"

    id = Column(Integer, primary_key=True, index=True)
    module_id = Column(Integer, ForeignKey("modules.id", ondelete="CASCADE"), nullable=False)
    type = Column(String(50), nullable=False)
    title = Column(String(500), nullable=False)
    url_or_file = Column(String(500), nullable=False)
    visible_to_learner = Column(Boolean, nullable=False, server_default="1")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    module = relationship("Module", back_populates="resources")

    __table_args__ = (Index("idx_resource_module", "module_id"),)


class AiPromptLog(Base):
    """Log of all AI generation operations for cost tracking and debugging."""
    __tablename__ = "ai_prompt_log"

    id = Column(Integer, primary_key=True, index=True)
    creator_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    operation = Column(String(100), nullable=False)
    inputs = Column(JSON, nullable=True)
    output = Column(Text, nullable=True)
    model_tier = Column(String(50), nullable=True)
    tokens_used = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    __table_args__ = (Index("idx_ai_log_creator_created", "creator_id", "created_at"),)


class CourseVersion(Base):
    """Immutable snapshot of a course at publish time, used for learner version pinning."""
    __tablename__ = "course_versions"

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    version_number = Column(Integer, nullable=False)
    snapshot = Column(JSON, nullable=False)
    published_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("course_id", "version_number", name="uq_course_version"),
        Index("idx_course_version", "course_id", "version_number"),
    )


class BroadcastSession(Base):
    """An ILB (Interactive Learning Broadcast) play session.

    Named BroadcastSession to avoid colliding with the auth `Session` table.
    Links to an Enrollment, which already carries the learner + course-version pin.
    """
    __tablename__ = "broadcast_sessions"

    id = Column(Integer, primary_key=True, index=True)
    # A session is backed by EITHER a course enrolment OR a standalone broadcast.
    enrollment_id = Column(Integer, ForeignKey("enrollments.id", ondelete="CASCADE"), nullable=True)
    broadcast_id = Column(Integer, ForeignKey("broadcasts.id", ondelete="CASCADE"), nullable=True)
    learner_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)  # set for standalone
    mode = Column(String(20), nullable=False, server_default="interrupt")  # interrupt | defer
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    final_score = Column(Float, nullable=True)  # percentage 0-100
    completion_status = Column(String(20), nullable=False, server_default="in_progress")  # in_progress | completed | abandoned
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=True)

    enrollment = relationship("Enrollment", back_populates="broadcast_sessions")
    broadcast = relationship("Broadcast", back_populates="sessions")
    interactions = relationship("Interaction", back_populates="broadcast_session", cascade="all, delete-orphan", order_by="Interaction.ts")
    attestations = relationship("SessionAttestation", back_populates="broadcast_session", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_broadcast_enrollment", "enrollment_id"),
        Index("idx_broadcast_session_broadcast", "broadcast_id"),
    )


class Interaction(Base):
    """A single logged interaction within a broadcast session (Q&A, knowledge check, attention check)."""
    __tablename__ = "interactions"

    id = Column(Integer, primary_key=True, index=True)
    broadcast_session_id = Column(Integer, ForeignKey("broadcast_sessions.id", ondelete="CASCADE"), nullable=False)
    ts = Column(DateTime, default=datetime.utcnow, nullable=False)
    type = Column(String(20), nullable=False)  # question | answer | check | attention
    input_mode = Column(String(10), nullable=True)  # voice | text
    question_text = Column(Text, nullable=True)
    answer_text = Column(Text, nullable=True)
    source_refs = Column(JSON, nullable=True)  # cited source passages used to ground the answer
    confidence = Column(Float, nullable=True)
    escalated = Column(Boolean, nullable=False, server_default="0")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    broadcast_session = relationship("BroadcastSession", back_populates="interactions")

    __table_args__ = (Index("idx_interaction_session_ts", "broadcast_session_id", "ts"),)


class SessionAttestation(Base):
    """Tamper-evidence record for a broadcast session.

    Per-learner hash chain: each attestation's prev_hash points at the learner's previous
    attestation content_hash. timestamp_token (RFC 3161) and anchor_ref (WORM) are populated
    by the external anchor; STUBBED in the demo, hardened in the praxis rebuild.
    """
    __tablename__ = "session_attestations"

    id = Column(Integer, primary_key=True, index=True)
    broadcast_session_id = Column(Integer, ForeignKey("broadcast_sessions.id", ondelete="CASCADE"), nullable=False)
    learner_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    sequence = Column(Integer, nullable=False, server_default="0")  # position in the learner's chain
    content_hash = Column(String(64), nullable=False)
    prev_hash = Column(String(64), nullable=True)
    signed_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    timestamp_token = Column(Text, nullable=True)   # RFC 3161 token — stub in demo
    anchor_ref = Column(String(500), nullable=True)  # WORM storage reference — stub in demo
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    broadcast_session = relationship("BroadcastSession", back_populates="attestations")

    __table_args__ = (
        Index("idx_attestation_session", "broadcast_session_id"),
        Index("idx_attestation_learner_seq", "learner_id", "sequence"),
    )


class Broadcast(Base):
    """A STANDALONE Interactive Learning Broadcast — org content outside a course
    (team brief, company news, policy update). Course-attached broadcasts live on Course;
    this is the additive standalone path with its own source material.
    """
    __tablename__ = "broadcasts"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    creator_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    source_text = Column(Text, nullable=True)  # grounding source (paste / extracted doc / AI topic)
    host_persona = Column(String(255), nullable=True)
    avatar_id = Column(String(100), nullable=True)
    voice_id = Column(String(100), nullable=True)
    script = Column(Text, nullable=True)
    segments = Column(JSON, nullable=True)
    segment_audio = Column(JSON, nullable=True)
    segment_video = Column(JSON, nullable=True)        # parallel to segment_audio; MP4 URLs (or None per seg)
    video_render_jobs = Column(JSON, nullable=True)    # [{"seg_index": int, "heygen_video_id": str, "status": str}]
    published = Column(Boolean, nullable=False, server_default="0")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=True)

    sessions = relationship("BroadcastSession", back_populates="broadcast")

    __table_args__ = (Index("idx_broadcast_creator", "creator_id"),)


class Department(Base):
    """A group of users that courses/podcasts can be assigned to."""

    __tablename__ = "departments"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    members = relationship(
        "DepartmentMember", back_populates="department", cascade="all, delete-orphan"
    )
    content = relationship(
        "DepartmentContent", back_populates="department", cascade="all, delete-orphan"
    )


class DepartmentMember(Base):
    """Join row: a user belongs to a department (many-to-many)."""

    __tablename__ = "department_members"

    id = Column(Integer, primary_key=True, index=True)
    department_id = Column(Integer, ForeignKey("departments.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    added_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    department = relationship("Department", back_populates="members")
    user = relationship("User")

    __table_args__ = (
        UniqueConstraint("department_id", "user_id", name="uq_department_user"),
        Index("idx_department_member_user", "user_id"),
        Index("idx_department_member_dept", "department_id"),
    )


class DepartmentContent(Base):
    """A course OR standalone broadcast assigned to a department, optionally mandatory.

    Exactly one of course_id / broadcast_id is set per row (enforced at the API boundary);
    the content "kind" is derived ('broadcast' if broadcast_id else 'course'). A course may
    itself be a course-attached broadcast (Course.ilb_published); a standalone broadcast is
    the Broadcast entity (org content outside a course). due_mode is 'fixed' (use due_date)
    or 'relative' (use due_days from the user's department-join date), or None for a
    mandatory item with no hard deadline.
    """

    __tablename__ = "department_content"

    id = Column(Integer, primary_key=True, index=True)
    department_id = Column(Integer, ForeignKey("departments.id", ondelete="CASCADE"), nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=True)
    broadcast_id = Column(Integer, ForeignKey("broadcasts.id", ondelete="CASCADE"), nullable=True)
    mandatory = Column(Boolean, default=False, nullable=False)
    due_mode = Column(String(20), nullable=True)
    due_date = Column(DateTime, nullable=True)
    due_days = Column(Integer, nullable=True)
    assigned_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    department = relationship("Department", back_populates="content")
    course = relationship("Course")
    broadcast = relationship("Broadcast")

    __table_args__ = (
        UniqueConstraint("department_id", "course_id", name="uq_department_course"),
        UniqueConstraint("department_id", "broadcast_id", name="uq_department_broadcast"),
        Index("idx_department_content_course", "course_id"),
        Index("idx_department_content_broadcast", "broadcast_id"),
    )


class IntegrationSettings(Base):
    """Single-row store for third-party API keys set via the admin Settings page.

    Always exactly one row (id == 1). A non-empty value overrides the corresponding
    environment variable at runtime (see services/integration_settings_service.py).
    NOTE: prod SQLite has no persistent volume, so these are wiped on redeploy —
    set the matching env vars in Coolify for permanence.
    """

    __tablename__ = "integration_settings"

    id = Column(Integer, primary_key=True)
    elevenlabs_api_key = Column(String(255), nullable=True)
    deepgram_api_key = Column(String(255), nullable=True)
    claude_api_key = Column(String(255), nullable=True)
    heygen_api_key = Column(String(255), nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
