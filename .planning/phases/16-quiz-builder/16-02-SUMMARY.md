---
phase: 16-quiz-builder
plan: 02
subsystem: api
tags: [sse, claude, fastapi, quiz, streaming, pytest]

# Dependency graph
requires:
  - phase: 16-01
    provides: test_quiz_phase16.py with QUIZ-08 stub + creator_quiz fixture + reset_sse_state autouse fixture
  - phase: 11-03
    provides: quizzes.py CRUD router with _get_quiz_or_404 helper
provides:
  - POST /api/quizzes/{quiz_id}/ai/generate-questions SSE endpoint in quizzes.py
  - AiQuestionRequest schema (count, tone_preset)
  - test_generate_questions_streams_tokens GREEN (QUIZ-08)
  - test_generate_questions_requires_auth GREEN
affects: [16-03, 16-04, 16-05, quiz-builder-frontend]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "SSE route declared before GET wildcard (FastAPI path-order safety — same as slides.py, modules.py)"
    - "Module-level claude_service singleton patched via routers.quizzes.claude_service._stream_text"
    - "async generator mock with side_effect=mock_stream for SSE integration tests"

key-files:
  created: []
  modified:
    - backend/routers/quizzes.py
    - backend/tests/test_quiz_phase16.py

key-decisions:
  - "POST /api/quizzes/{quiz_id}/ai/generate-questions declared BEFORE GET /api/quizzes/{quiz_id} — FastAPI first-match-wins (line 223 vs 261)"
  - "Module-level claude_service = ClaudeService() singleton in quizzes.py — enables patch('routers.quizzes.claude_service._stream_text') in tests"
  - "Starlette Request imported from starlette.requests (not fastapi) — consistent with slides.py pattern"

patterns-established:
  - "SSE quiz endpoint: same event_generator + EventSourceResponse + is_disconnected check as slides.py generate-narration"

requirements-completed: [QUIZ-08]

# Metrics
duration: 8min
completed: 2026-05-10
---

# Phase 16 Plan 02: Quiz Builder SSE Endpoint Summary

**SSE endpoint POST /api/quizzes/{quiz_id}/ai/generate-questions added to quizzes.py with claude_service streaming, declared before GET wildcard; QUIZ-08 test GREEN**

## Performance

- **Duration:** ~8 min
- **Started:** 2026-05-10T16:04:00Z
- **Completed:** 2026-05-10T16:12:42Z
- **Tasks:** 2/2
- **Files modified:** 2

## Accomplishments
- AiQuestionRequest schema (count, tone_preset) added to quizzes.py
- POST /api/quizzes/{quiz_id}/ai/generate-questions SSE endpoint live, route declared at line 223 before GET /api/quizzes/{quiz_id} at line 261
- test_generate_questions_streams_tokens PASSED (mocked 3-token stream, status 200, "data:" in body)
- test_generate_questions_requires_auth PASSED (no auth header returns 401/403)
- QUIZ-01 through QUIZ-07 stubs still FAILED as expected

## Task Commits

1. **Task 1: Add AiQuestionRequest schema and SSE endpoint** - `1d8694a` (feat)
2. **Task 2: Make QUIZ-08 backend test GREEN** - `2d5d5f0` (test)

## Files Created/Modified
- `backend/routers/quizzes.py` - Added Request import, EventSourceResponse, ClaudeService, module-level singleton, AiQuestionRequest schema, generate_questions SSE endpoint
- `backend/tests/test_quiz_phase16.py` - Replaced QUIZ-08 stub with real streaming test + auth guard test

## Decisions Made
- POST /api/quizzes/{quiz_id}/ai/generate-questions placed at line 223, before GET /api/quizzes/{quiz_id} at line 261 — mandatory FastAPI path-order collision prevention (same rule as STATE.md decision 14-02 for slides.py)
- Module-level claude_service singleton enables clean test patching via `routers.quizzes.claude_service._stream_text`
- starlette.requests.Request imported (same as slides.py pattern)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- QUIZ-08 backend SSE endpoint is live and tested
- Plans 03 and 04 can now implement QUIZ-01 through QUIZ-07 (question CRUD integration tests)
- Frontend quiz builder work in Plans 03-05 can wire to this endpoint

---
*Phase: 16-quiz-builder*
*Completed: 2026-05-10*
