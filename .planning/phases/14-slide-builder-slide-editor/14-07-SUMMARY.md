---
phase: 14-slide-builder-slide-editor
plan: "07"
subsystem: ui
tags: [react, typescript, slide-builder, ai-outline, wizard]

# Dependency graph
requires:
  - phase: 14-slide-builder-slide-editor
    provides: SlideOutlineWizard component (fully implemented, unit-tested, 261 lines)
provides:
  - SlideBuilderPage toolbar "AI Outline" button wired to SlideOutlineWizard
  - wizardOpen state controls modal lifecycle
  - fetchSlides() named function enables post-commit slide strip refresh
  - SLIDE-12 end-to-end reachability: creator can launch AI outline wizard from SlideBuilderPage UI
affects: [14-slide-builder-slide-editor, phase-15]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Named fetchSlides() function pattern: extract useEffect body so onCommitted callbacks can re-fetch without duplicating fetch logic"
    - "vi.mock('@/context/AuthContext') in page tests when page renders a component that calls useAuth()"

key-files:
  created: []
  modified:
    - frontend/src/pages/creator/SlideBuilderPage.tsx
    - frontend/src/pages/creator/__tests__/SlideBuilderPage.test.tsx

key-decisions:
  - "SlideBuilderPage renders SlideOutlineWizard unconditionally (open=false returns null) — safe per component contract; triggers useAuth() call at render time requiring AuthContext mock in tests"
  - "vi.mock('@/context/AuthContext') added to SlideBuilderPage.test.tsx — same pattern as SlideOutlineWizard.test.tsx; direct consequence of wiring wizard into page"
  - "anchorSlideId = slides[slides.length-1].id if slides exist, else 0 — wizard appends new slides after last existing slide or at position 0 for empty video"

patterns-established:
  - "Named fetch function pattern: const fetchSlides = () => { ... } + useEffect(() => { fetchSlides() }, [dep]) — allows external callers (onCommitted) to re-trigger fetch without duplicating logic"

requirements-completed:
  - SLIDE-12

# Metrics
duration: 9min
completed: 2026-05-09
---

# Phase 14 Plan 07: Gap Closure — Wire SlideOutlineWizard into SlideBuilderPage Summary

**SlideOutlineWizard wired into SlideBuilderPage with "AI Outline" toolbar button, wizardOpen state, and onCommitted slide refresh — SLIDE-12 now reachable from UI**

## Performance

- **Duration:** ~9 min
- **Started:** 2026-05-09T17:28:19Z
- **Completed:** 2026-05-09T17:37:42Z
- **Tasks:** 2/2 completed
- **Files modified:** 2

## Accomplishments

- Added `SlideOutlineWizard` import and `wizardOpen` state to `SlideBuilderPage`
- Extracted `fetchSlides()` named function so `onCommitted` callback can refresh the slide strip after wizard commits
- Added "AI Outline" button (`data-testid="ai-outline-btn"`) to toolbar, rendered before "+ Add Slide"
- Rendered `<SlideOutlineWizard>` with all required props (`open`, `videoId`, `anchorSlideId`, `onClose`, `onCommitted`)
- Fixed test failures: added `vi.mock('@/context/AuthContext')` to `SlideBuilderPage.test.tsx` — all 18 tests pass

## Task Commits

Each task was committed atomically:

1. **Task 1: Wire SlideOutlineWizard into SlideBuilderPage** - `940c742` (feat)
2. **Task 2 (auto-fix): Add useAuth mock to SlideBuilderPage tests** - `37d9149` (fix)

**Plan metadata:** (docs commit — see final_commit step)

## Files Created/Modified

- `frontend/src/pages/creator/SlideBuilderPage.tsx` — Added wizard import, `wizardOpen` state, `fetchSlides()` function, "AI Outline" toolbar button, `<SlideOutlineWizard>` render
- `frontend/src/pages/creator/__tests__/SlideBuilderPage.test.tsx` — Added `vi.mock('@/context/AuthContext')` to fix test failures caused by wizard wiring

## Decisions Made

- `SlideOutlineWizard` renders `null` when `open=false` per its component contract, so it is safe to always render it in the JSX tree — but it still calls `useAuth()` at React render time regardless of `open` prop, requiring `AuthContext` mock in tests
- `anchorSlideId` set to last slide's `.id` (or `0` if no slides) — wizard will append new slides after the last existing one

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] SlideBuilderPage tests failed after wizard wiring**
- **Found during:** Task 2 (TypeScript and test suite verification)
- **Issue:** Rendering `SlideBuilderPage` now always renders `SlideOutlineWizard` (open=false), which calls `useAuth()` internally. The test's `MemoryRouter` wrapper does not include `AuthProvider`, so all 3 tests threw `useAuth must be used within AuthProvider`
- **Fix:** Added `vi.mock('@/context/AuthContext', () => ({ useAuth: () => ({ token: 'test-token' }) }))` to `SlideBuilderPage.test.tsx`, matching the pattern used in `SlideOutlineWizard.test.tsx`
- **Files modified:** `frontend/src/pages/creator/__tests__/SlideBuilderPage.test.tsx`
- **Verification:** `npx vitest run src/components/slide/__tests__ src/pages/creator/__tests__` — 18/18 tests pass
- **Committed in:** `37d9149` (separate fix commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - Bug)
**Impact on plan:** Necessary fix — wizard wiring directly caused test failures. Pattern matches existing wizard test convention. No scope creep.

## Issues Encountered

- TypeScript `npx tsc --noEmit` shows pre-existing errors in `SlideCanvas.tsx`, `SlideEditorPage.tsx`, `NarrationTab.tsx`, and other slide components (TS6133 unused imports, TS2322 react-grid-layout Layout type mismatches, TS2339 missing `.token` property on `AuthContextValue`). None were introduced by this plan. Per scope boundary rules, logged here but not fixed.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- SLIDE-12 is now reachable from the UI: creator can click "AI Outline" in `SlideBuilderPage` toolbar to launch the 4-step wizard
- Pre-existing TypeScript errors in `SlideCanvas.tsx` and `SlideEditorPage.tsx` (Layout type mismatch, undo handler type mismatch) should be addressed before Phase 15 to prevent build failures
- All 18 slide component + page tests pass

---
*Phase: 14-slide-builder-slide-editor*
*Completed: 2026-05-09*
