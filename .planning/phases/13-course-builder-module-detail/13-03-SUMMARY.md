---
phase: 13-course-builder-module-detail
plan: "03"
subsystem: ui
tags: [react, dnd-kit, typescript, course-builder, drag-drop]

# Dependency graph
requires:
  - phase: 13-01
    provides: dnd-kit installed, TDD RED stubs for CourseBuilderPage
  - phase: 12-04
    provides: CreatorLayout, ProtectedRoute, builder stub route
provides:
  - CourseBuilderPage (two-panel layout: tree rail + module overview)
  - CourseTreeRail (nested tree with status pills, click navigation)
  - ModuleOverviewList (dnd-kit drag-drop for module and video reorder)
  - Shared builder types (BuilderModule, BuilderVideo, BuilderQuiz)
affects:
  - 13-04 (ModuleDetailPage uses same tree rail and builder types)
  - 13-05 (VideoDetailPage navigated to from CourseTreeRail)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Separate DndContext per module for video reorder (prevents cross-module drag)
    - PointerSensor activationConstraint distance:8 for click/drag coexistence
    - Namespaced dnd-kit IDs ("module-{id}", "video-{id}") to prevent ID collision
    - Shared types file (builder/types.ts) avoids TS2719 duplicate-name errors
    - vi.mock for api service in component tests; findByTestId for async render assertions

key-files:
  created:
    - frontend/src/components/builder/CourseTreeRail.tsx
    - frontend/src/components/builder/ModuleOverviewList.tsx
    - frontend/src/components/builder/types.ts
    - frontend/src/pages/creator/CourseBuilderPage.tsx
  modified:
    - frontend/src/pages/creator/__tests__/CourseBuilderPage.test.tsx

key-decisions:
  - "Shared builder/types.ts exports BuilderModule, BuilderVideo, BuilderQuiz — avoids TS2719 when same interface name defined in multiple files"
  - "Badge component uses variant prop (not className) — plan pseudocode used className; status pill wrapped in <span data-testid> to expose testid"
  - "Test file updated with vi.mock + findByTestId (async) + module fixture for status-pill test — API mock required because page shows loading state until fetch resolves"
  - "SortableModuleRow contains its own per-module DndContext + useSensors call — separate sensor instance prevents drag events from leaking across module boundaries"

patterns-established:
  - "Builder component types: import from @/components/builder/types rather than defining locally"
  - "Test async render: use findByTestId not getByTestId when component has a loading state gate"

requirements-completed:
  - BUILD-01
  - BUILD-02
  - BUILD-03
  - BUILD-06

# Metrics
duration: 3min
completed: 2026-05-09
---

# Phase 13 Plan 03: Course Builder Page Summary

**dnd-kit two-panel CourseBuilderPage with left-rail tree (CourseTreeRail) and drag-reorder module/video list (ModuleOverviewList); all 3 tests GREEN**

## Performance

- **Duration:** 3 min
- **Started:** 2026-05-09T11:49:37Z
- **Completed:** 2026-05-09T11:52:57Z
- **Tasks:** 3/3
- **Files modified:** 5

## Accomplishments

- CourseTreeRail renders nested module/video/quiz tree with status pills and click-to-navigate per module
- ModuleOverviewList provides dnd-kit drag-drop for module reorder (outer context) and per-module video reorder (separate inner DndContext per module)
- CourseBuilderPage fetches course tree on mount, holds optimistic state, renders both panels
- All 3 CourseBuilderPage.test.tsx tests GREEN; no regressions in full suite

## Task Commits

1. **Task 1: CourseTreeRail** - `cea2e3e` (feat)
2. **Task 2: ModuleOverviewList** - `b1c6567` (feat)
3. **Task 3: CourseBuilderPage + tests GREEN** - `23b9e24` (feat)

## Files Created/Modified

- `frontend/src/components/builder/CourseTreeRail.tsx` - Left-rail tree with module/video/quiz rows and status pills
- `frontend/src/components/builder/ModuleOverviewList.tsx` - dnd-kit sortable module list with per-module video sub-lists
- `frontend/src/components/builder/types.ts` - Shared BuilderModule, BuilderVideo, BuilderQuiz types
- `frontend/src/pages/creator/CourseBuilderPage.tsx` - Two-panel builder page with data fetch and optimistic state
- `frontend/src/pages/creator/__tests__/CourseBuilderPage.test.tsx` - Updated with vi.mock, async assertions, module fixture

## Decisions Made

- **Shared types file:** Badge component uses `variant` prop not `className`, and TypeScript raised TS2719 ("two different types with this name") when `Module` was defined locally in both `CourseBuilderPage.tsx` and `ModuleOverviewList.tsx`. Fixed by extracting to `builder/types.ts` with `BuilderModule`/`BuilderVideo`/`BuilderQuiz` exports imported by all three files.
- **Status pill testid:** Badge doesn't accept `data-testid` as a prop (only `variant` and `children`). Wrapped Badge in `<span data-testid="module-status-pill">` as the plan suggested.
- **Test mock required:** `CourseBuilderPage` shows a loading state until the API fetch resolves. Without `vi.mock('@/services/api')`, tests saw the loading spinner and couldn't find `course-tree-rail` or `module-overview-list`. Added api mock + `findByTestId` (async) + module fixture for the status-pill test.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed TS2719 type collision with shared types.ts**
- **Found during:** Task 3 (TypeScript check)
- **Issue:** Two separate `Module` interface declarations (one in CourseBuilderPage, one in ModuleOverviewList) caused TS2719 — TypeScript treats same-named interfaces from different modules as unrelated types even when structurally identical
- **Fix:** Extracted shared types to `frontend/src/components/builder/types.ts`; all three builder files import `BuilderModule`, `BuilderVideo`, `BuilderQuiz` from the shared file
- **Files modified:** CourseTreeRail.tsx, ModuleOverviewList.tsx, CourseBuilderPage.tsx, types.ts (new)
- **Verification:** `npx tsc --noEmit` returns zero errors for new files
- **Committed in:** cea2e3e, b1c6567, 23b9e24

**2. [Rule 1 - Bug] Updated test file to use vi.mock and async assertions**
- **Found during:** Task 3 (first test run)
- **Issue:** Tests used synchronous `getByTestId` but page renders a loading state until API resolves; without API mock the fetch always rejects and the page never leaves the loading state
- **Fix:** Added `vi.mock('@/services/api')` with mockGet factory, updated assertions to `await screen.findByTestId(...)`, added module fixture for status-pill test
- **Files modified:** CourseBuilderPage.test.tsx
- **Verification:** All 3 tests GREEN, 11/11 suite tests passing
- **Committed in:** 23b9e24

---

**Total deviations:** 2 auto-fixed (1 type collision bug, 1 test environment bug)
**Impact on plan:** Both fixes necessary for correctness. No scope creep.

## Issues Encountered

- Badge component interface: plan pseudocode used `className` prop but actual `Badge.tsx` uses `variant: 'info' | 'success' | 'warning' | 'danger'`. Adapted all badge usage to correct API.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- CourseBuilderPage, CourseTreeRail, ModuleOverviewList all complete and tested
- Ready for Plan 13-04: ModuleDetailPage (uses CourseTreeRail and builder types)
- Ready for Plan 13-05: VideoDetailPage (navigated to from CourseTreeRail video rows)
- Builder types (BuilderModule, BuilderVideo, BuilderQuiz) available for downstream plans

---
*Phase: 13-course-builder-module-detail*
*Completed: 2026-05-09*
