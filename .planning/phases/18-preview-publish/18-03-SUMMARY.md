---
phase: 18-preview-publish
plan: 03
subsystem: ui
tags: [react, typescript, react-router, vitest, iframe]

# Dependency graph
requires:
  - phase: 18-02
    provides: "Backend /api/courses/:id/player endpoint with draft-aware rendering (PREVIEW-02)"
provides:
  - CoursePreviewPage.tsx — full-screen preview with amber watermark and backend learner iframe
  - /creator/courses/:id/preview route in App.tsx behind ProtectedRoute(creatorRoute)
  - Preview button (data-testid=preview-mode-btn) in CourseBuilderPage header
  - 3 real PreviewMode tests passing (PREVIEW-01, PREVIEW-02, PREVIEW-03)
affects: [18-04, 18-05]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Full-screen route without CreatorLayout: ProtectedRoute(creatorRoute) wrapping only — same pattern as CourseViewerPage"
    - "iframe-as-renderer: reuse backend-rendered player via iframe rather than duplicate React renderer"
    - "returnTo pattern: encodeURIComponent on navigate, decodeURIComponent with useSearchParams on destination"

key-files:
  created:
    - frontend/src/pages/creator/CoursePreviewPage.tsx
    - frontend/src/pages/creator/__tests__/PreviewMode.test.tsx (replaced stubs)
  modified:
    - frontend/src/App.tsx
    - frontend/src/pages/creator/CourseBuilderPage.tsx
    - frontend/src/pages/creator/__tests__/CourseBuilderPage.test.tsx

key-decisions:
  - "CoursePreviewPage wraps iframe directly (not CourseViewerPage as component) — avoids nested iframe and matches backend player src pattern exactly"
  - "Fixed watermark uses z-index 1000 with position:fixed so it sits above iframe regardless of iframe scroll state"
  - "Preview button uses inline styles (consistent with CourseBuilderPage's existing inline style layout approach)"
  - "decodeURIComponent on returnTo required — caller uses encodeURIComponent; raw useSearchParams().get() would corrupt paths containing slashes"
  - "act() warning from React Router v6 MemoryRouter is pre-existing / benign — test still passes and verifies navigation outcome"

patterns-established:
  - "Pattern: preview-watermark always rendered with data-testid for test assertions"
  - "Pattern: exit navigation via returnTo query param with encode/decode cycle"

requirements-completed: [PREVIEW-01, PREVIEW-02, PREVIEW-03]

# Metrics
duration: ~33min
completed: 2026-05-11
---

# Phase 18 Plan 03: CoursePreviewPage Frontend Summary

**CoursePreviewPage with fixed amber watermark overlaying the backend learner iframe, Preview button in CourseBuilderPage, and route registered in App.tsx — PREVIEW-01/02/03 all GREEN**

## Performance

- **Duration:** ~33 min
- **Started:** 2026-05-10T23:20:27Z
- **Completed:** 2026-05-10T23:53:48Z
- **Tasks:** 2/2
- **Files modified:** 5

## Accomplishments

- CoursePreviewPage.tsx delivers fixed amber watermark banner (data-testid=preview-watermark) with "Preview Mode — Draft" text over the full-viewport learner iframe — PREVIEW-01
- Backend learner player reused via iframe (`${API_BASE}/api/courses/${id}/player`) giving all block types, answerable quizzes, and narration scripts without a new renderer — PREVIEW-02
- Exit Preview button (data-testid=exit-preview-btn) decodes returnTo query param and navigates back to caller — PREVIEW-03
- /creator/courses/:id/preview route added to App.tsx behind ProtectedRoute(creatorRoute) with no CreatorLayout wrapper (full-screen pattern)
- Preview button (data-testid=preview-mode-btn) added to CourseBuilderPage header, navigates with encoded returnTo
- All 7 tests pass: 3 PreviewMode + 4 CourseBuilderPage (including new preview-mode-btn assertion)

## Task Commits

Each task was committed atomically:

1. **Task 1: Create CoursePreviewPage with watermark and learner iframe** - `cd8027f` (feat)
2. **Task 2: PreviewMode tests, App.tsx route, CourseBuilderPage Preview button** - `037b91e` (feat)

**Plan metadata:** (docs commit — see below)

## Files Created/Modified

- `frontend/src/pages/creator/CoursePreviewPage.tsx` — New: full-screen page with fixed amber watermark div + backend player iframe
- `frontend/src/pages/creator/__tests__/PreviewMode.test.tsx` — Replaced stubs with 3 real assertions (watermark, returnTo nav, iframe src)
- `frontend/src/App.tsx` — Added CoursePreviewPage import + /creator/courses/:id/preview route
- `frontend/src/pages/creator/CourseBuilderPage.tsx` — Added useNavigate, handlePreview, Preview button with data-testid
- `frontend/src/pages/creator/__tests__/CourseBuilderPage.test.tsx` — Added preview button assertion

## Decisions Made

- **iframe-not-component:** CoursePreviewPage renders the iframe directly rather than wrapping CourseViewerPage. Wrapping CourseViewerPage would nest two iframes (CourseViewerPage is itself an iframe wrapper). Replicating the iframe pattern directly with a watermark overlay is the correct approach.
- **z-index 1000 on watermark:** Ensures the fixed banner always sits above the iframe regardless of iframe scroll or pointer events.
- **decodeURIComponent required:** CourseBuilderPage's handlePreview uses encodeURIComponent when building the preview URL. Without decode on the receiving end, paths with slashes get corrupted.
- **React Router act() warning:** The `exit preview button navigates to returnTo` test produces a benign act() warning from MemoryRouter. The test passes and verifies the correct navigation outcome. This is a pre-existing React Router v6 testing pattern in this codebase.

## Deviations from Plan

None — plan executed exactly as written. TypeScript compiled without errors and all 7 tests pass on first attempt.

## Issues Encountered

- iCloud Drive I/O latency caused vitest to take ~592 seconds to complete 7 tests (setup 234s + environment 763s). This is a pre-existing known limitation documented in STATE.md. TypeScript compilation (exit code 0) was used as the intermediate verification signal during the wait.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- PREVIEW-01, PREVIEW-02, PREVIEW-03 all GREEN
- CoursePreviewPage is live and wired — creators can click Preview in CourseBuilderPage to launch full-screen preview with watermark
- Ready for Plan 18-04 (publish flow) and Plan 18-05 (browser verification)

---
*Phase: 18-preview-publish*
*Completed: 2026-05-11*
