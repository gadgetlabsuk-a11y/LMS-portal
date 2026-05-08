---
phase: 09-vite-migration
plan: "06"
subsystem: ui
tags: [react, typescript, vite, react-router, creator-portal, learner-portal]

requires:
  - phase: 09-04
    provides: Auth guards, layout shells, LoginPage — all creator/learner pages sit inside these layouts
  - phase: 09-03
    provides: Card, Button, Badge, Modal common components used by creator/learner pages
  - phase: 09-02
    provides: api service, AuthContext, ToastContext — used by all page components

provides:
  - CreatorDashboard: stats overview + recent courses table for creator portal
  - CreatorLearners: filterable learner enrollment table for creator portal
  - LearnerCatalogue: paginated, searchable course grid for learner portal
  - CourseDetail: course detail view with ModuleAccordion content tree
  - ModuleAccordion: reusable expandable module/lesson accordion sub-component
  - CourseViewerPage: full-screen course iframe player with back navigation

affects: [09-07, 09-08, App.tsx routing — all 6 pages must be imported in the router]

tech-stack:
  added: []
  patterns:
    - useParams for route :id extraction (not useLocation + pathname.split)
    - navigate(-1) for back navigation (not window.history.back())
    - API_BASE exported from api.ts for direct URL construction in iframe src
    - Debounced search with setTimeout in useEffect (300ms)
    - Pagination via page state + setCourses append/replace pattern

key-files:
  created:
    - frontend/src/pages/creator/CreatorDashboard.tsx
    - frontend/src/pages/creator/CreatorLearners.tsx
    - frontend/src/pages/learn/LearnerCatalogue.tsx
    - frontend/src/pages/learn/CourseDetail.tsx
    - frontend/src/pages/learn/ModuleAccordion.tsx
    - frontend/src/pages/CourseViewerPage.tsx
  modified:
    - frontend/src/services/api.ts

key-decisions:
  - "CourseDetail and CourseViewerPage use useParams (not useLocation + pathname.split) — SPA-correct and avoids hash/basename edge cases"
  - "CourseViewerPage uses navigate(-1) not window.history.back() — keeps navigation within React Router history stack"
  - "API_BASE exported from api.ts so CourseViewerPage can build the iframe src correctly without duplicating env detection"
  - "ModuleAccordion accepts optional onLessonClick prop for future lesson-click wiring without a breaking change"

patterns-established:
  - "useParams pattern: const { id } = useParams<{ id: string }>() — type-safe route param extraction"
  - "navigate(-1) for back — consistent browser-back pattern across all page components"

requirements-completed:
  - INFRA-04

duration: 7min
completed: 2026-05-08
---

# Phase 09 Plan 06: Vite Migration — Creator and Learner Portal Pages Summary

**6 creator/learner/course portal pages extracted from monolith into typed TypeScript files, completing the 27-component migration across Plans 02–06**

## Performance

- **Duration:** ~7 min
- **Started:** 2026-05-08T21:28:07Z
- **Completed:** 2026-05-08T21:35:00Z
- **Tasks:** 2/2
- **Files modified:** 7

## Accomplishments
- Extracted 2 creator portal pages (CreatorDashboard, CreatorLearners) with full TypeScript types
- Extracted 4 learner/course pages (LearnerCatalogue, CourseDetail, ModuleAccordion, CourseViewerPage)
- Replaced all monolith navigation anti-patterns: `useLocation + pathname.split` → `useParams`, `window.history.back()` → `navigate(-1)`
- Build passes and all 6 unit tests pass

## Task Commits

Each task was committed atomically:

1. **Task 1: Extract CreatorDashboard and CreatorLearners** - `0942b24` (feat)
2. **Task 2: Extract LearnerCatalogue, CourseDetail, ModuleAccordion, CourseViewerPage** - `d554e6b` (feat)

**Plan metadata:** (docs commit — see below)

## Files Created/Modified
- `frontend/src/pages/creator/CreatorDashboard.tsx` - Loads /creator/stats and /courses, stat cards + recent courses table
- `frontend/src/pages/creator/CreatorLearners.tsx` - Loads /creator/learners with course_id filter, learner enrollment table
- `frontend/src/pages/learn/LearnerCatalogue.tsx` - Paginated course grid with debounced search, skeleton loading
- `frontend/src/pages/learn/CourseDetail.tsx` - Course detail with ModuleAccordion list, useParams for :id
- `frontend/src/pages/learn/ModuleAccordion.tsx` - Toggleable module/lesson accordion, first module open by default
- `frontend/src/pages/CourseViewerPage.tsx` - Full-screen iframe course player, navigate(-1) back
- `frontend/src/services/api.ts` - Exported API_BASE constant for iframe src construction

## Decisions Made
- `useParams` replaces `useLocation + pathname.split` in CourseDetail and CourseViewerPage — SPA-correct and avoids edge cases with base path
- `navigate(-1)` replaces `window.history.back()` in CourseViewerPage — keeps navigation inside the React Router stack
- `API_BASE` exported from api.ts to avoid duplicating `import.meta.env.PROD` logic in CourseViewerPage

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Replaced useLocation + pathname.split with useParams in CourseDetail and CourseViewerPage**
- **Found during:** Task 2 (Extract learner/course pages)
- **Issue:** Monolith used `const courseId = pathname.split('/').pop()` — fragile and wrong for a React Router SPA with a `/lms` base path
- **Fix:** Used `const { id: courseId } = useParams<{ id: string }>()` as specified in the plan
- **Files modified:** frontend/src/pages/learn/CourseDetail.tsx, frontend/src/pages/CourseViewerPage.tsx
- **Verification:** Build passes, useParams confirmed in grep verification
- **Committed in:** d554e6b (Task 2 commit)

**2. [Rule 1 - Bug] Replaced window.history.back() with navigate(-1) in CourseViewerPage**
- **Found during:** Task 2 (Extract CourseViewerPage)
- **Issue:** Monolith used `window.history.back()` — bypasses React Router history stack
- **Fix:** Used `navigate(-1)` from react-router-dom
- **Files modified:** frontend/src/pages/CourseViewerPage.tsx
- **Verification:** grep returns no matches for window.history in new files
- **Committed in:** d554e6b (Task 2 commit)

**3. [Rule 2 - Missing Critical] Exported API_BASE from api.ts**
- **Found during:** Task 2 (CourseViewerPage iframe src construction)
- **Issue:** CourseViewerPage needs the API base URL for the iframe src but API_BASE was module-private
- **Fix:** Added `export` to the API_BASE constant in api.ts
- **Files modified:** frontend/src/services/api.ts
- **Verification:** Build passes, no TypeScript errors
- **Committed in:** d554e6b (Task 2 commit)

---

**Total deviations:** 3 auto-fixed (2 Rule 1 bugs, 1 Rule 2 missing critical)
**Impact on plan:** All auto-fixes necessary for SPA correctness. No scope creep.

## Issues Encountered
None — build and tests passed on first attempt.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All 27 monolith components are now in individual .tsx files across Plans 02–06
- App.tsx router needs to be wired up (likely Plan 07) — all 6 page exports are ready to import
- Build is clean, 6 unit tests pass

---
*Phase: 09-vite-migration*
*Completed: 2026-05-08*
