# Course Player + Quiz Engine (Design)

**Date:** 2026-05-26
**Status:** Approved (pending spec review)
**Backlog:** P-3 (learner course player), P-1 (learner quiz-taking), unblocks T-4 (progress→completion).

## 1. Goal & scope

Build the learner-facing **course player** that renders relational slide/block courses
(Course → Module → Video → Slide → Block), with **progress + completion** and an
integrated **quiz engine**. This replaces today's placeholder (the old HTML player was
written for the retired `course.content` JSON; relational courses currently show
"This course doesn't have a playable preview yet").

**In scope (one combined build):**
- React course player rendering slides/blocks via the existing `BlockRenderer` (read-only).
- Paged navigation (Prev/Next) + per-slide **narration autoplay** (play `narration_audio_url`,
  auto-advance on audio-end; manual/timer fallback otherwise; honour Play/Pause).
- **Progress + completion**: update `enrollment.progress`; set `completed=true` at course end.
- **Quiz engine**: new `QuizAttempt` model + learner fetch/submit/score endpoints honouring
  `pass_rate`, `attempts_allowed`, `time_limit`, `shuffle_questions`, `show_feedback`,
  `on_fail_action`; quiz shown inline at the end of a video; gates the next video on a pass.
- Used by both learner (`CourseViewerPage`) and creator/admin **preview** (`CoursePreviewPage`);
  preview is read-only (no progress/attempt writes).

**Out of scope (deferred):** certificates (P-2), AI quiz authoring changes, course player for the
legacy `course.content` format (retired), offline/download.

## 2. Decisions (from brainstorming)

| # | Decision | Choice |
|---|----------|--------|
| 1 | Playback model | **Paged + narration autoplay** (reuse the ILB autoplay pattern) |
| 2 | Progress | **Track progress + mark complete on finish** |
| 3 | Quizzes | **Included** (learner quiz-taking with scoring) |
| 4 | Sequencing | **One combined build** (player + quiz engine together) |
| 5 | Architecture | **React player route** reusing `BlockRenderer` + the tree serializer (not backend HTML) |

## 3. Backend

### 3.1 New model — `QuizAttempt` (Alembic migration 015)
```
id              int PK
quiz_id         int FK quizzes.id (CASCADE)
user_id         int FK users.id (CASCADE)
attempt_number  int            # 1-based per (user, quiz)
score           int            # percentage 0–100
passed          bool
answers         JSON           # {question_id: submitted_answer}
started_at      datetime
submitted_at    datetime
```
Indexed on `(user_id, quiz_id)`. (`Enrollment.progress` Float + `completed` Bool already exist
and are reused for course completion.)

### 3.2 Learner endpoints (new; published + enrolled; never leak answers)
- `GET /api/learn/courses/{id}/player` — returns the course tree via `_serialize_course_tree`,
  **with each question's `correct_answer` and `explanation` removed**, plus the learner's
  `progress` and a per-quiz attempt summary `{attempts_used, attempts_remaining, last_score, passed}`.
  403/404 if not published or not enrolled.
- `POST /api/learn/courses/{id}/progress` — body `{slide_id}`. Recomputes `enrollment.progress`
  as (distinct slides reached / total slides); sets `completed=true` + `completed_at` when the
  final slide is reached. Idempotent.
- `GET /api/learn/quizzes/{quiz_id}` — questions for taking (prompt, type, options, points — **no
  `correct_answer`/`explanation`**), plus `pass_rate`, `attempts_allowed`, `attempts_remaining`,
  `time_limit_seconds`, `shuffle_questions`, `show_feedback`. Server applies `shuffle_questions`.
- `POST /api/learn/quizzes/{quiz_id}/attempt` — body `{answers: {question_id: answer}}`.
  Rejects (409) if `attempts_remaining == 0`. **Scores**: Σ points of correct questions ÷ Σ total
  points × 100; `passed = score >= pass_rate`. Persists a `QuizAttempt` (next `attempt_number`).
  Returns `{score, passed, attempts_remaining}` and per-question `{correct, explanation}` **only
  when `show_feedback` permits** (`immediate`/`on_submit` → include; `never`/`on_pass` → gate
  accordingly).

### 3.3 Answer grading
A helper `grade_question(question, submitted)` per type:
- single-choice / true-false → submitted equals `correct_answer`.
- multiple-choice (multi-select) → submitted set equals `correct_answer` set.
Unknown/blank → incorrect (0 points). Lives in a small `services/quiz_grading.py` (pure,
unit-testable).

### 3.4 Preview path
Creator/admin preview keeps using the existing creator `GET /{course_id}/preview` tree
(bypasses published) and is **read-only**: the player in preview mode calls no progress/attempt
endpoints.

## 4. Frontend

### 4.1 `CoursePlayer` component (new)
Full-screen player used by both `CourseViewerPage` (learner) and `CoursePreviewPage` (creator),
selecting the data source by a `mode: 'learner' | 'preview'` prop:
- learner → `/api/learn/courses/{id}/player`
- preview → `/api/courses/{id}/preview`

Replaces the current `<iframe src=/api/courses/{id}/player>` in both pages.

**Layout:** left rail = Module → Video → Slide outline + progress bar; main stage = current
slide's blocks via the existing `BlockRenderer` (read-only mode); footer = Prev / Next / Play-Pause.

**Navigation & narration:** a flattened ordered list of slides across all videos/modules. The
narration autoplay logic is **extracted into a shared hook** `useSegmentAutoplay` (refactored out
of `ILBPlayerPage`) so both players share one implementation: play the slide's `narration_audio_url`,
auto-advance on `ended`; word-count/duration timer when there's no audio; pause for Play/Pause.

**Quiz gating:** when the learner finishes the last slide of a video that has a quiz, the player
shows the quiz inline; advancing to the next video is gated on a pass (per `on_fail_action`:
`retake` → allow retry while attempts remain; otherwise lock with last result). Preview shows the
quiz but does not submit attempts (renders questions read-only with a notice).

**Progress (learner mode only):** each newly-reached slide POSTs `/progress`; reaching the final
slide marks completion. Preview never writes.

### 4.2 Quiz UI (`QuizRunner` component)
Renders question types (single-choice, multiple-choice, true/false), collects answers, **Submit →
POST attempt → shows score + pass/fail** and per-question feedback when allowed; shows attempts
remaining; **Retake** when failed and attempts remain.

### 4.3 `ilbApi`/`api` additions
Typed client methods: `getCoursePlayer(id)`, `postCourseProgress(id, slideId)`,
`getLearnerQuiz(quizId)`, `submitQuizAttempt(quizId, answers)`.

## 5. Error handling & edge cases
- Not enrolled / not published (learner) → friendly gate with an Enrol/Back action (enrolment
  itself stays in `CourseDetail`).
- Correct answers never sent to the client before submit; feedback gated by `show_feedback`.
- Unknown block types → skipped without crashing; empty course/slide → friendly "nothing to show
  yet" (the placeholder is otherwise removed for relational courses).
- Attempts exhausted → quiz locked, last result shown.
- Preview mode = strictly read-only (no progress, no attempts).

## 6. Testing
- **Backend unit:** `quiz_grading.grade_question` per type; `QuizAttempt` model/migration.
- **Backend router:** player-data gating (published+enrolled) and **no-answer-leak**; progress
  updates `progress` and flips `completed` at the end; quiz attempt scoring (pass/fail at the
  boundary, points weighting), `attempts_allowed` enforcement (409 when exhausted), `show_feedback`
  gating of explanations.
- **Frontend:** `CoursePlayer` renders slides and advances Prev/Next; narration auto-advances on
  audio `ended`; `QuizRunner` submit shows pass/fail + feedback; **preview mode issues no progress/
  attempt calls**.
- **Live prod check:** author a small course (slides + a video quiz), publish, play as a learner →
  reaches completion and the enrollment shows completed; preview as creator (read-only).

## 7. Notes for implementers
- Prod SQLite has no persistent volume; `init_db()` (`create_all`) recreates `quiz_attempts` on
  deploy, so the feature works on the wiped prod DB. Migration 015 keeps the dev chain correct.
- Reuse, don't duplicate: `BlockRenderer` (read-only), `_serialize_course_tree`, and the extracted
  `useSegmentAutoplay` hook.
- Keep `CoursePlayer`, `QuizRunner`, and the autoplay hook as focused, separately-testable units.
