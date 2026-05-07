"""SQLAlchemy ORM models — P1 + P2: all V1 tables."""

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean, Column, DateTime, Float, ForeignKey, Index, Integer,
    JSON, String, Text, UniqueConstraint, func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


# ---------------------------------------------------------------------------
# P1 models (kept unchanged except for new columns/relationships noted below)
# ---------------------------------------------------------------------------

class Course(Base):
    __tablename__ = "courses"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    source_filename: Mapped[str] = mapped_column(String, nullable=False, default="")
    published: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(nullable=False, server_default=func.now(), onupdate=func.now())

    # P2 additions
    catalog_visible: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, server_default="0")
    self_enrol_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, server_default="0")
    price_pence: Mapped[int] = mapped_column(Integer, default=0, nullable=False, server_default="0")
    estimated_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    pass_threshold: Mapped[int] = mapped_column(Integer, default=80, nullable=False, server_default="80")

    modules: Mapped[list["Module"]] = relationship("Module", back_populates="course", cascade="all, delete-orphan")
    trainee_progress: Mapped[list["TraineeProgress"]] = relationship("TraineeProgress", back_populates="course", cascade="all, delete-orphan")
    course_theme: Mapped["CourseTheme | None"] = relationship("CourseTheme", back_populates="course", uselist=False, cascade="all, delete-orphan")


class Module(Base):
    __tablename__ = "modules"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    course_id: Mapped[str] = mapped_column(String, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    course: Mapped["Course"] = relationship("Course", back_populates="modules")
    lessons: Mapped[list["Lesson"]] = relationship("Lesson", back_populates="module", cascade="all, delete-orphan")


class Lesson(Base):
    __tablename__ = "lessons"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    module_id: Mapped[str] = mapped_column(String, ForeignKey("modules.id", ondelete="CASCADE"), nullable=False)
    course_id: Mapped[str] = mapped_column(String, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    video_script: Mapped[str] = mapped_column(Text, nullable=False, default="")
    quiz_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    module: Mapped["Module"] = relationship("Module", back_populates="lessons")
    trainee_progress: Mapped[list["TraineeProgress"]] = relationship("TraineeProgress", back_populates="lesson", cascade="all, delete-orphan")
    slides: Mapped[list["Slide"]] = relationship("Slide", back_populates="lesson", cascade="all, delete-orphan")


class TraineeProgress(Base):
    __tablename__ = "trainee_progress"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    trainee_id: Mapped[str] = mapped_column(String, nullable=False)
    course_id: Mapped[str] = mapped_column(String, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    lesson_id: Mapped[str] = mapped_column(String, ForeignKey("lessons.id", ondelete="CASCADE"), nullable=False)
    completed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    quiz_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    quiz_answers_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(nullable=True)

    course: Mapped["Course"] = relationship("Course", back_populates="trainee_progress")
    lesson: Mapped["Lesson"] = relationship("Lesson", back_populates="trainee_progress")

    __table_args__ = (UniqueConstraint("trainee_id", "lesson_id", name="uq_trainee_lesson"),)


# ---------------------------------------------------------------------------
# P2 models — new V1 tables
# ---------------------------------------------------------------------------

class Theme(Base):
    __tablename__ = "themes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    slug = Column(String(50), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    tokens = Column(JSON, nullable=False)
    is_system = Column(Boolean, default=True)
    # created_by references users.id — deferred until auth system added
    created_by = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    course_themes: Mapped[list["CourseTheme"]] = relationship("CourseTheme", back_populates="theme")


class CourseTheme(Base):
    __tablename__ = "course_themes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    course_id = Column(String, ForeignKey("courses.id", ondelete="CASCADE"), unique=True, nullable=False)
    theme_id = Column(Integer, ForeignKey("themes.id"), nullable=False)
    overrides = Column(JSON, nullable=True)

    course: Mapped["Course"] = relationship("Course", back_populates="course_theme")
    theme: Mapped["Theme"] = relationship("Theme", back_populates="course_themes")


class Slide(Base):
    __tablename__ = "slides"

    id = Column(Integer, primary_key=True, autoincrement=True)
    lesson_id = Column(String, ForeignKey("lessons.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(500), nullable=True)
    position = Column(Integer, nullable=False, default=0)
    layout = Column(String(100), nullable=False, default="single-column")
    blocks = Column(JSON, nullable=False, default=list)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    lesson: Mapped["Lesson"] = relationship("Lesson", back_populates="slides")

    __table_args__ = (Index("idx_slide_lesson_pos", "lesson_id", "position"),)


class MediaAsset(Base):
    __tablename__ = "media_assets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    course_id = Column(String, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    # uploader_id references users.id — deferred until auth system added
    uploader_id = Column(String, nullable=False)
    kind = Column(String(50), nullable=False)
    filename = Column(String(500), nullable=False)
    storage_key = Column(String(1000), nullable=False)
    mime_type = Column(String(100), nullable=False)
    size_bytes = Column(Integer, nullable=False)
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    duration_s = Column(Float, nullable=True)
    alt_text = Column(String(1000), nullable=True)
    source = Column(String(50), nullable=False, default="upload")
    source_ref = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class ScormPackage(Base):
    __tablename__ = "scorm_packages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    course_id = Column(String, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    version = Column(String(50), nullable=False)
    export_version = Column(Integer, nullable=False)
    storage_key = Column(String(1000), nullable=False)
    size_bytes = Column(Integer, nullable=False)
    # exported_by references users.id — deferred until auth system added
    exported_by = Column(String, nullable=False)
    exported_at = Column(DateTime, default=datetime.utcnow)


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, autoincrement=True)
    # user_id references users.id — deferred until auth system added
    user_id = Column(String, nullable=False)
    kind = Column(String(50), nullable=False)
    course_id = Column(String, ForeignKey("courses.id", ondelete="CASCADE"), nullable=True)
    payload = Column(JSON, nullable=True)
    sent_email_at = Column(DateTime, nullable=True)
    read_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (Index("idx_notification_user_created", "user_id", "created_at"),)


class BillingAccount(Base):
    __tablename__ = "billing_accounts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    # user_id references users.id — deferred until auth system added
    user_id = Column(String, unique=True, nullable=False)
    stripe_customer_id = Column(String(255), unique=True, nullable=True)
    plan = Column(String(50), nullable=False, default="payg")
    created_at = Column(DateTime, default=datetime.utcnow)

    transactions: Mapped[list["BillingTransaction"]] = relationship("BillingTransaction", back_populates="account")


class BillingTransaction(Base):
    __tablename__ = "billing_transactions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    account_id = Column(Integer, ForeignKey("billing_accounts.id"), nullable=False)
    course_id = Column(String, ForeignKey("courses.id"), nullable=True)
    # enrollment_id references enrollments.id — deferred until enrollments table added
    enrollment_id = Column(String, nullable=True)
    stripe_payment_intent = Column(String(255), unique=True, nullable=True)
    amount_pence = Column(Integer, nullable=False)
    currency = Column(String(3), nullable=False, default="GBP")
    status = Column(String(50), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    account: Mapped["BillingAccount"] = relationship("BillingAccount", back_populates="transactions")


class DataDeletionRequest(Base):
    __tablename__ = "data_deletion_requests"

    id = Column(Integer, primary_key=True, autoincrement=True)
    # user_id references users.id — deferred until auth system added
    user_id = Column(String, nullable=False)
    requested_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    status = Column(String(50), default="pending")


# ---------------------------------------------------------------------------
# P8 models — Enrollment
# ---------------------------------------------------------------------------

class Enrollment(Base):
    __tablename__ = "enrollments"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, nullable=False)          # learner ID
    course_id = Column(String, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    enrolled_at = Column(DateTime, default=datetime.utcnow)
    completed = Column(Boolean, default=False, nullable=False)
    progress_pct = Column(Float, default=0.0, nullable=False)
    score = Column(Float, nullable=True)
    last_slide_id = Column(Integer, nullable=True)
    time_spent_s = Column(Integer, default=0, nullable=False)
    due_date = Column(DateTime, nullable=True)
    assigned_by = Column(String, nullable=True)       # admin user ID who assigned
    completed_at = Column(DateTime, nullable=True)

    __table_args__ = (UniqueConstraint("user_id", "course_id", name="uq_enrollment"),)
