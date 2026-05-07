from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import AsyncSessionLocal
from app.models import Course, Lesson, Module, Slide
from app.document_parser import extract_text
from app.ai_service import generate_course
from app.services.quiz_service import generate_quiz_questions, questions_to_blocks
import json, uuid, logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["ingest"])

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

def get_user(x_user_id: str = Header(default="system")) -> str:
    return x_user_id


@router.post("/courses/{course_id}/ingest")
async def ingest_document(
    course_id: str,
    file: UploadFile = File(...),
    generate_quiz: bool = Form(False),
    quiz_per_lesson: int = Form(3),
    quiz_difficulty: str = Form("medium"),
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_user),
):
    # Validate course exists
    result = await db.execute(select(Course).where(Course.id == course_id))
    course = result.scalar_one_or_none()
    if not course:
        raise HTTPException(404, "Course not found")

    # Clamp quiz_per_lesson
    quiz_per_lesson = max(1, min(10, quiz_per_lesson))
    if quiz_difficulty not in ("easy", "medium", "hard"):
        quiz_difficulty = "medium"

    # Extract text
    data = await file.read()
    if not file.filename:
        raise HTTPException(400, "No filename")
    try:
        text = await extract_text(data, file.filename)
    except Exception as e:
        raise HTTPException(422, f"Could not extract text: {e}")
    if len(text.strip()) < 50:
        raise HTTPException(422, "Document too short")

    # Generate course structure via AI
    try:
        course_data = await generate_course(text, file.filename)
    except Exception as e:
        logger.error("AI generation failed: %s", e)
        raise HTTPException(502, "Course generation failed — please try again")

    # Persist modules, lessons, and optionally quiz slides
    created = {"modules": 0, "lessons": 0, "quiz_slides": 0}
    for m_idx, mod in enumerate(course_data.get("modules", [])):
        module_id = str(uuid.uuid4())
        db.add(Module(
            id=module_id, course_id=course_id,
            title=mod["title"], sort_order=m_idx,
        ))
        for l_idx, lesson in enumerate(mod.get("lessons", [])):
            lesson_id = str(uuid.uuid4())
            db.add(Lesson(
                id=lesson_id, module_id=module_id, course_id=course_id,
                title=lesson["title"],
                summary=lesson.get("summary", ""),
                video_script=lesson.get("video_script", ""),
                quiz_json=json.dumps(lesson.get("quiz", [])),
                sort_order=l_idx,
            ))
            created["lessons"] += 1

            # AI quiz generation
            if generate_quiz:
                lesson_text = lesson.get("summary", "") + "\n" + lesson.get("video_script", "")
                try:
                    questions = await generate_quiz_questions(
                        lesson_title=lesson["title"],
                        lesson_text=lesson_text,
                        n=quiz_per_lesson,
                        difficulty=quiz_difficulty,
                    )
                    blocks = questions_to_blocks(questions)
                    if blocks:
                        db.add(Slide(
                            lesson_id=lesson_id,
                            title=f"Quiz: {lesson['title']}",
                            position=999,
                            layout="quiz",
                            blocks=blocks,
                            notes="AI-generated draft questions — review before publishing",
                        ))
                        created["quiz_slides"] += 1
                except Exception as e:
                    logger.warning("Quiz gen failed for lesson %s: %s", lesson["title"], e)

        created["modules"] += 1

    await db.commit()
    return {"status": "ok", "course_id": course_id, "created": created}
