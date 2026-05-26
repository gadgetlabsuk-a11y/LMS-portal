# Course Player + Quiz Engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A React learner course player that renders relational Module→Video→Slide→Block courses with paged navigation, narration autoplay, progress→completion, and an integrated quiz engine — replacing the legacy placeholder.

**Architecture:** New learner backend endpoints (player tree without answers, progress, quiz fetch/submit) + a new `QuizAttempt` model. A new React `CoursePlayer` renders slides with a **new read‑only block view** (the existing `BlockRenderer` is editor‑only and cannot be reused) and a `QuizRunner` for quizzes; narration autoplay is a shared hook extracted from the broadcast player. `CourseViewerPage` (learner) and `CoursePreviewPage` (creator, read‑only) render it instead of iframing the backend placeholder.

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, pytest; React + TypeScript + Vite + Vitest.

**Spec:** `docs/superpowers/specs/2026-05-26-course-player-design.md`

## Reference facts (verified)
- Models: `Course→Module→Video→Slide→Block`; `Quiz(module_id?,video_id?, pass_rate, attempts_allowed, time_limit_seconds, shuffle_questions, show_feedback, on_fail_action)`; `Question(type, prompt, points, explanation, options JSON, correct_answer JSON)`. `Enrollment(user_id, course_id, progress Float, completed Bool, completed_at)`.
- Question `type` ∈ `mcq_single | mcq_multi | true_false | short_answer`. `correct_answer`: int index (mcq_single), int[] (mcq_multi), "True"/"False" (true_false), string|null (short_answer). `options`: string[]|null.
- Block `content`: text/heading `{html}`, image `{url}`, code `{code}`, quote/list/callout `{text}`, divider none.
- learn router: `routers/learn.py`, `prefix="/api/learn"`, auth `get_current_active_user`; enrollment lookup `db.query(Enrollment).filter(Enrollment.user_id==user.id, Enrollment.course_id==id)`.
- Tree serializer `_serialize_course_tree` exists in `routers/courses.py` but includes `correct_answer` and only module‑level quizzes — the learner endpoint uses its own serializer.
- `CourseViewerPage.tsx` and `CoursePreviewPage.tsx` currently iframe `${API_BASE}/api/courses/{id}/player`.
- Prod note: SQLite has no volume; `init_db()` recreates tables on deploy, so the feature works on the wiped prod DB. Migration 015 keeps the dev chain correct.

---

## File structure
**Backend**
- Modify `backend/models/models.py` — add `QuizAttempt`; export in `backend/models/__init__.py`.
- Create `backend/alembic/versions/015_quiz_attempts.py`.
- Create `backend/services/quiz_grading.py` — pure grading helper.
- Create `backend/routers/learn_player.py` — learner player/progress/quiz endpoints; register in `main.py`.
- Tests: `backend/tests/test_quiz_grading.py`, `backend/tests/test_learn_player.py`.

**Frontend**
- Create `frontend/src/components/player/SlideBlockView.tsx` — read‑only block renderer.
- Create `frontend/src/hooks/useSegmentAutoplay.ts` — extracted autoplay hook.
- Create `frontend/src/components/player/CoursePlayer.tsx` + `frontend/src/components/player/QuizRunner.tsx`.
- Modify `frontend/src/services/coursePlayerApi.ts` (new) — typed client.
- Modify `frontend/src/pages/CourseViewerPage.tsx` and `frontend/src/pages/creator/CoursePreviewPage.tsx` — render `CoursePlayer`.
- Tests: `frontend/src/components/player/__tests__/CoursePlayer.test.tsx`, `QuizRunner.test.tsx`, `SlideBlockView.test.tsx`.

---

## Task 1: QuizAttempt model + migration

**Files:** Modify `backend/models/models.py`, `backend/models/__init__.py`; Create `backend/alembic/versions/015_quiz_attempts.py`.

- [ ] **Step 1: Add the model.** In `backend/models/models.py`, after the `Question` class, add:
```python
class QuizAttempt(Base):
    """A learner's graded attempt at a quiz."""

    __tablename__ = "quiz_attempts"

    id = Column(Integer, primary_key=True, index=True)
    quiz_id = Column(Integer, ForeignKey("quizzes.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    attempt_number = Column(Integer, nullable=False, server_default="1")
    score = Column(Integer, nullable=False, server_default="0")   # percentage 0-100
    passed = Column(Boolean, nullable=False, server_default="0")
    answers = Column(JSON, nullable=True)                          # {question_id: submitted}
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    submitted_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (Index("idx_quiz_attempt_user_quiz", "user_id", "quiz_id"),)
```

- [ ] **Step 2: Export it.** In `backend/models/__init__.py`, add `QuizAttempt` to both the `from .models import (...)` block and `__all__` (mirror how `IntegrationSettings` is listed).

- [ ] **Step 3: Migration.** Create `backend/alembic/versions/015_quiz_attempts.py`:
```python
"""Add quiz_attempts (learner quiz scoring).

Revision ID: 015
Revises: 014
Create Date: 2026-05-26
"""
from alembic import op
import sqlalchemy as sa

revision = '015'
down_revision = '014'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'quiz_attempts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('quiz_id', sa.Integer(), sa.ForeignKey('quizzes.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('attempt_number', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('score', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('passed', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('answers', sa.JSON(), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=False),
        sa.Column('submitted_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_quiz_attempt_user_quiz', 'quiz_attempts', ['user_id', 'quiz_id'])


def downgrade() -> None:
    op.drop_index('idx_quiz_attempt_user_quiz', table_name='quiz_attempts')
    op.drop_table('quiz_attempts')
```

- [ ] **Step 4: Verify.** Run: `cd backend && source venv/bin/activate && python -c "from models import QuizAttempt; print(QuizAttempt.__tablename__, [c.name for c in QuizAttempt.__table__.columns])"` — expect `quiz_attempts [...]` including `score`, `passed`, `answers`.

- [ ] **Step 5: Commit.**
```bash
git add backend/models/models.py backend/models/__init__.py backend/alembic/versions/015_quiz_attempts.py
git commit -m "feat(player): QuizAttempt model + migration 015"
```

---

## Task 2: Quiz grading service

**Files:** Create `backend/services/quiz_grading.py`; Test `backend/tests/test_quiz_grading.py`.

- [ ] **Step 1: Failing tests.** Create `backend/tests/test_quiz_grading.py`:
```python
from services.quiz_grading import grade_question, score_quiz


def q(type, correct, points=1):
    class Q: pass
    o = Q(); o.type = type; o.correct_answer = correct; o.points = points; o.id = 1
    return o


def test_mcq_single():
    assert grade_question(q("mcq_single", 2), 2) is True
    assert grade_question(q("mcq_single", 2), 1) is False


def test_mcq_multi_order_insensitive():
    assert grade_question(q("mcq_multi", [0, 2]), [2, 0]) is True
    assert grade_question(q("mcq_multi", [0, 2]), [0]) is False


def test_true_false():
    assert grade_question(q("true_false", "True"), "True") is True
    assert grade_question(q("true_false", "True"), "False") is False


def test_short_answer_normalized():
    assert grade_question(q("short_answer", "Paris"), " paris ") is True
    assert grade_question(q("short_answer", "Paris"), "London") is False


def test_blank_is_incorrect():
    assert grade_question(q("mcq_single", 2), None) is False


def test_score_quiz_percentage_and_pass():
    questions = [q("mcq_single", 0, points=1), q("mcq_single", 1, points=3)]
    questions[0].id, questions[1].id = 10, 11
    # got the 3-point one right, the 1-point one wrong -> 3/4 = 75%
    score, per = score_quiz(questions, {10: 1, 11: 1})
    assert score == 75
    assert per[10] is False and per[11] is True
```

- [ ] **Step 2: Run — expect ImportError.** `cd backend && source venv/bin/activate && python -m pytest tests/test_quiz_grading.py -q`

- [ ] **Step 3: Implement.** Create `backend/services/quiz_grading.py`:
```python
"""Pure, network-free grading for learner quiz attempts."""
from typing import Any, Tuple


def grade_question(question, submitted: Any) -> bool:
    """True if `submitted` is correct for `question.type` / `question.correct_answer`."""
    correct = question.correct_answer
    t = question.type
    if submitted is None or correct is None:
        return False
    if t == "mcq_single":
        return submitted == correct
    if t == "mcq_multi":
        try:
            return set(submitted) == set(correct)
        except TypeError:
            return False
    if t == "true_false":
        return str(submitted).strip().lower() == str(correct).strip().lower()
    if t == "short_answer":
        return str(submitted).strip().lower() == str(correct).strip().lower()
    return False


def score_quiz(questions, answers: dict) -> Tuple[int, dict]:
    """Return (percentage 0-100, {question_id: bool correct}).

    `answers` keys may be ints or strings (JSON object keys are strings); both are tried.
    """
    total = sum(max(1, q.points) for q in questions) or 1
    earned = 0
    per: dict = {}
    for q in questions:
        submitted = answers.get(q.id, answers.get(str(q.id)))
        ok = grade_question(q, submitted)
        per[q.id] = ok
        if ok:
            earned += max(1, q.points)
    return round(earned / total * 100), per
```

- [ ] **Step 4: Run — expect 6 passed.** `python -m pytest tests/test_quiz_grading.py -q`

- [ ] **Step 5: Commit.**
```bash
git add backend/services/quiz_grading.py backend/tests/test_quiz_grading.py
git commit -m "feat(player): pure quiz grading service"
```

---

## Task 3: Learner player-data endpoint

**Files:** Create `backend/routers/learn_player.py`; Modify `backend/main.py` (register router); Test `backend/tests/test_learn_player.py`.

- [ ] **Step 1: Failing test.** Create `backend/tests/test_learn_player.py`:
```python
import pytest
from fastapi.testclient import TestClient
from main import app
from models import Course, CourseStatus, Module, Video, Slide, Block, Quiz, Question, Enrollment

client = TestClient(app)


def _published_course_with_content(db, owner_id):
    c = Course(title="Player Course", creator_id=owner_id, status=CourseStatus.PUBLISHED)
    db.add(c); db.flush()
    m = Module(course_id=c.id, title="M1", order_index=0); db.add(m); db.flush()
    v = Video(module_id=m.id, title="V1", order_index=0); db.add(v); db.flush()
    s = Slide(video_id=v.id, order_index=0); db.add(s); db.flush()
    db.add(Block(slide_id=s.id, order_index=0, type="heading", content={"html": "<h1>Hi</h1>"}))
    quiz = Quiz(video_id=v.id, title="Q", pass_rate=50, attempts_allowed=2); db.add(quiz); db.flush()
    db.add(Question(quiz_id=quiz.id, order_index=0, type="mcq_single", prompt="2+2?",
                    options=["3", "4"], correct_answer=1, points=1))
    db.commit()
    return c, v, quiz


def test_player_requires_enrollment(db, trainee_user, trainee_token):
    c, v, quiz = _published_course_with_content(db, trainee_user.id)
    r = client.get(f"/api/learn/courses/{c.id}/player",
                   headers={"Authorization": f"Bearer {trainee_token}"})
    assert r.status_code == 403


def test_player_tree_strips_answers(db, trainee_user, trainee_token):
    c, v, quiz = _published_course_with_content(db, trainee_user.id)
    db.add(Enrollment(user_id=trainee_user.id, course_id=c.id)); db.commit()
    r = client.get(f"/api/learn/courses/{c.id}/player",
                   headers={"Authorization": f"Bearer {trainee_token}"})
    assert r.status_code == 200
    body = r.json()
    q = body["modules"][0]["videos"][0]["quizzes"][0]["questions"][0]
    assert "correct_answer" not in q and "explanation" not in q
    assert q["options"] == ["3", "4"]
    assert body["progress"] == 0
```

(The `db`, `trainee_user`, `trainee_token` fixtures exist in `tests/conftest.py`.)

- [ ] **Step 2: Run — expect 404 (route missing).** `python -m pytest tests/test_learn_player.py -q`

- [ ] **Step 3: Implement the router.** Create `backend/routers/learn_player.py`:
```python
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


def _slides_total(course: Course) -> int:
    return sum(len(v.slides) for m in course.modules for v in m.videos)


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
```

- [ ] **Step 4: Register the router.** In `backend/main.py`, add `learn_player` to the `from routers import (...)` line and add `app.include_router(learn_player.router)` next to the other `include_router` calls.

- [ ] **Step 5: Run — expect 2 passed.** `python -m pytest tests/test_learn_player.py -q`

- [ ] **Step 6: Commit.**
```bash
git add backend/routers/learn_player.py backend/main.py backend/tests/test_learn_player.py
git commit -m "feat(player): learner course-player data endpoint (enrolled, answers stripped)"
```

---

## Task 4: Progress + completion endpoint

**Files:** Modify `backend/routers/learn_player.py`; append to `backend/tests/test_learn_player.py`.

- [ ] **Step 1: Failing test.** Append to `tests/test_learn_player.py`:
```python
def test_progress_updates_and_completes(db, trainee_user, trainee_token):
    c, v, quiz = _published_course_with_content(db, trainee_user.id)
    db.add(Enrollment(user_id=trainee_user.id, course_id=c.id)); db.commit()
    h = {"Authorization": f"Bearer {trainee_token}"}
    s_id = v.slides[0].id
    r = client.post(f"/api/learn/courses/{c.id}/progress", json={"slide_id": s_id}, headers=h)
    assert r.status_code == 200
    body = r.json()
    assert body["progress"] == 100 and body["completed"] is True  # only 1 slide -> done
```

- [ ] **Step 2: Run — expect failure (route missing).**

- [ ] **Step 3: Implement.** In `backend/routers/learn_player.py` add:
```python
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
```

- [ ] **Step 4: Run — expect pass.** `python -m pytest tests/test_learn_player.py -q`

- [ ] **Step 5: Commit.**
```bash
git add backend/routers/learn_player.py backend/tests/test_learn_player.py
git commit -m "feat(player): progress endpoint with monotonic progress + completion"
```

---

## Task 5: Learner quiz fetch + submit/score endpoints

**Files:** Modify `backend/routers/learn_player.py`; append tests.

- [ ] **Step 1: Failing tests.** Append to `tests/test_learn_player.py`:
```python
def test_quiz_get_hides_answers(db, trainee_user, trainee_token):
    c, v, quiz = _published_course_with_content(db, trainee_user.id)
    db.add(Enrollment(user_id=trainee_user.id, course_id=c.id)); db.commit()
    r = client.get(f"/api/learn/quizzes/{quiz.id}", headers={"Authorization": f"Bearer {trainee_token}"})
    assert r.status_code == 200
    assert "correct_answer" not in r.json()["questions"][0]
    assert r.json()["attempts_remaining"] == 2


def test_quiz_submit_scores_and_limits(db, trainee_user, trainee_token):
    c, v, quiz = _published_course_with_content(db, trainee_user.id)
    db.add(Enrollment(user_id=trainee_user.id, course_id=c.id)); db.commit()
    h = {"Authorization": f"Bearer {trainee_token}"}
    qid = quiz.questions[0].id
    r = client.post(f"/api/learn/quizzes/{quiz.id}/attempt", json={"answers": {str(qid): 1}}, headers=h)
    assert r.status_code == 200
    assert r.json()["score"] == 100 and r.json()["passed"] is True
    # second wrong attempt
    client.post(f"/api/learn/quizzes/{quiz.id}/attempt", json={"answers": {str(qid): 0}}, headers=h)
    # third should 409 (attempts_allowed=2)
    r3 = client.post(f"/api/learn/quizzes/{quiz.id}/attempt", json={"answers": {str(qid): 1}}, headers=h)
    assert r3.status_code == 409
```

- [ ] **Step 2: Run — expect failure.**

- [ ] **Step 3: Implement.** In `backend/routers/learn_player.py` add:
```python
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
```

- [ ] **Step 4: Run — expect pass.** `python -m pytest tests/test_learn_player.py tests/test_quiz_grading.py -q`

- [ ] **Step 5: Commit.**
```bash
git add backend/routers/learn_player.py backend/tests/test_learn_player.py
git commit -m "feat(player): learner quiz fetch + scored submit with attempt limit + feedback gating"
```

---

## Task 6: Read-only slide block view (frontend)

**Files:** Create `frontend/src/components/player/SlideBlockView.tsx`; Test `frontend/src/components/player/__tests__/SlideBlockView.test.tsx`.

- [ ] **Step 1: Failing test.** Create the test:
```tsx
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { SlideBlockView } from '../SlideBlockView'

describe('SlideBlockView', () => {
  it('renders heading html', () => {
    render(<SlideBlockView block={{ id: 1, type: 'heading', content: { html: '<h1>Hello</h1>' }, order_index: 0 }} />)
    expect(screen.getByText('Hello')).toBeInTheDocument()
  })
  it('renders image url', () => {
    render(<SlideBlockView block={{ id: 2, type: 'image', content: { url: 'http://x/y.png' }, order_index: 0 }} />)
    expect(screen.getByRole('img')).toHaveAttribute('src', 'http://x/y.png')
  })
  it('renders unknown type as text without crashing', () => {
    render(<SlideBlockView block={{ id: 3, type: 'callout', content: { text: 'Note!' }, order_index: 0 }} />)
    expect(screen.getByText('Note!')).toBeInTheDocument()
  })
})
```

- [ ] **Step 2: Run — expect fail (module missing).** `cd frontend && npx vitest run src/components/player/__tests__/SlideBlockView.test.tsx`

- [ ] **Step 3: Implement.** Create `frontend/src/components/player/SlideBlockView.tsx`:
```tsx
export interface PlayerBlock {
  id: number
  type: string
  content: Record<string, unknown> | null
  order_index: number
}

export function SlideBlockView({ block }: { block: PlayerBlock }) {
  const c = (block.content || {}) as Record<string, unknown>
  switch (block.type) {
    case 'heading':
    case 'text':
      return <div className="prose max-w-none text-gray-100" dangerouslySetInnerHTML={{ __html: String(c.html ?? '') }} />
    case 'image':
      return c.url ? <img src={String(c.url)} alt={String(c.alt ?? '')} className="max-w-full rounded" /> : null
    case 'code':
      return <pre className="bg-gray-900 text-green-400 text-sm p-3 rounded overflow-auto"><code>{String(c.code ?? '')}</code></pre>
    case 'quote':
      return <blockquote className="border-l-4 border-indigo-400 pl-4 italic text-gray-200">{String(c.text ?? '')}</blockquote>
    case 'callout':
      return <div className="bg-amber-100 text-amber-900 rounded p-3">{String(c.text ?? '')}</div>
    case 'list': {
      const items = Array.isArray(c.items) ? (c.items as unknown[]) : String(c.text ?? '').split('\n').filter(Boolean)
      return <ul className="list-disc pl-6 text-gray-100">{items.map((it, i) => <li key={i}>{String(it)}</li>)}</ul>
    }
    case 'video':
      return c.url ? <video controls src={String(c.url)} className="max-w-full rounded" /> : null
    case 'divider':
      return <hr className="border-gray-600 my-4" />
    default:
      return <p className="text-gray-100">{String(c.text ?? c.html ?? '')}</p>
  }
}
```
Note: `dangerouslySetInnerHTML` renders TipTap-authored HTML produced by creators within this app (trusted authoring), consistent with how the editor stores `{html}`.

- [ ] **Step 4: Run — expect 3 passed.**

- [ ] **Step 5: Commit.**
```bash
git add frontend/src/components/player/SlideBlockView.tsx frontend/src/components/player/__tests__/SlideBlockView.test.tsx
git commit -m "feat(player): read-only SlideBlockView for the 9 block types"
```

---

## Task 7: Extract the narration autoplay hook

**Files:** Create `frontend/src/hooks/useSegmentAutoplay.ts`; Modify `frontend/src/pages/learn/ILBPlayerPage.tsx` to use it; existing ILB test must still pass.

- [ ] **Step 1: Implement the hook** (lifts the logic already in `ILBPlayerPage`). Create `frontend/src/hooks/useSegmentAutoplay.ts`:
```tsx
import { useEffect, useRef } from 'react'

/** Drives one <audio>/<video> element: play while `playing`, pause otherwise, and
 *  advance via the returned onEnded handler; timer fallback when there's no media URL. */
export function useSegmentAutoplay(opts: {
  playing: boolean
  index: number
  mediaUrl: string | null
  text: string | null
  isLast: boolean
  onAdvance: () => void
  enableTimer?: boolean   // default true (broadcast). Course player sets false: no-audio slides wait for Next.
}) {
  const ref = useRef<HTMLMediaElement | null>(null)
  const enableTimer = opts.enableTimer !== false

  useEffect(() => {
    const el = ref.current
    if (!el) return
    if (opts.playing) void el.play().catch(() => {})
    else el.pause()
  }, [opts.playing, opts.index, opts.mediaUrl])

  useEffect(() => {
    if (!enableTimer || !opts.playing || opts.mediaUrl || opts.isLast) return
    const words = (opts.text ?? '').trim().split(/\s+/).filter(Boolean).length
    const seconds = Math.min(20, Math.max(6, words / 2.5))
    const t = setTimeout(opts.onAdvance, seconds * 1000)
    return () => clearTimeout(t)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [opts.playing, opts.mediaUrl, opts.text, opts.index, opts.isLast])

  const onEnded = () => { if (opts.playing && !opts.isLast) opts.onAdvance() }
  return { ref, onEnded }
}
```

- [ ] **Step 2: Refactor `ILBPlayerPage.tsx`** to use the hook in place of its inline `mediaRef`/play-pause effect/timer effect/`handleSegmentEnded`:
  - Replace the `mediaRef` + the two effects + `handleSegmentEnded`/`advanceSegment` wiring with:
    ```tsx
    const { ref: mediaRef, onEnded: handleSegmentEnded } = useSegmentAutoplay({
      playing: state === 'playing', index: segIdx,
      mediaUrl: currentVideo || currentAudio, text: currentSegment,
      isLast: segIdx >= segments.length - 1,
      onAdvance: advanceSegment,
    })
    ```
    Keep `advanceSegment` (it still flushes the defer queue). Keep the `<video>/<audio> ref={mediaRef} onEnded={handleSegmentEnded}` usage.
  - Remove the now-duplicated inline effects.

- [ ] **Step 3: Run the ILB player test — must still pass.** `cd frontend && npx vitest run src/pages/learn/__tests__/ILBPlayerPage.test.tsx` and `npx tsc -b`.

- [ ] **Step 4: Commit.**
```bash
git add frontend/src/hooks/useSegmentAutoplay.ts frontend/src/pages/learn/ILBPlayerPage.tsx
git commit -m "refactor(ilb): extract useSegmentAutoplay hook (shared by broadcast + course players)"
```

---

## Task 8: Course-player API client

**Files:** Create `frontend/src/services/coursePlayerApi.ts`.

- [ ] **Step 1: Implement.** Create `frontend/src/services/coursePlayerApi.ts`:
```tsx
import { api } from './api'

async function unwrap<T>(r: Response): Promise<T> {
  if (!r.ok) throw new Error((await r.json().catch(() => ({}))).detail || `Request failed (${r.status})`)
  return r.json() as Promise<T>
}

export interface PlayerQuestion { id: number; type: string; prompt: string; options: string[] | null; points: number; order_index: number }
export interface PlayerQuiz { id: number; title: string; pass_rate: number; attempts_allowed: number; attempts_remaining: number; attempts_used: number; passed: boolean; last_score: number | null; questions: PlayerQuestion[] }
export interface PlayerSlide { id: number; order_index: number; narration_audio_url: string | null; duration_seconds: number | null; blocks: { id: number; type: string; content: Record<string, unknown> | null; order_index: number }[] }
export interface PlayerVideo { id: number; title: string; order_index: number; slides: PlayerSlide[]; quizzes: PlayerQuiz[] }
export interface PlayerModule { id: number; title: string; order_index: number; videos: PlayerVideo[] }
export interface PlayerCourse { id: number; title: string; progress: number; completed: boolean; modules: PlayerModule[] }
export interface AttemptResult { score: number; passed: boolean; attempts_remaining: number; feedback: { question_id: number; correct: boolean; explanation: string | null }[] | null }

export const coursePlayerApi = {
  getLearnerPlayer: (id: number) => api.get(`/learn/courses/${id}/player`).then((r) => unwrap<PlayerCourse>(r)),
  getPreviewTree: (id: number) => api.get(`/courses/${id}/preview`).then((r) => unwrap<PlayerCourse>(r)),
  postProgress: (id: number, slideId: number) => api.post(`/learn/courses/${id}/progress`, { slide_id: slideId }).then((r) => unwrap<{ progress: number; completed: boolean }>(r)),
  getQuiz: (quizId: number) => api.get(`/learn/quizzes/${quizId}`).then((r) => unwrap<PlayerQuiz>(r)),
  submitAttempt: (quizId: number, answers: Record<string, unknown>) => api.post(`/learn/quizzes/${quizId}/attempt`, { answers }).then((r) => unwrap<AttemptResult>(r)),
}
```
Note: the creator `/courses/{id}/preview` tree has a slightly different shape (module-level quizzes, includes answers); the player treats preview as read-only and only needs slides/blocks from it — `QuizRunner` is not submitted in preview mode (Task 11). `PlayerCourse` typing is best-effort for preview.

- [ ] **Step 2: Typecheck.** `cd frontend && npx tsc -b` (expect 0).

- [ ] **Step 3: Commit.**
```bash
git add frontend/src/services/coursePlayerApi.ts
git commit -m "feat(player): typed course-player API client"
```

---

## Task 9: QuizRunner component

**Files:** Create `frontend/src/components/player/QuizRunner.tsx`; Test `__tests__/QuizRunner.test.tsx`.

- [ ] **Step 1: Failing test.** Create `frontend/src/components/player/__tests__/QuizRunner.test.tsx`:
```tsx
import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QuizRunner } from '../QuizRunner'
import { coursePlayerApi } from '@/services/coursePlayerApi'

vi.mock('@/services/coursePlayerApi', () => ({ coursePlayerApi: { submitAttempt: vi.fn() } }))
const mocked = coursePlayerApi as unknown as Record<string, ReturnType<typeof vi.fn>>

const quiz = { id: 1, title: 'Q', pass_rate: 50, attempts_allowed: 3, attempts_remaining: 3, attempts_used: 0, passed: false, last_score: null,
  questions: [{ id: 9, type: 'mcq_single', prompt: '2+2?', options: ['3', '4'], points: 1, order_index: 0 }] }

describe('QuizRunner', () => {
  it('submits and shows pass result', async () => {
    mocked.submitAttempt.mockResolvedValue({ score: 100, passed: true, attempts_remaining: 2, feedback: null })
    render(<QuizRunner quiz={quiz} onPassed={vi.fn()} />)
    await userEvent.click(screen.getByLabelText('4'))
    await userEvent.click(screen.getByText('Submit'))
    expect(await screen.findByText(/Passed/i)).toBeInTheDocument()
    expect(mocked.submitAttempt).toHaveBeenCalledWith(1, { '9': 1 })
  })
})
```

- [ ] **Step 2: Run — expect fail.**

- [ ] **Step 3: Implement.** Create `frontend/src/components/player/QuizRunner.tsx`:
```tsx
import { useState } from 'react'
import { coursePlayerApi, type PlayerQuiz, type AttemptResult } from '@/services/coursePlayerApi'

export function QuizRunner({ quiz, onPassed }: { quiz: PlayerQuiz; onPassed: () => void }) {
  const [answers, setAnswers] = useState<Record<string, unknown>>({})
  const [result, setResult] = useState<AttemptResult | null>(null)
  const [remaining, setRemaining] = useState(quiz.attempts_remaining)
  const [busy, setBusy] = useState(false)

  const setSingle = (qid: number, idx: number) => setAnswers((a) => ({ ...a, [qid]: idx }))
  const toggleMulti = (qid: number, idx: number) => setAnswers((a) => {
    const cur = Array.isArray(a[qid]) ? (a[qid] as number[]) : []
    return { ...a, [qid]: cur.includes(idx) ? cur.filter((x) => x !== idx) : [...cur, idx] }
  })

  const submit = async () => {
    setBusy(true)
    try {
      const res = await coursePlayerApi.submitAttempt(quiz.id, answers)
      setResult(res); setRemaining(res.attempts_remaining)
      if (res.passed) onPassed()
    } finally { setBusy(false) }
  }

  if (result) {
    return (
      <div className="max-w-2xl mx-auto p-6 text-center text-gray-100">
        <h3 className="text-xl font-bold mb-2">{result.passed ? 'Passed ✓' : 'Not passed'}</h3>
        <p className="mb-4">Score: {result.score}% (pass mark {quiz.pass_rate}%)</p>
        {!result.passed && remaining > 0 && (
          <button onClick={() => { setResult(null); setAnswers({}) }} className="px-4 py-2 rounded bg-indigo-600 text-white">
            Retake ({remaining} left)
          </button>
        )}
        {!result.passed && remaining === 0 && <p className="text-amber-400">No attempts remaining.</p>}
      </div>
    )
  }

  return (
    <div className="max-w-2xl mx-auto p-6 text-gray-100">
      <h3 className="text-xl font-bold mb-4">{quiz.title}</h3>
      {quiz.questions.map((q) => (
        <div key={q.id} className="mb-5">
          <p className="font-medium mb-2">{q.prompt}</p>
          {(q.options ?? []).map((opt, idx) => (
            <label key={idx} className="flex items-center gap-2 mb-1">
              <input
                type={q.type === 'mcq_multi' ? 'checkbox' : 'radio'}
                name={`q-${q.id}`}
                aria-label={opt}
                onChange={() => (q.type === 'mcq_multi' ? toggleMulti(q.id, idx) : setSingle(q.id, idx))}
              />
              {opt}
            </label>
          ))}
          {q.type === 'true_false' && (q.options == null) && (
            ['True', 'False'].map((tf) => (
              <label key={tf} className="flex items-center gap-2 mb-1">
                <input type="radio" name={`q-${q.id}`} aria-label={tf} onChange={() => setAnswers((a) => ({ ...a, [q.id]: tf }))} />
                {tf}
              </label>
            ))
          )}
        </div>
      ))}
      <button onClick={() => void submit()} disabled={busy} className="px-5 py-2 rounded bg-indigo-600 text-white disabled:opacity-50">
        {busy ? 'Submitting…' : 'Submit'}
      </button>
    </div>
  )
}
```

- [ ] **Step 4: Run — expect pass.** `npx vitest run src/components/player/__tests__/QuizRunner.test.tsx` and `npx tsc -b`.

- [ ] **Step 5: Commit.**
```bash
git add frontend/src/components/player/QuizRunner.tsx frontend/src/components/player/__tests__/QuizRunner.test.tsx
git commit -m "feat(player): QuizRunner (render/submit/score/retake)"
```

---

## Task 10: CoursePlayer component

**Files:** Create `frontend/src/components/player/CoursePlayer.tsx`; Test `__tests__/CoursePlayer.test.tsx`.

- [ ] **Step 1: Failing test.** Create `frontend/src/components/player/__tests__/CoursePlayer.test.tsx`:
```tsx
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { CoursePlayer } from '../CoursePlayer'
import { coursePlayerApi } from '@/services/coursePlayerApi'

vi.mock('@/services/api', () => ({ API_BASE: '' }))
vi.mock('@/services/coursePlayerApi', () => ({ coursePlayerApi: { getLearnerPlayer: vi.fn(), getPreviewTree: vi.fn(), postProgress: vi.fn().mockResolvedValue({ progress: 100, completed: true }) } }))
const mocked = coursePlayerApi as unknown as Record<string, ReturnType<typeof vi.fn>>

const course = { id: 1, title: 'C', progress: 0, completed: false, modules: [
  { id: 1, title: 'M', order_index: 0, videos: [
    { id: 1, title: 'V', order_index: 0, quizzes: [], slides: [
      { id: 10, order_index: 0, narration_audio_url: null, duration_seconds: null, blocks: [{ id: 1, type: 'heading', content: { html: '<h2>Slide A</h2>' }, order_index: 0 }] },
      { id: 11, order_index: 1, narration_audio_url: null, duration_seconds: null, blocks: [{ id: 2, type: 'text', content: { html: '<p>Slide B</p>' }, order_index: 0 }] },
    ] },
  ] },
] }

describe('CoursePlayer', () => {
  beforeEach(() => vi.clearAllMocks())
  it('renders first slide and advances on Next', async () => {
    mocked.getLearnerPlayer.mockResolvedValue(course)
    render(<CoursePlayer courseId={1} mode="learner" />)
    expect(await screen.findByText('Slide A')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: /next/i }))
    expect(await screen.findByText('Slide B')).toBeInTheDocument()
  })
  it('preview mode never posts progress', async () => {
    mocked.getPreviewTree.mockResolvedValue(course)
    render(<CoursePlayer courseId={1} mode="preview" />)
    await screen.findByText('Slide A')
    await userEvent.click(screen.getByRole('button', { name: /next/i }))
    await screen.findByText('Slide B')
    expect(mocked.postProgress).not.toHaveBeenCalled()
  })
})
```

- [ ] **Step 2: Run — expect fail.**

- [ ] **Step 3: Implement.** Create `frontend/src/components/player/CoursePlayer.tsx`:
```tsx
import { useEffect, useMemo, useState } from 'react'
import { API_BASE } from '@/services/api'
import { coursePlayerApi, type PlayerCourse, type PlayerSlide, type PlayerQuiz } from '@/services/coursePlayerApi'
import { useSegmentAutoplay } from '@/hooks/useSegmentAutoplay'
import { SlideBlockView } from './SlideBlockView'
import { QuizRunner } from './QuizRunner'

type Step = { kind: 'slide'; slide: PlayerSlide } | { kind: 'quiz'; quiz: PlayerQuiz }

export function CoursePlayer({ courseId, mode }: { courseId: number; mode: 'learner' | 'preview' }) {
  const [course, setCourse] = useState<PlayerCourse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [idx, setIdx] = useState(0)
  const [playing, setPlaying] = useState(true)

  useEffect(() => {
    const load = mode === 'learner' ? coursePlayerApi.getLearnerPlayer(courseId) : coursePlayerApi.getPreviewTree(courseId)
    load.then(setCourse).catch((e) => setError(e instanceof Error ? e.message : 'Failed to load course'))
  }, [courseId, mode])

  // Flatten into an ordered list of steps: each video's slides, then its quiz (if any).
  const steps: Step[] = useMemo(() => {
    if (!course) return []
    const out: Step[] = []
    for (const m of course.modules)
      for (const v of m.videos) {
        for (const s of v.slides) out.push({ kind: 'slide', slide: s })
        for (const q of v.quizzes || []) out.push({ kind: 'quiz', quiz: q })
      }
    return out
  }, [course])

  const step = steps[Math.min(idx, steps.length - 1)]
  const slideStep = step && step.kind === 'slide' ? step.slide : null
  const isLast = idx >= steps.length - 1

  const advance = () => setIdx((i) => Math.min(steps.length - 1, i + 1))
  const { ref: mediaRef, onEnded } = useSegmentAutoplay({
    playing, index: idx, mediaUrl: slideStep?.narration_audio_url ?? null,
    text: null, isLast, onAdvance: advance,
    enableTimer: false,   // course slides without audio wait for Next; audio slides advance on end
  })

  // Learner progress: report the furthest slide reached.
  useEffect(() => {
    if (mode !== 'learner' || !slideStep) return
    void coursePlayerApi.postProgress(courseId, slideStep.id).catch(() => {})
  }, [mode, courseId, slideStep?.id])

  if (error) return <div className="min-h-screen flex items-center justify-center bg-gray-900 text-gray-300">{error}</div>
  if (!course) return <div className="min-h-screen flex items-center justify-center bg-gray-900 text-gray-400">Loading…</div>
  if (steps.length === 0) return <div className="min-h-screen flex items-center justify-center bg-gray-900 text-gray-300">This course has no content yet.</div>

  return (
    <div className="min-h-screen flex flex-col bg-gray-900 text-gray-100">
      <div className="bg-gray-800 px-6 py-2 text-xs text-gray-400 flex justify-between">
        <span>{course.title}{mode === 'preview' && ' · preview'}</span>
        <span>Step {idx + 1} / {steps.length}</span>
      </div>
      <div className="flex-1 flex flex-col items-center justify-center p-6 gap-4">
        {step.kind === 'slide' ? (
          <div className="w-full max-w-3xl space-y-3">
            {step.slide.blocks.map((b) => <SlideBlockView key={b.id} block={b} />)}
            {step.slide.narration_audio_url && (
              <audio key={`a-${idx}`} ref={mediaRef as React.RefObject<HTMLAudioElement>} controls onEnded={onEnded}
                     src={`${API_BASE}${step.slide.narration_audio_url}`} className="w-full mt-2" />
            )}
          </div>
        ) : (
          <QuizRunner quiz={step.quiz} onPassed={advance} />
        )}
      </div>
      <div className="bg-gray-800 px-6 py-3 flex items-center justify-center gap-3">
        <button onClick={() => setIdx((i) => Math.max(0, i - 1))} disabled={idx === 0}
                className="px-3 py-2 rounded bg-gray-700 disabled:opacity-40 text-sm">◀ Prev</button>
        {slideStep && (
          <button onClick={() => setPlaying((p) => !p)} className="px-3 py-2 rounded bg-gray-700 text-sm">
            {playing ? 'Pause' : 'Play'}
          </button>
        )}
        <button onClick={advance} disabled={isLast || step.kind === 'quiz'}
                className="px-4 py-2 rounded bg-indigo-600 disabled:opacity-40 text-sm">Next ▶</button>
        {isLast && <span className="text-emerald-400 text-sm ml-2">End of course</span>}
      </div>
    </div>
  )
}
```
(Quiz steps disable plain "Next" — the learner advances by passing, via `QuizRunner.onPassed`.)

- [ ] **Step 4: Run — expect 2 passed.** `npx vitest run src/components/player/__tests__/CoursePlayer.test.tsx` and `npx tsc -b`.

- [ ] **Step 5: Commit.**
```bash
git add frontend/src/components/player/CoursePlayer.tsx frontend/src/components/player/__tests__/CoursePlayer.test.tsx
git commit -m "feat(player): CoursePlayer (slides + quiz steps, narration autoplay, progress)"
```

---

## Task 11: Wire CoursePlayer into the viewer + preview pages

**Files:** Modify `frontend/src/pages/CourseViewerPage.tsx`, `frontend/src/pages/creator/CoursePreviewPage.tsx`.

- [ ] **Step 1: Learner viewer.** Replace the `<iframe>` body of `CourseViewerPage.tsx` with the React player:
```tsx
import { useParams } from 'react-router-dom'
import { CoursePlayer } from '@/components/player/CoursePlayer'

export const CourseViewerPage = () => {
  const { id } = useParams<{ id: string }>()
  return <CoursePlayer courseId={Number(id)} mode="learner" />
}
```

- [ ] **Step 2: Creator preview.** In `CoursePreviewPage.tsx`, replace the `<iframe src=.../player>` with `<CoursePlayer courseId={Number(id)} mode="preview" />` (keep the page's existing exit/back chrome + watermark). Import `CoursePlayer`.

- [ ] **Step 3: Typecheck + existing tests.** `cd frontend && npx tsc -b && npx vitest run src/components/player src/pages/learn`.

- [ ] **Step 4: Commit.**
```bash
git add frontend/src/pages/CourseViewerPage.tsx frontend/src/pages/creator/CoursePreviewPage.tsx
git commit -m "feat(player): render CoursePlayer in learner viewer + creator preview (replaces placeholder)"
```

---

## Task 12: Full verification + deploy

- [ ] **Step 1: Backend suite.** `cd backend && source venv/bin/activate && python -m pytest tests/test_quiz_grading.py tests/test_learn_player.py tests/test_ilb_router.py -q` — all pass.
- [ ] **Step 2: Frontend.** `cd frontend && npx tsc -b && npx vitest run src/components/player src/pages/learn src/pages/admin` — tsc 0, tests pass.
- [ ] **Step 3: Push.** `git push origin <branch>` (or merge to main per the finishing-a-development-branch flow).
- [ ] **Step 4: Deploy** backend + frontend via Coolify (uuids backend `grezgrjpzsiy1x1aqlqu4yml`, frontend `dta9d9jm5k5tb94wnomxfxps`); wait for both `finished`.
- [ ] **Step 5: Live check.** As admin/creator: build a course with a slide (heading+text) and a video quiz (1 mcq_single), publish. As an enrolled learner: open the course → slides render and Next advances → quiz shows → submit → pass → reaches "End of course" and the enrollment shows completed. Creator preview renders read-only (no progress writes).

---

## Notes for the executor
- `BlockRenderer` (editor) is NOT reused — `SlideBlockView` (Task 6) is the read-only renderer. This corrects the spec's "reuse BlockRenderer" line.
- The learner endpoints live in a NEW `routers/learn_player.py` (not the existing `routers/learn.py`) to keep the player surface focused; both share `prefix="/api/learn"` — ensure no path collisions (paths used here: `/courses/{id}/player`, `/courses/{id}/progress`, `/quizzes/{id}`, `/quizzes/{id}/attempt` — none exist in `learn.py`).
- Preview uses the creator `/courses/{id}/preview` tree (module-level quizzes, includes answers) and is read-only; `QuizRunner` isn't submitted in preview. If preview quizzes need hiding, that's a follow-up.
- Enrolment is required for the learner player; enrolling stays in `CourseDetail`. If a learner isn't enrolled, the player shows the error gate — acceptable for v1.
