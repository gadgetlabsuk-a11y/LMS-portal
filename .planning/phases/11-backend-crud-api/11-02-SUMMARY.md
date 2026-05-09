---
phase: 11-backend-crud-api
plan: 02
subsystem: api
tags: [fastapi, sqlalchemy, pydantic, pytest, crud, video, slide]

# Dependency graph
requires:
  - phase: 11-01
    provides: modules router, ownership check pattern, reorder atomic pattern, conftest fixtures
provides:
  - Video CRUD + reorder router (6 endpoints)
  - Slide CRUD + reorder router (6 endpoints)
  - Combined pytest test suite — 12 tests GREEN
  - videos.router and slides.router registered in main.py
affects: [14-slide-builder, 15-ai-generation, 17-tts-pipeline]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "ownership traversal via SQLAlchemy .join() chain: Video.join(Module).join(Course) — no joinedload, explicit joins for clarity"
    - "slide ownership: Slide.join(Video).join(Module).join(Course) — three-hop traversal"
    - "reorder: single db.commit() after all order_index assignments — atomic, no drift"
    - "test fixtures chained via API calls (creator_module → creator_video → creator_slide) for realistic integration coverage"

key-files:
  created:
    - backend/routers/videos.py
    - backend/routers/slides.py
    - backend/tests/test_videos_slides_router.py
  modified:
    - backend/main.py

key-decisions:
  - "videos.py uses _get_module_or_404 helper (module.join(Course)) for create/list/reorder; get/update/delete use inline join for single-item fetch"
  - "slides.py uses _get_video_or_404 helper (video.join(Module).join(Course)) for create/list/reorder; get/update/delete use inline four-table join"
  - "creator_course fixture from conftest.py reused (no re-definition in test file); creator_module/creator_video/creator_slide defined locally as they are test-file-specific"

patterns-established:
  - "Ownership check helper pattern: _get_{parent}_or_404(id, db, current_user) with join chain and role check"
  - "Reorder endpoint pattern: validate all IDs belong to parent in one query, assign idx in loop, single commit"

requirements-completed: [API-02, API-03, API-07]

# Metrics
duration: 2min
completed: 2026-05-09
---

# Phase 11 Plan 02: Video + Slide CRUD API Summary

**Video and Slide CRUD + reorder routers with 12 tests GREEN — ownership traverses module.course and video.module.course chains**

## Performance

- **Duration:** 2 min
- **Started:** 2026-05-09T08:58:30Z
- **Completed:** 2026-05-09T09:00:38Z
- **Tasks:** 2/2
- **Files modified:** 4

## Accomplishments

- Created `backend/routers/videos.py` with 6 endpoints: POST create, GET list, GET single, PUT update, DELETE delete, POST reorder — all with 403/404 guards
- Created `backend/routers/slides.py` with 6 endpoints following identical pattern, ownership traverses three hops (slide → video → module → course → creator_id)
- 12 pytest tests all GREEN covering every endpoint including trainee 403 rejection and atomic reorder verification

## Task Commits

1. **Task 1: Video + Slide routers — CRUD + reorder** - `9623939` (feat)
2. **Task 2: Video + Slide tests + register in main.py** - `0a9e8b4` (feat)

**Plan metadata:** (see final commit below)

## Files Created/Modified

- `backend/routers/videos.py` — 6 Video endpoints, VideoCreate/Update/Response schemas, _get_module_or_404 helper
- `backend/routers/slides.py` — 6 Slide endpoints, SlideCreate/Update/Response schemas, _get_video_or_404 helper
- `backend/tests/test_videos_slides_router.py` — 12 tests with creator_module/creator_video/creator_slide fixtures
- `backend/main.py` — imports videos and slides, registers videos.router and slides.router after modules.router

## Decisions Made

- `_get_module_or_404` used as helper for operations that require the parent (create, list, reorder); single-item operations (get, update, delete) use inline join for consistency with modules.py pattern
- Test fixtures use API calls (not direct DB inserts) to exercise the full stack — if the create endpoint breaks, fixture fails immediately with a clear assert message
- `creator_course` not redefined in test file — conftest fixture already exists and covers the same shape

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

- `python` not on PATH in venv activation context; used `source venv/bin/activate && python3` pattern. All tests pass cleanly after activation.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- Video and Slide endpoints are live; Slide Builder (Phase 14) can now POST/GET/PUT slides via `/api/videos/{id}/slides`
- Block CRUD endpoints (Plan 03) will follow the same three-hop ownership pattern established here
- All 37 tests (data models + modules + videos/slides) pass GREEN

---
*Phase: 11-backend-crud-api*
*Completed: 2026-05-09*
