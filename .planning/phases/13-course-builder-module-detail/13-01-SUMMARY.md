---
phase: 13-course-builder-module-detail
plan: 01
subsystem: testing
tags: [vitest, pytest, dnd-kit, tdd, react, typescript]

requires:
  - phase: 12-course-identity-structure
    provides: Builder stub route in App.tsx, SSE pattern in courses.py, ModuleUpdate schema fields

provides:
  - "@dnd-kit/core, @dnd-kit/sortable, @dnd-kit/utilities installed in frontend/package.json"
  - "CourseBuilderPage.test.tsx: 3 failing stubs for BUILD-01/BUILD-02/BUILD-03"
  - "ModuleDetailPage.test.tsx: 2 failing stubs for BUILD-04/BUILD-05"
  - "test_modules_phase13.py: 3 failing stubs for BUILD-05 SSE endpoint"

affects:
  - 13-02-PLAN.md
  - 13-03-PLAN.md
  - 13-04-PLAN.md

tech-stack:
  added:
    - "@dnd-kit/core ^6.x"
    - "@dnd-kit/sortable ^8.x"
    - "@dnd-kit/utilities ^3.x"
  patterns:
    - "TDD RED stubs: frontend uses import-of-nonexistent-file to fail at vitest collection"
    - "TDD RED stubs: backend uses pytest.fail() directly to produce FAILED (not ERROR) state"

key-files:
  created:
    - frontend/src/pages/creator/__tests__/CourseBuilderPage.test.tsx
    - frontend/src/pages/creator/__tests__/ModuleDetailPage.test.tsx
    - backend/tests/test_modules_phase13.py
  modified:
    - frontend/package.json
    - frontend/package-lock.json

key-decisions:
  - "Frontend RED state: import non-existent ../CourseBuilderPage and ../ModuleDetailPage — vitest fails at collection with import resolution error (not a test-body failure)"
  - "Backend RED state: pytest.fail() directly in test functions (no imports of unimplemented code) — produces FAILED not ERROR, matching Phase 12 Wave 0 pattern"
  - "dnd-kit locked as drag-and-drop library per STATE.md stack decision; react-grid-layout reserved for slide canvas only"

patterns-established:
  - "Wave 0 TDD: always create __tests__ dir + stub files before any implementation exists"
  - "venv activation required for backend pytest (pyotp and other deps not on system path)"

requirements-completed:
  - BUILD-01
  - BUILD-02
  - BUILD-03
  - BUILD-04
  - BUILD-05
  - BUILD-06

duration: 2min
completed: 2026-05-09
---

# Phase 13 Plan 01: Course Builder Module Detail — Wave 0 Summary

**dnd-kit installed and three TDD RED-state test stubs created across frontend (Vitest) and backend (pytest) to anchor all Phase 13 implementation tasks**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-05-09T11:45:20Z
- **Completed:** 2026-05-09T11:47:29Z
- **Tasks:** 3/3
- **Files modified:** 5

## Accomplishments
- Installed @dnd-kit/core, @dnd-kit/sortable, and @dnd-kit/utilities into frontend/package.json (locked stack dependency)
- Created CourseBuilderPage.test.tsx and ModuleDetailPage.test.tsx — both fail at Vitest collection (import resolution error), establishing RED state for BUILD-01 through BUILD-05
- Created test_modules_phase13.py with 3 pytest.fail() stubs for BUILD-05 SSE endpoint — all 3 FAILED (not ERROR), matching Phase 12 Wave 0 pattern

## Task Commits

Each task was committed atomically:

1. **Task 1: Install dnd-kit and create __tests__ directory** - `7df5d26` (chore)
2. **Task 2: Create failing frontend test stubs (RED state)** - `bd1a03d` (test)
3. **Task 3: Create failing backend test stub (RED state)** - `19dad20` (test)

## Files Created/Modified
- `frontend/package.json` - Added @dnd-kit/core, @dnd-kit/sortable, @dnd-kit/utilities dependencies
- `frontend/package-lock.json` - Updated lockfile with dnd-kit transitive deps
- `frontend/src/pages/creator/__tests__/CourseBuilderPage.test.tsx` - 3 failing stubs (BUILD-01/02/03)
- `frontend/src/pages/creator/__tests__/ModuleDetailPage.test.tsx` - 2 failing stubs (BUILD-04/05)
- `backend/tests/test_modules_phase13.py` - 3 failing stubs for BUILD-05 SSE

## Decisions Made
- Frontend RED state via import of non-existent source file: vitest collection failure is the intentional RED state; no test body needed
- Backend RED state via pytest.fail() directly: produces FAILED not ERROR, consistent with Phase 12 Wave 0 decision from STATE.md
- venv activation required to run backend pytest (pyotp not on system path); future plans should activate venv before running pytest

## Deviations from Plan
None - plan executed exactly as written.

## Issues Encountered
- `python` command not found (macOS uses `python3`); resolved by using `python3 -m pytest` with venv activated — venv activation documented as pattern for future backend tasks

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All three test files in RED state; Wave 1 plans (13-02, 13-03) can implement CourseBuilderPage and ModuleDetailPage to make tests GREEN
- dnd-kit available for drag-and-drop module reordering in CourseBuilderPage
- Backend test stub ready for 13-04 (SSE endpoint implementation)

---
*Phase: 13-course-builder-module-detail*
*Completed: 2026-05-09*
