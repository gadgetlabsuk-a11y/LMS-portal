---
phase: 12-course-identity-structure
plan: 01
subsystem: testing
tags: [pytest, vitest, sse-starlette, tdd, wave0]

# Dependency graph
requires:
  - phase: 11-backend-crud-api
    provides: conftest.py fixtures (client, creator_token, creator_course) used by backend stubs
provides:
  - "4 failing backend test stubs for COURSE-01 through COURSE-05 (minus COURSE-04)"
  - "1 failing frontend test stub for COURSE-04 SkeletonTreePreview"
  - "sse-starlette==2.1.3 in requirements.txt for SSE streaming endpoints"
affects: [12-02, 12-03]

# Tech tracking
tech-stack:
  added: [sse-starlette==2.1.3]
  patterns: [Wave 0 RED stub pattern — pytest.fail() for backend, import-fail for frontend]

key-files:
  created:
    - backend/tests/test_courses_phase12.py
    - frontend/src/components/course/__tests__/SkeletonTreePreview.test.tsx
  modified:
    - backend/requirements.txt

key-decisions:
  - "Backend stubs use pytest.fail() directly — no Phase 12 imports — so they fail cleanly rather than with ImportError before any implementation exists"
  - "Frontend stub uses direct import of non-existent SkeletonTreePreview.tsx — vitest import failure is the intended RED state for Wave 0"
  - "sse-starlette placed after httpx in requirements.txt (grouping with async/HTTP dependencies)"

patterns-established:
  - "Wave 0 stub pattern: pytest.fail('STUB — implement in 12-XX') for clean FAILED state"
  - "Frontend Wave 0 stub: import from not-yet-created component causes test file failure on collection"

requirements-completed: [COURSE-01, COURSE-02, COURSE-03, COURSE-04, COURSE-05]

# Metrics
duration: 12min
completed: 2026-05-09
---

# Phase 12 Plan 01: Course Identity Structure — Test Scaffold Summary

**Nyquist-compliant Wave 0 test scaffold: 4 backend stubs (FAILED via pytest.fail) + 1 frontend stub (FAILED via missing import) + sse-starlette==2.1.3 dependency declared**

## Performance

- **Duration:** ~12 min
- **Started:** 2026-05-09T09:33:07Z
- **Completed:** 2026-05-09T09:45:00Z
- **Tasks:** 3/3
- **Files modified:** 3

## Accomplishments
- Added sse-starlette==2.1.3 to backend/requirements.txt (required for COURSE-02 and COURSE-03 SSE streaming)
- Created 4 backend test stubs (test_courses_phase12.py) — all 4 show FAILED (not ERROR) in pytest output
- Created frontend test stub (SkeletonTreePreview.test.tsx) — fails on import of non-existent component

## Task Commits

Each task was committed atomically:

1. **Task 1: Add sse-starlette to requirements.txt** - `40c0b98` (chore)
2. **Task 2: Create backend test stubs (COURSE-01, 02, 03, 05)** - `e120aea` (test)
3. **Task 3: Create frontend SkeletonTreePreview test stub (COURSE-04)** - `ae46149` (test)

**Plan metadata:** (docs commit follows)

## Files Created/Modified
- `backend/requirements.txt` - Added sse-starlette==2.1.3 after httpx line
- `backend/tests/test_courses_phase12.py` - 4 stub tests using pytest.fail(), all FAILED
- `frontend/src/components/course/__tests__/SkeletonTreePreview.test.tsx` - Frontend stub that fails on import of missing component

## Decisions Made
- Backend stubs use `pytest.fail()` directly with no Phase 12 imports so failures are clean FAILED (not ERROR/ImportError)
- Frontend stub uses direct import — vitest fails the whole test file at collection, which is the acceptable Wave 0 RED state
- sse-starlette placed after httpx (logical grouping with async/HTTP dependencies)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- vitest hangs when run non-interactively via `npx vitest run` or `npm run test:unit -- --run` on this macOS machine (process never terminates). Verified RED state logically: `SkeletonTreePreview.tsx` does not exist in `frontend/src/components/course/`, so the import in the test stub will always fail at collection. The vitest config includes `src/**/*.test.{ts,tsx}` which covers this path.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Wave 0 scaffold is complete — all 5 requirements have failing stubs
- 12-02 can now implement COURSE-01 through COURSE-03 and COURSE-05 (backend)
- 12-03 can implement COURSE-04 (SkeletonTreePreview component)
- No blockers

---
*Phase: 12-course-identity-structure*
*Completed: 2026-05-09*
