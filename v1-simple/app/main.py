"""LMS Course Builder — FastAPI application entry point."""

import json
import logging
import time
import uuid
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, File, HTTPException, UploadFile, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from sqlalchemy import delete, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from .config import settings
from .database import AsyncSessionLocal, init_db
from .document_parser import extract_text
from .ai_service import generate_course
from .logging_config import setup_logging
from .models import Course, Lesson, Module, TraineeProgress
from .routers import courses as courses_router
from .routers import themes as themes_router
from .routers import media as media_router
from .routers import scorm as scorm_router
from .routers import ingest as ingest_router
from .routers import catalog as catalog_router
from .routers import reports as reports_router
from .routers import notifications as notifications_router
from .routers import gdpr as gdpr_router
from .routers import billing as billing_router

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
setup_logging(settings.log_level)
logger = logging.getLogger(__name__)

APP_VERSION = "1.0.0"
START_TIME = time.time()


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    logger.info("Application started", extra={"version": APP_VERSION, "port": settings.port})
    yield
    logger.info("Application shutting down")


app = FastAPI(title="LMS Course Builder", version=APP_VERSION, lifespan=lifespan)

app.include_router(courses_router.router)
app.include_router(themes_router.router)
app.include_router(media_router.router)
app.include_router(scorm_router.router)
app.include_router(ingest_router.router)
app.include_router(catalog_router.router)
app.include_router(reports_router.router)
app.include_router(notifications_router.router)
app.include_router(gdpr_router.router)
app.include_router(billing_router.router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

import os as _os
from fastapi.staticfiles import StaticFiles as _StaticFiles
_os.makedirs("uploads", exist_ok=True)
app.mount("/uploads", _StaticFiles(directory="uploads"), name="uploads")


# ---------------------------------------------------------------------------
# ATLAS middleware — inject request_id into every response and log entry
# ---------------------------------------------------------------------------
@app.middleware("http")
async def atlas_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    request.state.request_id = request_id

    start = time.time()
    response = await call_next(request)
    duration_ms = round((time.time() - start) * 1000, 1)

    response.headers["X-Request-ID"] = request_id
    logger.info(
        "Request completed",
        extra={
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status": response.status_code,
            "duration_ms": duration_ms,
        },
    )
    return response


# ---------------------------------------------------------------------------
# ATLAS health & ready
# ---------------------------------------------------------------------------
@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "version": APP_VERSION,
        "uptime_seconds": round(time.time() - START_TIME, 1),
    }


@app.get("/ready")
async def ready():
    try:
        async with AsyncSessionLocal() as db:
            await db.execute(text("SELECT 1"))
        return {"status": "ready"}
    except Exception:
        return JSONResponse({"status": "not_ready"}, status_code=503)


# ---------------------------------------------------------------------------
# Error handler — ATLAS compliant (no raw stack traces)
# ---------------------------------------------------------------------------
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    request_id = getattr(request.state, "request_id", "unknown")
    logger.exception("Unhandled exception", extra={"request_id": request_id})
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "request_id": request_id,
        },
    )


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------
class ModuleUpdate(BaseModel):
    title: str | None = None


class LessonUpdate(BaseModel):
    title: str | None = None
    summary: str | None = None
    video_script: str | None = None


class QuizSubmission(BaseModel):
    answers: list[int]


# ---------------------------------------------------------------------------
# Document upload & course generation
# ---------------------------------------------------------------------------
@app.post("/api/courses/generate")
async def generate_course_endpoint(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(400, "No file provided")

    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in ("pdf", "docx"):
        raise HTTPException(400, "Only PDF and DOCX files are supported")

    file_bytes = await file.read()
    if len(file_bytes) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(400, f"File exceeds {settings.max_upload_mb}MB limit")

    # Extract text
    try:
        text_content = await extract_text(file_bytes, file.filename)
    except Exception as e:
        logger.error("Document extraction failed", extra={"error": str(e)})
        raise HTTPException(422, f"Could not extract text: {e}")

    if len(text_content.strip()) < 50:
        raise HTTPException(422, "Document contains too little text to generate a course")

    # Generate via AI
    try:
        course_data = await generate_course(text_content, file.filename)
    except json.JSONDecodeError:
        raise HTTPException(502, "AI returned invalid course structure — please try again")
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        logger.error("AI generation failed", extra={"error": str(e)})
        raise HTTPException(502, "Course generation failed — please try again")

    # Persist to database
    course_id = str(uuid.uuid4())
    async with AsyncSessionLocal() as db:
        async with db.begin():
            db.add(Course(
                id=course_id,
                title=course_data["title"],
                description=course_data.get("description", ""),
                source_filename=file.filename,
            ))
            for m_idx, mod in enumerate(course_data.get("modules", [])):
                module_id = str(uuid.uuid4())
                db.add(Module(
                    id=module_id,
                    course_id=course_id,
                    title=mod["title"],
                    sort_order=m_idx,
                ))
                for l_idx, lesson in enumerate(mod.get("lessons", [])):
                    db.add(Lesson(
                        id=str(uuid.uuid4()),
                        module_id=module_id,
                        course_id=course_id,
                        title=lesson["title"],
                        summary=lesson.get("summary", ""),
                        video_script=lesson.get("video_script", ""),
                        quiz_json=json.dumps(lesson.get("quiz", [])),
                        sort_order=l_idx,
                    ))

    return await _build_course_response(course_id)


# ---------------------------------------------------------------------------
# Course CRUD
# ---------------------------------------------------------------------------
@app.get("/api/courses")
async def list_courses(published_only: bool = False):
    async with AsyncSessionLocal() as db:
        stmt = select(Course).order_by(Course.created_at.desc())
        if published_only:
            stmt = stmt.where(Course.published == True)  # noqa: E712
        result = await db.execute(stmt)
        courses = result.scalars().all()
        return [_course_to_dict(c) for c in courses]


@app.get("/api/courses/{course_id}")
async def get_course(course_id: str):
    return await _build_course_response(course_id)


@app.post("/api/courses/{course_id}/publish")
async def publish_course(course_id: str):
    async with AsyncSessionLocal() as db:
        async with db.begin():
            result = await db.execute(
                update(Course)
                .where(Course.id == course_id)
                .values(published=True)
            )
            if result.rowcount == 0:
                raise HTTPException(404, "Course not found")
    return {"status": "published"}


@app.post("/api/courses/{course_id}/unpublish")
async def unpublish_course(course_id: str):
    async with AsyncSessionLocal() as db:
        async with db.begin():
            result = await db.execute(
                update(Course)
                .where(Course.id == course_id)
                .values(published=False)
            )
            if result.rowcount == 0:
                raise HTTPException(404, "Course not found")
    return {"status": "unpublished"}


@app.delete("/api/courses/{course_id}")
async def delete_course(course_id: str):
    async with AsyncSessionLocal() as db:
        async with db.begin():
            result = await db.execute(
                delete(Course).where(Course.id == course_id)
            )
            if result.rowcount == 0:
                raise HTTPException(404, "Course not found")
    return {"status": "deleted"}


@app.post("/api/courses/{course_id}/regenerate")
async def regenerate_course(course_id: str, file: UploadFile = File(...)):
    """Delete existing course content and regenerate from the uploaded document."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Course).where(Course.id == course_id))
        if not result.scalar_one_or_none():
            raise HTTPException(404, "Course not found")

    # Delete old modules/lessons/progress (cascade handles lessons & progress)
    async with AsyncSessionLocal() as db:
        async with db.begin():
            await db.execute(delete(TraineeProgress).where(TraineeProgress.course_id == course_id))
            await db.execute(delete(Lesson).where(Lesson.course_id == course_id))
            await db.execute(delete(Module).where(Module.course_id == course_id))

    file_bytes = await file.read()
    text_content = await extract_text(file_bytes, file.filename or "document")

    try:
        course_data = await generate_course(text_content, file.filename or "document")
    except Exception as e:
        logger.error("Regeneration failed", extra={"error": str(e)})
        raise HTTPException(502, "Regeneration failed — please try again")

    async with AsyncSessionLocal() as db:
        async with db.begin():
            await db.execute(
                update(Course)
                .where(Course.id == course_id)
                .values(title=course_data["title"], description=course_data.get("description", ""))
            )
            for m_idx, mod in enumerate(course_data.get("modules", [])):
                module_id = str(uuid.uuid4())
                db.add(Module(id=module_id, course_id=course_id, title=mod["title"], sort_order=m_idx))
                for l_idx, lesson in enumerate(mod.get("lessons", [])):
                    db.add(Lesson(
                        id=str(uuid.uuid4()),
                        module_id=module_id,
                        course_id=course_id,
                        title=lesson["title"],
                        summary=lesson.get("summary", ""),
                        video_script=lesson.get("video_script", ""),
                        quiz_json=json.dumps(lesson.get("quiz", [])),
                        sort_order=l_idx,
                    ))

    return await _build_course_response(course_id)


# ---------------------------------------------------------------------------
# Module / Lesson editing
# ---------------------------------------------------------------------------
@app.patch("/api/modules/{module_id}")
async def update_module(module_id: str, body: ModuleUpdate):
    async with AsyncSessionLocal() as db:
        async with db.begin():
            if body.title is not None:
                result = await db.execute(
                    update(Module).where(Module.id == module_id).values(title=body.title)
                )
                if result.rowcount == 0:
                    raise HTTPException(404, "Module not found")
    return {"status": "updated"}


@app.delete("/api/modules/{module_id}")
async def delete_module(module_id: str):
    async with AsyncSessionLocal() as db:
        async with db.begin():
            await db.execute(delete(Lesson).where(Lesson.module_id == module_id))
            result = await db.execute(delete(Module).where(Module.id == module_id))
            if result.rowcount == 0:
                raise HTTPException(404, "Module not found")
    return {"status": "deleted"}


@app.patch("/api/lessons/{lesson_id}")
async def update_lesson(lesson_id: str, body: LessonUpdate):
    values: dict[str, Any] = {}
    if body.title is not None:
        values["title"] = body.title
    if body.summary is not None:
        values["summary"] = body.summary
    if body.video_script is not None:
        values["video_script"] = body.video_script

    if values:
        async with AsyncSessionLocal() as db:
            async with db.begin():
                result = await db.execute(
                    update(Lesson).where(Lesson.id == lesson_id).values(**values)
                )
                if result.rowcount == 0:
                    raise HTTPException(404, "Lesson not found")
    return {"status": "updated"}


@app.delete("/api/lessons/{lesson_id}")
async def delete_lesson(lesson_id: str):
    async with AsyncSessionLocal() as db:
        async with db.begin():
            result = await db.execute(delete(Lesson).where(Lesson.id == lesson_id))
            if result.rowcount == 0:
                raise HTTPException(404, "Lesson not found")
    return {"status": "deleted"}


# ---------------------------------------------------------------------------
# Trainee progress
# ---------------------------------------------------------------------------
@app.get("/api/courses/{course_id}/progress/{trainee_id}")
async def get_progress(course_id: str, trainee_id: str):
    async with AsyncSessionLocal() as db:
        lesson_result = await db.execute(
            select(Lesson.id).where(Lesson.course_id == course_id).order_by(Lesson.sort_order)
        )
        lesson_ids = [row[0] for row in lesson_result]
        total = len(lesson_ids)

        progress_result = await db.execute(
            select(TraineeProgress).where(
                TraineeProgress.course_id == course_id,
                TraineeProgress.trainee_id == trainee_id,
            )
        )
        progress_rows = progress_result.scalars().all()
        completed = sum(1 for r in progress_rows if r.completed)
        progress_map = {r.lesson_id: _progress_to_dict(r) for r in progress_rows}
        return {
            "trainee_id": trainee_id,
            "course_id": course_id,
            "total_lessons": total,
            "completed_lessons": completed,
            "progress_pct": round((completed / total) * 100, 1) if total > 0 else 0,
            "lessons": progress_map,
        }


@app.post("/api/lessons/{lesson_id}/complete")
async def complete_lesson(lesson_id: str, trainee_id: str, body: QuizSubmission):
    async with AsyncSessionLocal() as db:
        lesson_result = await db.execute(select(Lesson).where(Lesson.id == lesson_id))
        lesson = lesson_result.scalar_one_or_none()
        if not lesson:
            raise HTTPException(404, "Lesson not found")

        quiz = json.loads(lesson.quiz_json)

        # Score the quiz
        correct = 0
        for i, q in enumerate(quiz):
            if i < len(body.answers) and body.answers[i] == q.get("correct"):
                correct += 1
        score = round((correct / len(quiz)) * 100, 1) if quiz else 100.0

        # Upsert progress
        existing_result = await db.execute(
            select(TraineeProgress).where(
                TraineeProgress.trainee_id == trainee_id,
                TraineeProgress.lesson_id == lesson_id,
            )
        )
        existing = existing_result.scalar_one_or_none()

        async with db.begin():
            if existing:
                existing.completed = True
                existing.quiz_score = score
                existing.quiz_answers_json = json.dumps(body.answers)
                from datetime import datetime, timezone
                existing.completed_at = datetime.now(timezone.utc)
            else:
                from datetime import datetime, timezone
                db.add(TraineeProgress(
                    id=str(uuid.uuid4()),
                    trainee_id=trainee_id,
                    course_id=lesson.course_id,
                    lesson_id=lesson_id,
                    completed=True,
                    quiz_score=score,
                    quiz_answers_json=json.dumps(body.answers),
                    completed_at=datetime.now(timezone.utc),
                ))

        return {"status": "completed", "score": score, "correct": correct, "total": len(quiz)}


@app.post("/api/courses/{course_id}/reset/{trainee_id}")
async def reset_progress(course_id: str, trainee_id: str):
    async with AsyncSessionLocal() as db:
        async with db.begin():
            await db.execute(
                delete(TraineeProgress).where(
                    TraineeProgress.course_id == course_id,
                    TraineeProgress.trainee_id == trainee_id,
                )
            )
    return {"status": "reset"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _course_to_dict(course: Course) -> dict[str, Any]:
    return {
        "id": course.id,
        "title": course.title,
        "description": course.description,
        "source_filename": course.source_filename,
        "published": course.published,
        "created_at": course.created_at.isoformat() if course.created_at else None,
        "updated_at": course.updated_at.isoformat() if course.updated_at else None,
    }


def _progress_to_dict(p: TraineeProgress) -> dict[str, Any]:
    return {
        "id": p.id,
        "trainee_id": p.trainee_id,
        "course_id": p.course_id,
        "lesson_id": p.lesson_id,
        "completed": p.completed,
        "quiz_score": p.quiz_score,
        "quiz_answers_json": p.quiz_answers_json,
        "completed_at": p.completed_at.isoformat() if p.completed_at else None,
    }


async def _build_course_response(course_id: str) -> dict[str, Any]:
    async with AsyncSessionLocal() as db:
        course_result = await db.execute(select(Course).where(Course.id == course_id))
        course = course_result.scalar_one_or_none()
        if not course:
            raise HTTPException(404, "Course not found")

        course_dict = _course_to_dict(course)

        modules_result = await db.execute(
            select(Module).where(Module.course_id == course_id).order_by(Module.sort_order)
        )
        modules = modules_result.scalars().all()

        course_dict["modules"] = []
        for mod in modules:
            mod_dict = {
                "id": mod.id,
                "course_id": mod.course_id,
                "title": mod.title,
                "sort_order": mod.sort_order,
            }
            lessons_result = await db.execute(
                select(Lesson).where(Lesson.module_id == mod.id).order_by(Lesson.sort_order)
            )
            lessons = lessons_result.scalars().all()
            mod_dict["lessons"] = []
            for les in lessons:
                les_dict = {
                    "id": les.id,
                    "module_id": les.module_id,
                    "course_id": les.course_id,
                    "title": les.title,
                    "summary": les.summary,
                    "video_script": les.video_script,
                    "sort_order": les.sort_order,
                    "quiz": json.loads(les.quiz_json or "[]"),
                }
                mod_dict["lessons"].append(les_dict)
            course_dict["modules"].append(mod_dict)

        return course_dict


# ---------------------------------------------------------------------------
# Serve frontend
# ---------------------------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
async def serve_frontend():
    import pathlib
    index = pathlib.Path(__file__).parent / "static" / "index.html"
    return HTMLResponse(index.read_text())
