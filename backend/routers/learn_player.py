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
