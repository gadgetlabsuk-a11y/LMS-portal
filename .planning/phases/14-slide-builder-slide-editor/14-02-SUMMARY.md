---
phase: 14-slide-builder-slide-editor
plan: 02
subsystem: api
tags: [sse, streaming, claude, fastapi, slides, narration, outline]

# Dependency graph
requires:
  - phase: 14-01
    provides: RED stub tests for SLIDE-11 and SLIDE-12 in test_slides_phase14.py
  - phase: 12-02
    provides: ClaudeService._stream_text pattern and SSE route ordering pattern
provides:
  - POST /api/slides/{slide_id}/ai/generate-narration SSE endpoint (SLIDE-11)
  - POST /api/slides/{slide_id}/ai/generate-outline SSE endpoint (SLIDE-12)
  - AiNarrationRequest and AiOutlineRequest Pydantic models in slides.py
  - _get_slide_or_404 ownership helper in slides.py
  - 5 GREEN integration tests in test_slides_phase14.py
affects: [14-05-frontend-slide-editor, 14-03, 14-04]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "SSE routes declared before wildcard GET /{id} — FastAPI declaration-order path matching"
    - "claude_service = ClaudeService() module-level singleton in slides.py"
    - "AppStatus.should_exit_event = None reset in each SSE test (sse-starlette 2.x anyio fix)"
    - "_stream_text mock uses side_effect=async_gen_fn in SSE integration tests"

key-files:
  created: []
  modified:
    - backend/routers/slides.py
    - backend/tests/test_slides_phase14.py

key-decisions:
  - "SSE routes POST /api/slides/{slide_id}/ai/* declared BEFORE GET /api/slides/{slide_id} wildcard — FastAPI path collision prevention"
  - "_get_slide_or_404 added to slides.py (duplicated from blocks.py) — keeps SSE endpoints self-contained without cross-router import"
  - "Block content text assembled by joining b.content.get('text') or b.content.get('html') — handles both rich-text and plain-text block types"

patterns-established:
  - "slides.py SSE pattern: identical to modules.py pattern from Phase 12/13"

requirements-completed: [SLIDE-11, SLIDE-12]

# Metrics
duration: 15min
completed: 2026-05-09
---

# Phase 14 Plan 02: Slide AI SSE Endpoints Summary

**Two new SSE streaming endpoints in slides.py — generate-narration (SLIDE-11) and generate-outline (SLIDE-12) — with ClaudeService singleton, ownership helper, and 5 GREEN integration tests**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-05-09T17:44:49Z
- **Completed:** 2026-05-09T17:59:00Z
- **Tasks:** 2/2
- **Files modified:** 2

## Accomplishments

- Added `generate-narration` and `generate-outline` SSE endpoints to slides.py, both declared before the GET `/{slide_id}` wildcard route
- Added `ClaudeService` module-level singleton, `AiNarrationRequest`, `AiOutlineRequest` models, and `_get_slide_or_404` helper
- Replaced 5 pytest.fail() stubs in test_slides_phase14.py with full integration tests — all GREEN; full backend suite passes (5 pre-existing learn_router failures unchanged)

## Task Commits

1. **Task 1: Add SSE endpoints to slides.py** - `9e7ba27` (feat)
2. **Task 2: Implement backend test stubs → GREEN** - `091413d` (feat)

## Files Created/Modified

- `backend/routers/slides.py` - Added SSE imports, ClaudeService singleton, AiNarrationRequest/AiOutlineRequest models, _get_slide_or_404 helper, generate-narration and generate-outline endpoints
- `backend/tests/test_slides_phase14.py` - Replaced stubs with creator_slide fixture and 5 real integration tests

## Decisions Made

- SSE routes declared before wildcard `GET /api/slides/{slide_id}` — FastAPI routes matched in declaration order; POST `.../ai/generate-narration` would shadow or be shadowed without this ordering
- `_get_slide_or_404` duplicated into slides.py rather than imported from blocks.py — avoids cross-router coupling; the helper is 10 lines and idiomatic to keep co-located with the routes that use it
- Block text assembled via `content.get("text") or content.get("html")` — handles both plain-text and TipTap HTML block content types

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Removed stale test_lms_tmp.db before running tests**
- **Found during:** Task 2 (running test suite)
- **Issue:** Leftover SQLite file from prior test run caused `table users already exists` OperationalError at test setup
- **Fix:** Deleted `backend/test_lms_tmp.db` — conftest `setup_test_db` fixture creates and drops DB each test, but leftover file from interrupted run blocks first `create_all`
- **Files modified:** None (file deletion only)
- **Verification:** Tests ran cleanly after removal
- **Committed in:** N/A (file not tracked by git)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Trivial cleanup of stale test artifact. No scope creep.

## Issues Encountered

- `_get_slide_or_404` shown as "existing helper" in plan interfaces section but actually lives in `blocks.py`, not `slides.py` — added it to slides.py as intended by the plan's action steps.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- SLIDE-11 and SLIDE-12 backend complete — Plan 05 (frontend slide editor) can consume these SSE endpoints
- Plans 14-03 and 14-04 (block CRUD and slide canvas) are independent of these SSE endpoints

---
*Phase: 14-slide-builder-slide-editor*
*Completed: 2026-05-09*
