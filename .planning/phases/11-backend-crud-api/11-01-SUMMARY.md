---
phase: 11-backend-crud-api
plan: "01"
subsystem: api
tags: [fastapi, sqlalchemy, pydantic, pytest, modules, crud]

requires:
  - phase: 10-data-models
    provides: Module SQLAlchemy model with course_id FK, order_index, cascade delete to Video

provides:
  - "POST /api/courses/{course_id}/modules — create module, returns 201"
  - "GET /api/courses/{course_id}/modules — list ordered by order_index"
  - "GET /api/modules/{module_id} — single module detail"
  - "PUT /api/modules/{module_id} — partial update"
  - "DELETE /api/modules/{module_id} — cascade deletes videos"
  - "POST /api/courses/{course_id}/modules/reorder — atomic single-transaction reorder"
  - "7-test pytest suite proving all operations + 403 guards"

affects:
  - 11-02-video-router
  - 12-course-builder-ui

tech-stack:
  added: []
  patterns:
    - "Single APIRouter with explicit /api/... paths (no router prefix) for resource endpoints spanning two URL hierarchies"
    - "Ownership helper _get_course_or_404 + _check_course_ownership for consistent 404/403 logic"
    - "Reorder: load all siblings in one query, reassign order_index in loop, single db.commit() — prevents drift"

key-files:
  created:
    - backend/routers/modules.py
    - backend/tests/test_modules_router.py
  modified:
    - backend/main.py
    - backend/tests/conftest.py

key-decisions:
  - "Single router with explicit /api/courses/... and /api/modules/... paths (no router prefix) avoids prefix conflicts with existing courses.py router which already owns /api/courses prefix"
  - "Reorder uses single db.commit() after all index assignments to guarantee atomicity and prevent order_index drift"
  - "conftest.py Course fixtures had stale content= kwarg (column removed in Phase 10 migration) — removed to restore test suite correctness"

patterns-established:
  - "Module ownership guard: course.creator_id == current_user.id; admin role bypasses via role.value != 'admin' check"

requirements-completed: [API-01, API-07]

duration: 3min
completed: "2026-05-09"
---

# Phase 11 Plan 01: Module CRUD + Reorder Router Summary

**FastAPI Module CRUD router with 6 endpoints (create/list/get/update/delete/reorder), atomic order_index management, and 7-test pytest suite proving creator-only access and 403 trainee guards**

## Performance

- **Duration:** ~3 min
- **Started:** 2026-05-09T09:52:49Z
- **Completed:** 2026-05-09T09:55:54Z
- **Tasks:** 2/2
- **Files modified:** 4

## Accomplishments
- Module CRUD router with 6 endpoints registered at `/api/courses/{id}/modules` and `/api/modules/{id}`
- Reorder endpoint uses a single `db.commit()` after all `order_index` reassignments — atomic, no drift
- All 7 tests pass GREEN; `test_data_models.py` unchanged (25 total pass)

## Task Commits

1. **Task 1: Module router — CRUD + reorder** - `112bee5` (feat)
2. **Task 2: Module router tests + register in main.py** - `ed918a6` (feat)

## Files Created/Modified
- `backend/routers/modules.py` - Module CRUD + reorder router with 6 endpoints, Pydantic schemas, ownership helpers
- `backend/tests/test_modules_router.py` - 7 pytest tests covering all operations and 403 guards
- `backend/main.py` - Added `modules` import and `app.include_router(modules.router)`
- `backend/tests/conftest.py` - Removed stale `content=` kwargs from Course fixtures (Rule 1 bug fix)

## Decisions Made
- Used a single `APIRouter` with no prefix and explicit paths (`/api/courses/{id}/modules`, `/api/modules/{id}`) to avoid prefix collision with `courses.py` which already owns `/api/courses`
- Reorder validates all module IDs in one query (`Module.id.in_(body.module_ids)`) before mutating, then single `db.commit()` — guarantees atomicity
- `_get_course_or_404` combines 404 + 403 ownership checks in one helper, matching the ownership pattern in `courses.py`

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Removed stale `content=` kwargs from conftest.py Course fixtures**
- **Found during:** Task 2 (running tests)
- **Issue:** `published_course`, `draft_course`, and `creator_course` fixtures passed `content={"modules": [...]}` to the `Course` constructor. The `Course.content` column was dropped in Phase 10 migration 003, making this a `TypeError: 'content' is an invalid keyword argument for Course` error on every test.
- **Fix:** Removed `content=` argument from all three fixtures in `conftest.py`
- **Files modified:** `backend/tests/conftest.py`
- **Verification:** All 7 module tests pass GREEN; `test_data_models.py` 18 tests unaffected
- **Committed in:** `ed918a6` (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - Bug)
**Impact on plan:** Fix was necessary for test suite to run. No scope creep — change is minimal (3 lines removed from conftest.py).

## Issues Encountered
- bcrypt 5.0 + passlib 1.7.4 incompatibility on Python 3.14 (`__about__` attribute removed) — conftest.py already had a `detect_wrap_bug` monkey-patch from a previous plan. Downgraded to `bcrypt==4.0.1` in the local venv to confirm the patch resolved it cleanly.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Module endpoints are live and tested; Plan 02 (Video router) can now depend on module IDs
- Phase 12 (Course Builder UI) has all module API endpoints available
- No blockers

---
*Phase: 11-backend-crud-api*
*Completed: 2026-05-09*
