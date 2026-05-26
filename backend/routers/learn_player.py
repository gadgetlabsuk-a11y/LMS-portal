"""Learner-facing course player + quiz endpoints (published + enrolled; no answer leaks)."""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session, selectinload

from database import get_db
from models import (User, Course, CourseStatus, Module, Video, Slide, Block,
                    Quiz, Question, Enrollment, QuizAttempt)
from middleware.auth_middleware import get_current_active_user
from services.quiz_grading import score_quiz

router = APIRouter(prefix="/api/learn", tags=["learn-player"])


def _enrollment(db: Session, user_id: int, course_id: int) -> Optional[Enrollment]:
    return (db.query(Enrollment)
            .filter(Enrollment.user_id == user_id, Enrollment.course_id == course_id)
            .first())


def _quiz_json(quiz: Quiz, db: Session, user_id: int) -> Dict[str, Any]:
    attempts = (db.query(QuizAttempt)
                .filter(QuizAttempt.user_id == user_id, QuizAttempt.quiz_id == quiz.id)
                .all())
    best = max((a for a in attempts), key=lambda a: a.score, default=None)
    return {
        "id": quiz.id, "title": quiz.title,
        "pass_rate": quiz.pass_rate, "attempts_allowed": quiz.attempts_allowed,
        "attempts_used": len(attempts),
        "attempts_remaining": max(0, quiz.attempts_allowed - len(attempts)),
        "passed": any(a.passed for a in attempts),
        "last_score": best.score if best else None,
        "questions": [
            {"id": q.id, "type": q.type, "prompt": q.prompt,
             "options": q.options, "points": q.points, "order_index": q.order_index}
            for q in quiz.questions
        ],  # NOTE: correct_answer + explanation intentionally omitted
    }


@router.get("/courses/{course_id}/player")
def get_course_player(course_id: int, db: Session = Depends(get_db),
                      current_user: User = Depends(get_current_active_user)) -> Dict[str, Any]:
    course = (db.query(Course)
              .options(selectinload(Course.modules).selectinload(Module.videos)
                       .selectinload(Video.slides).selectinload(Slide.blocks),
                       selectinload(Course.modules).selectinload(Module.videos)
                       .selectinload(Video.quizzes).selectinload(Quiz.questions))
              .filter(Course.id == course_id).first())
    if not course or course.status != CourseStatus.PUBLISHED:
        raise HTTPException(status_code=404, detail="Course not found")
    enr = _enrollment(db, current_user.id, course_id)
    if not enr:
        raise HTTPException(status_code=403, detail="Not enrolled in this course")

    modules = []
    for m in sorted(course.modules, key=lambda x: x.order_index):
        videos = []
        for v in sorted(m.videos, key=lambda x: x.order_index):
            slides = [
                {"id": s.id, "order_index": s.order_index,
                 "narration_audio_url": s.narration_audio_url,
                 "duration_seconds": s.duration_seconds,
                 "blocks": [{"id": b.id, "type": b.type, "content": b.content,
                             "order_index": b.order_index}
                            for b in sorted(s.blocks, key=lambda x: x.order_index)]}
                for s in sorted(v.slides, key=lambda x: x.order_index)
            ]
            videos.append({"id": v.id, "title": v.title, "order_index": v.order_index,
                           "slides": slides,
                           "quizzes": [_quiz_json(q, db, current_user.id)
                                       for q in sorted(v.quizzes, key=lambda x: x.order_index)]})
        modules.append({"id": m.id, "title": m.title, "order_index": m.order_index, "videos": videos})

    return {"id": course.id, "title": course.title, "progress": int(enr.progress or 0),
            "completed": bool(enr.completed), "modules": modules}


def _quiz_or_404(db: Session, quiz_id: int) -> Quiz:
    quiz = (db.query(Quiz).options(selectinload(Quiz.questions))
            .filter(Quiz.id == quiz_id).first())
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")
    return quiz


@router.get("/quizzes/{quiz_id}")
def get_learner_quiz(quiz_id: int, db: Session = Depends(get_db),
                     current_user: User = Depends(get_current_active_user)) -> Dict[str, Any]:
    quiz = _quiz_or_404(db, quiz_id)
    return _quiz_json(quiz, db, current_user.id)


class AttemptBody(BaseModel):
    answers: Dict[str, Any]


@router.post("/quizzes/{quiz_id}/attempt")
def submit_attempt(quiz_id: int, body: AttemptBody, db: Session = Depends(get_db),
                   current_user: User = Depends(get_current_active_user)) -> Dict[str, Any]:
    quiz = _quiz_or_404(db, quiz_id)
    used = (db.query(QuizAttempt)
            .filter(QuizAttempt.user_id == current_user.id, QuizAttempt.quiz_id == quiz_id).count())
    if used >= quiz.attempts_allowed:
        raise HTTPException(status_code=409, detail="No attempts remaining")

    score, per = score_quiz(quiz.questions, body.answers)
    passed = score >= quiz.pass_rate
    db.add(QuizAttempt(quiz_id=quiz_id, user_id=current_user.id, attempt_number=used + 1,
                       score=score, passed=passed, answers=body.answers,
                       started_at=datetime.now(timezone.utc), submitted_at=datetime.now(timezone.utc)))
    db.commit()

    reveal = quiz.show_feedback in ("immediate", "on_submit") or (quiz.show_feedback == "on_pass" and passed)
    feedback = None
    if reveal:
        feedback = [{"question_id": q.id, "correct": bool(per.get(q.id)),
                     "explanation": q.explanation} for q in quiz.questions]
    return {"score": score, "passed": passed,
            "attempts_remaining": max(0, quiz.attempts_allowed - (used + 1)),
            "feedback": feedback}


class ProgressBody(BaseModel):
    slide_id: int


@router.post("/courses/{course_id}/progress")
def post_progress(course_id: int, body: ProgressBody, db: Session = Depends(get_db),
                  current_user: User = Depends(get_current_active_user)) -> Dict[str, Any]:
    course = (db.query(Course)
              .options(selectinload(Course.modules).selectinload(Module.videos).selectinload(Video.slides))
              .filter(Course.id == course_id).first())
    if not course or course.status != CourseStatus.PUBLISHED:
        raise HTTPException(status_code=404, detail="Course not found")
    enr = _enrollment(db, current_user.id, course_id)
    if not enr:
        raise HTTPException(status_code=403, detail="Not enrolled in this course")

    ordered = [s.id for m in sorted(course.modules, key=lambda x: x.order_index)
               for v in sorted(m.videos, key=lambda x: x.order_index)
               for s in sorted(v.slides, key=lambda x: x.order_index)]
    total = len(ordered) or 1
    if body.slide_id not in ordered:
        raise HTTPException(status_code=404, detail="Slide not in course")
    reached_idx = ordered.index(body.slide_id) + 1            # 1-based furthest reached
    pct = int(reached_idx / total * 100)
    enr.progress = max(float(enr.progress or 0), float(pct))  # monotonic
    if enr.progress >= 100 and not enr.completed:
        enr.completed = True
        enr.completed_at = datetime.now(timezone.utc)
    db.commit(); db.refresh(enr)
    return {"progress": int(enr.progress), "completed": bool(enr.completed)}
