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
    content = Column(JSON, nullable=True)
    creator_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(Enum(CourseStatus), default=CourseStatus.DRAFT, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    creator = relationship("User", back_populates="courses_created")
    enrollments = relationship("Enrollment", back_populates="course", cascade="all, delete-orphan")

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

    # Relationships
    user = relationship("User", back_populates="enrollments")
    course = relationship("Course", back_populates="enrollments")

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
