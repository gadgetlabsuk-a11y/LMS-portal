"""
Quiz CRUD + Question CRUD + question reorder router.
Available to creator and admin roles only.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session
from starlette.requests import Request
from datetime import datetime
from typing import Any, List, Optional
import logging

from database import get_db
from models import Course, Module, Quiz, Question, CourseStatus
from middleware.auth_middleware import require_creator
from sse_starlette.sse import EventSourceResponse
from services.claude_service import ClaudeService

logger = logging.getLogger(__name__)
claude_service = ClaudeService()

router = APIRouter(tags=["quizzes"])


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

class QuizCreate(BaseModel):
    title: str
    description: Optional[str] = None
    quiz_type: Optional[str] = "knowledge_check"
    pass_rate: Optional[int] = 80
    attempts_allowed: Optional[int] = 3
    time_limit_seconds: Optional[int] = None
    shuffle_questions: Optional[bool] = False
    show_feedback: Optional[str] = "immediate"
    on_fail_action: Optional[str] = "retake"
    status: Optional[str] = "draft"


class QuizUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    quiz_type: Optional[str] = None
    pass_rate: Optional[int] = None
    attempts_allowed: Optional[int] = None
    time_limit_seconds: Optional[int] = None
    shuffle_questions: Optional[bool] = None
    show_feedback: Optional[str] = None
    on_fail_action: Optional[str] = None
    status: Optional[str] = None


class QuizResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    module_id: Optional[int]
    video_id: Optional[int]
    order_index: int
    title: str
    pass_rate: int
    attempts_allowed: int
    shuffle_questions: bool
    show_feedback: str
    status: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]


class QuestionCreate(BaseModel):
    type: str
    prompt: str
    points: Optional[int] = 1
    explanation: Optional[str] = None
    options: Optional[list] = None
    correct_answer: Optional[Any] = None
    difficulty: Optional[str] = None


class QuestionUpdate(BaseModel):
    type: Optional[str] = None
    prompt: Optional[str] = None
    points: Optional[int] = None
    explanation: Optional[str] = None
    options: Optional[list] = None
    correct_answer: Optional[Any] = None
    difficulty: Optional[str] = None


class QuestionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    quiz_id: int
    order_index: int
    type: str
    prompt: str
    points: int
    explanation: Optional[str]
    options: Optional[list]
    correct_answer: Optional[Any]
    difficulty: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]


class QuestionReorderRequest(BaseModel):
    question_ids: List[int]


class AiQuestionRequest(BaseModel):
    count: Optional[int] = 5
    tone_preset: Optional[str] = "professional"


# ---------------------------------------------------------------------------
# Ownership helpers
# ---------------------------------------------------------------------------

def _get_module_or_404(module_id: int, db: Session, current_user) -> Module:
    """Fetch module (with course join), raise 404 if missing, 403 if not owner."""
    module = db.query(Module).join(Course).filter(Module.id == module_id).first()
    if not module:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Module not found")
    if current_user.role.value != "admin" and module.course.creator_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return module


def _get_quiz_or_404(quiz_id: int, db: Session, current_user) -> Quiz:
    """Fetch quiz (with module/course join via module_id), raise 404 if missing, 403 if not owner."""
    quiz = db.query(Quiz).join(Module, Quiz.module_id == Module.id).join(Course).filter(Quiz.id == quiz_id).first()
    if not quiz:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quiz not found")
    if current_user.role.value != "admin" and quiz.module.course.creator_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return quiz


def _get_question_or_404(question_id: int, db: Session, current_user) -> Question:
    """Fetch question (with quiz/module/course join), raise 404 if missing, 403 if not owner."""
    question = (
        db.query(Question)
        .join(Quiz, Question.quiz_id == Quiz.id)
        .join(Module, Quiz.module_id == Module.id)
        .join(Course, Module.course_id == Course.id)
        .filter(Question.id == question_id)
        .first()
    )
    if not question:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")
    if current_user.role.value != "admin" and question.quiz.module.course.creator_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return question


def _mark_course_changed(course_id: int, db: Session) -> None:
    """Set HAS_UNPUBLISHED_CHANGES on a PUBLISHED course.

    Only transitions when status == PUBLISHED. Caller is responsible for db.commit().
    """
    course = db.query(Course).filter(Course.id == course_id).first()
    if course and course.status == CourseStatus.PUBLISHED:
        course.status = CourseStatus.HAS_UNPUBLISHED_CHANGES
        db.add(course)


# ---------------------------------------------------------------------------
# Quiz endpoints
# ---------------------------------------------------------------------------

@router.post(
    "/api/modules/{module_id}/quizzes",
    response_model=QuizResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_quiz(
    module_id: int,
    body: QuizCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_creator),
) -> Quiz:
    """Create a new quiz linked to a module."""
    module = _get_module_or_404(module_id, db, current_user)

    max_index = db.query(Quiz).filter(Quiz.module_id == module_id).count()

    quiz = Quiz(
        module_id=module.id,
        order_index=max_index,
        title=body.title,
        description=body.description,
        quiz_type=body.quiz_type or "knowledge_check",
        pass_rate=body.pass_rate if body.pass_rate is not None else 80,
        attempts_allowed=body.attempts_allowed if body.attempts_allowed is not None else 3,
        time_limit_seconds=body.time_limit_seconds,
        shuffle_questions=body.shuffle_questions if body.shuffle_questions is not None else False,
        show_feedback=body.show_feedback or "immediate",
        on_fail_action=body.on_fail_action or "retake",
        status=body.status or "draft",
    )
    db.add(quiz)
    _mark_course_changed(module.course_id, db)
    db.commit()
    db.refresh(quiz)

    logger.info(f"Quiz created: {quiz.id} in module {module_id} by user {current_user.id}")
    return quiz


@router.get(
    "/api/modules/{module_id}/quizzes",
    response_model=List[QuizResponse],
)
def list_quizzes(
    module_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_creator),
) -> List[Quiz]:
    """List all quizzes for a module."""
    module = _get_module_or_404(module_id, db, current_user)
    quizzes = (
        db.query(Quiz)
        .filter(Quiz.module_id == module.id)
        .order_by(Quiz.order_index)
        .all()
    )
    return quizzes


@router.post("/api/quizzes/{quiz_id}/ai/generate-questions")
async def generate_questions(
    quiz_id: int,
    body: AiQuestionRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_creator),
):
    """Stream AI-generated quiz questions from module content. QUIZ-08.

    ROUTE ORDER: Declared before GET /api/quizzes/{quiz_id} to prevent FastAPI
    path collision (same rule as slides.py — STATE.md decision 14-02).
    """
    quiz = _get_quiz_or_404(quiz_id, db, current_user)
    module = quiz.module
    prompt = (
        f"Generate {body.count} quiz questions for a module titled '{module.title}'. "
        f"Description: {module.description or 'no description provided'}. "
        f"Return ONLY a valid JSON array with no extra text. Each element must have: "
        f"type ('mcq_single'|'mcq_multi'|'true_false'|'short_answer'), "
        f"prompt (string), options (string array or null), "
        f"correct_answer (int index for mcq_single, int array for mcq_multi, "
        f"'True'/'False' string for true_false, string or null for short_answer), "
        f"explanation (string). Tone: {body.tone_preset}."
    )

    async def event_generator():
        async for token in claude_service._stream_text(prompt):
            if await request.is_disconnected():
                break
            yield {"data": token}

    return EventSourceResponse(event_generator())


@router.get(
    "/api/quizzes/{quiz_id}",
    response_model=QuizResponse,
)
def get_quiz(
    quiz_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_creator),
) -> Quiz:
    """Get a single quiz by id."""
    return _get_quiz_or_404(quiz_id, db, current_user)


@router.put(
    "/api/quizzes/{quiz_id}",
    response_model=QuizResponse,
)
def update_quiz(
    quiz_id: int,
    body: QuizUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_creator),
) -> Quiz:
    """Partial update of a quiz."""
    quiz = _get_quiz_or_404(quiz_id, db, current_user)

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(quiz, field, value)

    quiz.updated_at = datetime.utcnow()
    _mark_course_changed(quiz.module.course_id, db)
    db.commit()
    db.refresh(quiz)

    logger.info(f"Quiz updated: {quiz.id} by user {current_user.id}")
    return quiz


@router.delete("/api/quizzes/{quiz_id}")
def delete_quiz(
    quiz_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_creator),
) -> dict:
    """Delete a quiz (cascade deletes questions)."""
    quiz = _get_quiz_or_404(quiz_id, db, current_user)

    course_id = quiz.module.course_id
    db.delete(quiz)
    _mark_course_changed(course_id, db)
    db.commit()

    logger.info(f"Quiz deleted: {quiz_id} by user {current_user.id}")
    return {"message": "Quiz deleted"}


# ---------------------------------------------------------------------------
# Question endpoints
# ---------------------------------------------------------------------------

@router.post(
    "/api/quizzes/{quiz_id}/questions",
    response_model=QuestionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_question(
    quiz_id: int,
    body: QuestionCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_creator),
) -> Question:
    """Create a new question in the given quiz."""
    quiz = _get_quiz_or_404(quiz_id, db, current_user)

    max_index = db.query(Question).filter(Question.quiz_id == quiz_id).count()

    question = Question(
        quiz_id=quiz.id,
        order_index=max_index,
        type=body.type,
        prompt=body.prompt,
        points=body.points if body.points is not None else 1,
        explanation=body.explanation,
        options=body.options,
        correct_answer=body.correct_answer,
        difficulty=body.difficulty,
    )
    db.add(question)
    _mark_course_changed(quiz.module.course_id, db)
    db.commit()
    db.refresh(question)

    logger.info(f"Question created: {question.id} in quiz {quiz_id} by user {current_user.id}")
    return question


@router.get(
    "/api/quizzes/{quiz_id}/questions",
    response_model=List[QuestionResponse],
)
def list_questions(
    quiz_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_creator),
) -> List[Question]:
    """List all questions for a quiz, ordered by order_index."""
    quiz = _get_quiz_or_404(quiz_id, db, current_user)
    questions = (
        db.query(Question)
        .filter(Question.quiz_id == quiz.id)
        .order_by(Question.order_index)
        .all()
    )
    return questions


@router.get(
    "/api/questions/{question_id}",
    response_model=QuestionResponse,
)
def get_question(
    question_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_creator),
) -> Question:
    """Get a single question by id."""
    return _get_question_or_404(question_id, db, current_user)


@router.put(
    "/api/questions/{question_id}",
    response_model=QuestionResponse,
)
def update_question(
    question_id: int,
    body: QuestionUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_creator),
) -> Question:
    """Partial update of a question."""
    question = _get_question_or_404(question_id, db, current_user)

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(question, field, value)

    question.updated_at = datetime.utcnow()
    _mark_course_changed(question.quiz.module.course_id, db)
    db.commit()
    db.refresh(question)

    logger.info(f"Question updated: {question.id} by user {current_user.id}")
    return question


@router.delete("/api/questions/{question_id}")
def delete_question(
    question_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_creator),
) -> dict:
    """Delete a question."""
    question = _get_question_or_404(question_id, db, current_user)

    course_id = question.quiz.module.course_id
    db.delete(question)
    _mark_course_changed(course_id, db)
    db.commit()

    logger.info(f"Question deleted: {question_id} by user {current_user.id}")
    return {"message": "Question deleted"}


@router.post("/api/quizzes/{quiz_id}/questions/reorder")
def reorder_questions(
    quiz_id: int,
    body: QuestionReorderRequest,
    db: Session = Depends(get_db),
    current_user=Depends(require_creator),
) -> dict:
    """Atomically reassign order_index for all questions in a single transaction."""
    quiz = _get_quiz_or_404(quiz_id, db, current_user)

    # Validate all ids belong to this quiz in one query
    questions = (
        db.query(Question)
        .filter(
            Question.id.in_(body.question_ids),
            Question.quiz_id == quiz_id,
        )
        .all()
    )
    if len(questions) != len(body.question_ids):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Some question IDs do not belong to this quiz",
        )

    id_to_question = {q.id: q for q in questions}
    for idx, qid in enumerate(body.question_ids):
        id_to_question[qid].order_index = idx

    db.commit()  # single transaction — no order_index drift

    logger.info(f"Questions reordered in quiz {quiz_id} by user {current_user.id}")
    return {"message": "Reordered"}
