---
phase: 16-quiz-builder
verified: 2026-05-10T00:00:00Z
status: passed
score: 4/4 must-haves verified
re_verification: false
---

# Phase 16: Quiz Builder Verification Report

**Phase Goal:** Creators can build quizzes with four question types, reorder questions by drag-and-drop, and generate a batch of questions via AI from module content.
**Verified:** 2026-05-10
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | A creator can create a quiz linked to a module and configure pass score, max attempts, and feedback settings | VERIFIED | `QuizBuilderPage.tsx` lines 93–107: `handleSaveSettings` calls `PUT /api/quizzes/{quizId}` with all three fields. Backend `update_quiz` (quizzes.py:270–293) accepts `QuizUpdate` and persists via `model_dump(exclude_unset=True)`. |
| 2 | A creator can add MCQ single-answer, MCQ multi-answer, true/false, and short-answer questions with correct answers and explanation text | VERIFIED | `QuestionForm.tsx` implements all four types with type-specific correct-answer inputs (radio for mcq_single, checkboxes for mcq_multi, radio pair for true_false, text input for short_answer) plus explanation textarea present for all types. Backend `create_question` stores `type`, `correct_answer`, `explanation` for all variants. |
| 3 | A creator can drag questions to reorder them; the new order persists after a page reload with no `order_index` drift | VERIFIED | `SortableQuestionRow.tsx` wraps each question in dnd-kit `useSortable`. `handleDragEnd` in `QuizBuilderPage.tsx` calls `POST /api/quizzes/{quizId}/questions/reorder`. Backend `reorder_questions` (quizzes.py:424–456) validates all IDs belong to the quiz then atomically reassigns `order_index` in a single `db.commit()`. `list_questions` orders by `order_index` on read — no drift possible. |
| 4 | A creator can trigger AI question generation from module content and see a batch of questions streamed in, then confirm them to the quiz | VERIFIED | `handleGenerate` in `QuizBuilderPage.tsx` uses `useSSEStream` → `POST /api/quizzes/{quizId}/ai/generate-questions`. Backend streams tokens via `EventSourceResponse` + `claude_service._stream_text(prompt)`. Frontend accumulates buffer, parses JSON, populates `pendingQuestions` shown in `SideDrawer`. `handleConfirmAI` POSTs each pending question to `POST /api/quizzes/{quizId}/questions`. |

**Score:** 4/4 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `frontend/src/pages/creator/QuizBuilderPage.tsx` | Quiz settings form, question list with DnD, AI drawer | VERIFIED | 407 lines, substantive. Full implementation — settings, add/edit/delete questions, DndContext wiring, SideDrawer AI flow. |
| `frontend/src/components/quiz/QuestionForm.tsx` | All four question type forms with correct-answer and explanation fields | VERIFIED | 230 lines, substantive. All four types implemented with type-switching logic and `buildCorrectAnswer()`. |
| `frontend/src/components/quiz/SortableQuestionRow.tsx` | Drag handle wrapping question content | VERIFIED | 39 lines. Uses `useSortable`, renders braille-dot drag handle at absolute left position, outside interactive child content. |
| `backend/routers/quizzes.py` | Quiz CRUD, Question CRUD, reorder endpoint, SSE AI endpoint | VERIFIED | 456 lines. All endpoints present with auth guards (`require_creator`), ownership checks, atomic reorder, SSE streaming. |
| `frontend/src/App.tsx` | Route `/creator/courses/:id/quizzes/:quizId` registered | VERIFIED | Line 171–179: route registered with `ProtectedRoute creatorRoute` wrapping `QuizBuilderPage`. |
| `frontend/src/components/builder/CourseTreeRail.tsx` | Quiz rows link to quiz builder | VERIFIED | Lines 87–107: renders quiz rows with `onClick` navigating to `/creator/courses/${courseId}/quizzes/${quiz.id}`. Fed by `CourseBuilderPage` which fetches `/modules/${mod.id}/quizzes`. |
| `frontend/src/pages/creator/__tests__/QuizBuilderPage.test.tsx` | Unit tests for QUIZ-01, QUIZ-07, QUIZ-08 | VERIFIED | 109 lines. 4 substantive tests covering settings render, question list, AI button, SideDrawer open. |
| `frontend/src/components/quiz/__tests__/QuestionForm.test.tsx` | Unit tests for QUIZ-02 through QUIZ-06 | VERIFIED | 53 lines. 7 tests covering all four question types, explanation field, save callback shape, cancel callback. |
| `backend/tests/test_quiz_phase16.py` | Integration tests QUIZ-01 through QUIZ-08 | VERIFIED | 201 lines. 9 tests: settings update, all four question types, explanation persistence, reorder persists, SSE streaming, unauthenticated rejection. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `QuizBuilderPage` | `PUT /api/quizzes/{quizId}` | `api.put` in `handleSaveSettings` | WIRED | Line 97: `api.put(\`/quizzes/${quizId}\`, {...})`. Response stored in state. |
| `QuizBuilderPage` | `POST /api/quizzes/{quizId}/questions` | `api.post` in `handleAddQuestion` | WIRED | Lines 118–124: posts all question fields, then reloads list. |
| `QuizBuilderPage` | `POST /api/quizzes/{quizId}/questions/reorder` | `api.post` in `handleDragEnd` | WIRED | Lines 153–155: POSTs `question_ids` array after optimistic UI update. |
| `QuizBuilderPage` | SSE `POST /api/quizzes/{quizId}/ai/generate-questions` | `useSSEStream.startStream` | WIRED | Lines 161–166: streams tokens into `bufferRef`, parses JSON on completion, sets `pendingQuestions`. |
| `pendingQuestions` | `POST /api/quizzes/{quizId}/questions` | `handleConfirmAI` loop | WIRED | Lines 175–187: iterates pending questions, POSTs each, clears state, reloads list. |
| `CourseTreeRail` quiz row | `/creator/courses/:id/quizzes/:quizId` route | `navigate()` onClick | WIRED | Line 92: `navigate(\`/creator/courses/${courseId}/quizzes/${quiz.id}\`)`. |
| `backend/routers/quizzes.py` | `ClaudeService._stream_text` | `claude_service._stream_text(prompt)` | WIRED | Lines 248–254: async generator consumed into `EventSourceResponse`. |
| `quizzes.router` | FastAPI `app` | `app.include_router` in `main.py` | WIRED | main.py line 211: `app.include_router(quizzes.router)`. |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| QUIZ-01 | 16-05-PLAN.md | Quiz settings (pass_rate, attempts_allowed, show_feedback) | SATISFIED | `handleSaveSettings` + `QuizUpdate` schema + backend `update_quiz`. |
| QUIZ-02 | 16-05-PLAN.md | MCQ single-answer question type | SATISFIED | `QuestionForm.tsx` mcq_single branch; backend `QuestionCreate` + `create_question`. |
| QUIZ-03 | 16-05-PLAN.md | MCQ multi-answer question type | SATISFIED | `QuestionForm.tsx` mcq_multi branch with checkbox correct-answer selection. |
| QUIZ-04 | 16-05-PLAN.md | True/false question type | SATISFIED | `QuestionForm.tsx` true_false branch with True/False radio pair. |
| QUIZ-05 | 16-05-PLAN.md | Short-answer question type | SATISFIED | `QuestionForm.tsx` short_answer branch with optional model answer input. |
| QUIZ-06 | 16-05-PLAN.md | Explanation text on all question types | SATISFIED | Explanation `<Textarea>` rendered unconditionally outside type switch. Backend stores `explanation` field. |
| QUIZ-07 | 16-05-PLAN.md | Drag-to-reorder with no order_index drift | SATISFIED | `SortableQuestionRow` + `handleDragEnd` + atomic `reorder_questions` endpoint. |
| QUIZ-08 | 16-05-PLAN.md | AI question generation via SSE, confirm to quiz | SATISFIED | `handleGenerate` via `useSSEStream` + backend `generate_questions` SSE endpoint + `handleConfirmAI`. |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `QuestionForm.tsx` | 112, 145, 205, 219 | `placeholder=` attribute | Info | HTML input placeholder attributes — correct usage, not stub code. |

No stub code, TODO/FIXME comments, empty handlers, or placeholder return values found in any phase 16 file.

### Human Verification Required

All human browser checks (6 checks) were completed and approved prior to this verification, as documented in `16-05-SUMMARY.md`:

1. Navigate from CourseTreeRail to QuizBuilderPage — Passed
2. Quiz settings (pass_rate, attempts_allowed, show_feedback) persist after reload — Passed
3. All 4 question types (MCQ single, MCQ multi, true/false, short answer) — Passed
4. Explanation text persists after reload — Passed
5. Drag-to-reorder persists after reload (no order_index drift) — Passed
6. AI question generation streams, pending questions shown, "Add All" commits to quiz — Passed

No further human verification is required.

### Summary

All four success criteria are fully achieved. Every key artifact is substantive, correctly wired, and tested. The backend reorder endpoint uses a single atomic transaction to prevent `order_index` drift. The AI generation pipeline is end-to-end: SSE from Claude service → token accumulation → JSON parse → pending preview → bulk confirm. Route registration, navigation from the course tree, and auth guards are all in place. 9/9 backend tests and 59/60 frontend tests pass (1 pre-existing jsdom AbortController limitation unrelated to phase 16).

---

_Verified: 2026-05-10_
_Verifier: Claude (gsd-verifier)_
