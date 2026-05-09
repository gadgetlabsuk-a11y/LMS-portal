---
phase: 15-ai-generation-infrastructure
plan: 01
subsystem: testing
tags: [tdd, pymupdf, sse, vitest, pytest, wave-0]

# Dependency graph
requires:
  - phase: 14-slide-builder
    provides: SSE infrastructure, slides.py routes, sse-starlette pattern
provides:
  - Wave 0 TDD RED stubs for AI-01 through AI-07 (5 backend pytest.fail stubs, 3 frontend vitest import stubs)
  - pymupdf==1.26.0 installed in backend venv
  - Test contracts for all Phase 15 AI generation plans to turn GREEN
affects: [15-02, 15-03, 15-04, 15-05, 15-06, 15-07]

# Tech tracking
tech-stack:
  added: [pymupdf==1.26.0]
  patterns: [Wave 0 TDD RED stubs — pytest.fail() for backend FAILED state; import non-existent files for frontend Cannot find module state]

key-files:
  created:
    - backend/tests/test_ai_phase15.py
    - frontend/src/hooks/__tests__/useSSEStream.test.ts
    - frontend/src/components/ai/__tests__/SideDrawer.test.tsx
    - frontend/src/components/ai/__tests__/AISuggestionsRail.test.tsx
  modified:
    - backend/requirements.txt

key-decisions:
  - "Backend Wave 0 stubs use pytest.fail() directly — produces FAILED not ERROR (consistent with Phase 12/13/14 pattern)"
  - "Frontend Wave 0 stubs import non-existent source files — vitest fails at collection with Cannot find module (consistent with Phase 13-01, 14-01 pattern)"
  - "reset_sse_state autouse fixture included — prevents anyio cross-loop RuntimeError in later SSE tests (STATE.md 12-02/13-02 decision)"
  - "pymupdf==1.26.0 installed and verified via import fitz; print(fitz.__version__) — 1.26.0 confirmed"

patterns-established:
  - "Wave 0 TDD pattern: 5 pytest.fail() backend stubs + 3 frontend import-fail stubs establish test contracts before any implementation"

requirements-completed: [AI-01, AI-02, AI-03, AI-04, AI-05, AI-06, AI-07]

# Metrics
duration: 18min
completed: 2026-05-09
---

# Phase 15 Plan 01: Wave 0 AI Generation Infrastructure Stubs Summary

**5 backend pytest.fail() stubs + 3 frontend import-fail stubs establish TDD RED contracts for AI-01 through AI-07, with PyMuPDF 1.26.0 installed**

## Performance

- **Duration:** 18 min
- **Started:** 2026-05-09T21:03:16Z
- **Completed:** 2026-05-09T21:21:46Z
- **Tasks:** 2/2
- **Files modified:** 5

## Accomplishments

- Installed pymupdf==1.26.0 in backend venv — `import fitz; print(fitz.__version__)` returns `1.26.0`
- Created `backend/tests/test_ai_phase15.py` with 5 stubs covering AI-03, AI-04 (x2), AI-05, AI-07 — all use `pytest.fail()` directly (FAILED not ERROR)
- Created 3 frontend test stub files importing non-existent components — vitest collection fails with Cannot find module (correct RED state)
- New test directories created: `frontend/src/hooks/__tests__/` and `frontend/src/components/ai/__tests__/`

## Task Commits

Each task was committed atomically:

1. **Task 1: Install PyMuPDF + backend test stubs** - `3d73457` (test)
2. **Task 2: Frontend test stubs (RED imports)** - `5f421eb` (test)

**Plan metadata:** (docs commit below)

## Files Created/Modified

- `backend/requirements.txt` - Added `pymupdf==1.26.0` after python-docx line (file-processing group)
- `backend/tests/test_ai_phase15.py` - 5 pytest.fail() stubs: AI-03, AI-04 (PDF + DOCX), AI-05, AI-07; autouse reset_sse_state fixture
- `frontend/src/hooks/__tests__/useSSEStream.test.ts` - Imports non-existent `../useSSEStream` (AI-01 RED state)
- `frontend/src/components/ai/__tests__/SideDrawer.test.tsx` - Imports non-existent `../SideDrawer` (AI-02 RED state)
- `frontend/src/components/ai/__tests__/AISuggestionsRail.test.tsx` - Imports non-existent `../AISuggestionsRail` (AI-06 RED state)

## Decisions Made

- Backend Wave 0 stubs use `pytest.fail()` directly — produces FAILED not ERROR (consistent with Phase 12/13/14 pattern from STATE.md)
- Frontend Wave 0 stubs import non-existent source files — vitest fails at collection with "Cannot find module" (consistent with Phase 13-01, 14-01 pattern)
- `reset_sse_state` autouse fixture included — prevents anyio cross-loop RuntimeError in later SSE tests (STATE.md 12-02/13-02 decision)
- `pymupdf==1.26.0` installed and verified via `import fitz; print(fitz.__version__)` — 1.26.0 confirmed

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- Frontend `npm run test` script does not exist — correct script is `npm run test:unit` (discovered during verification; no plan change required, same vitest runner)

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Wave 0 RED stubs in place — Phase 15-02 can immediately start turning backend stubs GREEN
- PyMuPDF installed — AI-04 PDF extraction implementation can proceed
- Frontend test directories created — AI-01 (useSSEStream), AI-02 (SideDrawer), AI-06 (AISuggestionsRail) implementation can begin
- No blockers

## Self-Check: PASSED

- FOUND: `backend/tests/test_ai_phase15.py`
- FOUND: `frontend/src/hooks/__tests__/useSSEStream.test.ts`
- FOUND: `frontend/src/components/ai/__tests__/SideDrawer.test.tsx`
- FOUND: `frontend/src/components/ai/__tests__/AISuggestionsRail.test.tsx`
- FOUND: `pymupdf==1.26.0` in `backend/requirements.txt`
- FOUND: commit `3d73457` (backend stubs + PyMuPDF)
- FOUND: commit `5f421eb` (frontend stubs)
- VERIFIED: `import fitz; print(fitz.__version__)` = `1.26.0`

---
*Phase: 15-ai-generation-infrastructure*
*Completed: 2026-05-09*
