---
phase: 12-course-identity-structure
plan: 02
subsystem: api
tags: [fastapi, sse, claude, streaming, pydantic, pytest]

# Dependency graph
requires:
  - phase: 12-01
    provides: Wave 0 stubs for COURSE-01/02/03/05 in test_courses_phase12.py; sse-starlette declared
  - phase: 10-02
    provides: Course ORM model with audience_level, learning_objectives, ai_tone_preset, ai_custom_prompt columns

provides:
  - POST /api/courses accepts and persists all Phase 12 identity fields
  - POST /api/courses/ai/generate-description — SSE streaming endpoint via EventSourceResponse
  - POST /api/courses/ai/generate-objectives — SSE streaming endpoint via EventSourceResponse
  - ClaudeService.stream_course_description() async generator
  - ClaudeService.stream_learning_objectives() async generator
  - ClaudeService._stream_text() core streaming method (httpx streaming, Anthropic SSE protocol)
  - GREEN test assertions for COURSE-01, COURSE-02, COURSE-03, COURSE-05

affects:
  - 12-03 (frontend identity form can build against confirmed endpoints)
  - 12-04 (scaffold UI can use confirmed module/video creation endpoint behaviour)

# Tech tracking
tech-stack:
  added: [sse-starlette==2.1.3 (installed to venv)]
  patterns:
    - SSE endpoints use EventSourceResponse wrapping an async generator that checks request.is_disconnected()
    - Module-level claude_service = ClaudeService() singleton in courses.py; patch via routers.courses.claude_service
    - AppStatus.should_exit_event reset to None before each SSE test to avoid anyio.Event cross-loop binding
    - ClaudeService streaming via httpx.AsyncClient.stream() parsing Anthropic SSE lines

key-files:
  created: []
  modified:
    - backend/routers/courses.py
    - backend/services/claude_service.py
    - backend/tests/test_courses_phase12.py

key-decisions:
  - "Module-level claude_service singleton in courses.py; function-local instantiations in generate_course and generate_course_from_document left unchanged to avoid regression"
  - "SSE routes /ai/generate-description and /ai/generate-objectives declared before /{course_id} routes to prevent FastAPI path collision"
  - "AppStatus.should_exit_event = None reset added to each SSE test — sse-starlette 2.x creates anyio.Event class-level attribute at first request; TestClient cycles event loops between tests causing 'bound to a different event loop' RuntimeError"
  - "test_learn_router.py::test_returns_only_published_courses is a pre-existing failure unrelated to this plan; verified by git stash before/after check"
  - "learning_objectives stored and returned as JSON array of strings; CourseResponse extended with audience_level, learning_objectives, ai_tone_preset (all Optional)"

patterns-established:
  - "SSE generator pattern: async def generator() inside route, yields {data: token}, checks await request.is_disconnected() on every yield before yield"
  - "Mock SSE in tests: patch routers.courses.claude_service.<method> with side_effect=lambda: _mock_stream() + reset AppStatus.should_exit_event = None"

requirements-completed: [COURSE-01, COURSE-02, COURSE-03, COURSE-05]

# Metrics
duration: 18min
completed: 2026-05-09
---

# Phase 12 Plan 02: Course Identity & Structure Backend Summary

**Extended CourseCreate with Phase 12 identity fields, added two SSE AI endpoints backed by ClaudeService streaming generators, and replaced Wave 0 stubs with GREEN integration tests**

## Performance

- **Duration:** 18 min
- **Started:** 2026-05-09T09:48:45Z
- **Completed:** 2026-05-09T10:07:00Z
- **Tasks:** 2/2
- **Files modified:** 3

## Accomplishments

- CourseCreate/CourseResponse now accept and return audience_level, learning_objectives (JSON array), ai_tone_preset, ai_custom_prompt, summary
- Two SSE endpoints added at /api/courses/ai/generate-description and /api/courses/ai/generate-objectives, both declared before /{course_id} to prevent path collision
- ClaudeService gains stream_course_description(), stream_learning_objectives(), and _stream_text() for real Anthropic streaming API calls
- All 4 Phase 12 tests GREEN: COURSE-01 (identity persistence), COURSE-02 (description SSE), COURSE-03 (objectives SSE), COURSE-05 (scaffold structure)

## Task Commits

Each task was committed atomically:

1. **Tasks 1+2: Extend CourseCreate + SSE endpoints + ClaudeService streaming + GREEN tests** - `f148213` (feat)

**Plan metadata:** (docs commit to follow)

## Files Created/Modified

- `backend/routers/courses.py` - Added sse_starlette import, module-level claude_service singleton, Phase 12 identity fields in CourseCreate and CourseResponse, AiDescriptionRequest/AiObjectivesRequest models, two SSE POST endpoints
- `backend/services/claude_service.py` - Added AsyncGenerator import, stream_course_description(), stream_learning_objectives(), _stream_text() methods
- `backend/tests/test_courses_phase12.py` - Replaced pytest.fail() stubs with real assertions for all 4 tests; AppStatus reset for SSE test isolation

## Decisions Made

- Module-level `claude_service = ClaudeService()` singleton added to courses.py; existing function-local instantiations in `generate_course` and `generate_course_from_document` left unchanged to avoid regression risk
- SSE routes declared before `/{course_id}` routes — FastAPI matches routes in declaration order; "ai" would otherwise match as a course_id integer (and fail with 422)
- `AppStatus.should_exit_event = None` reset before each SSE test: sse-starlette 2.x creates a class-level `anyio.Event` at first request; with Starlette TestClient cycling event loops between tests, the second SSE test fails with "bound to a different event loop"

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] AppStatus.should_exit_event cross-event-loop binding in SSE tests**
- **Found during:** Task 1 (running test_generate_objectives_sse after test_generate_description_sse)
- **Issue:** sse-starlette 2.x stores `anyio.Event()` as class attribute `AppStatus.should_exit_event`; created in first test's event loop, reused in second test's different event loop causing `RuntimeError: is bound to a different event loop`
- **Fix:** Added `AppStatus.should_exit_event = None` before each SSE test call to force re-creation in the current loop
- **Files modified:** backend/tests/test_courses_phase12.py
- **Verification:** All 4 tests pass consistently in sequence
- **Committed in:** f148213

---

**Total deviations:** 1 auto-fixed (Rule 1 - Bug)
**Impact on plan:** Fix essential for test reliability — sse-starlette TestClient interaction not covered by plan. No scope creep.

## Issues Encountered

- `test_learn_router.py::test_returns_only_published_courses` appeared in full suite run; confirmed pre-existing by `git stash` verification — failing before any 12-02 changes, out of scope
- sse-starlette not yet installed in venv despite being in requirements.txt — installed via `venv/bin/pip install sse-starlette==2.1.3`

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Backend endpoints confirmed and tested; frontend identity form (12-03) can build against POST /api/courses with identity fields
- SSE endpoints ready for frontend streaming UI (12-03)
- Scaffold structure verified (COURSE-05) — module and video creation in order works correctly

---
*Phase: 12-course-identity-structure*
*Completed: 2026-05-09*
