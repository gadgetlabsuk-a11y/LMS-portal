---
phase: 18-preview-publish
plan: "04"
subsystem: frontend-publish-flow
tags: [publish, preflight, modal, course-builder, PUBLISH-01, PUBLISH-02, PUBLISH-03, PUBLISH-04, PUBLISH-05, PUBLISH-06, PUBLISH-08]
dependency_graph:
  requires: [18-03]
  provides: [publish-flow-frontend, preflight-modal, archive-button]
  affects: [frontend/src/pages/creator/CourseBuilderPage.tsx]
tech_stack:
  added: []
  patterns: [nested-modal-pattern, api-response-json, tdd-red-green]
key_files:
  created:
    - frontend/src/components/publish/PreflightModal.tsx
    - frontend/src/components/publish/PublishConfirmModal.tsx
    - frontend/src/components/publish/__tests__/PreflightModal.test.tsx
  modified:
    - frontend/src/pages/creator/CourseBuilderPage.tsx
    - frontend/src/pages/creator/__tests__/CourseBuilderPage.test.tsx
decisions:
  - "api.get returns Response (not { data: T }) — PreflightModal uses .json() not .data; plan's interface docs were incorrect"
  - "PublishConfirmModal embedded as nested Modal inside PreflightModal — no separate standalone component needed"
  - "Course status fetched via GET /api/courses/:id on mount in CourseBuilderPage; archive-btn visibility driven by courseStatus state"
  - "CourseBuilderPage test mock updated with extra mockResolvedValueOnce for new course status fetch (first api.get call)"
metrics:
  duration: "~5 min"
  completed_date: "2026-05-11"
  tasks: 2/2
  files: 5
---

# Phase 18 Plan 04: Publish Flow Frontend Summary

Frontend publish flow with PreflightModal (colour-coded checklist), PublishConfirmModal (nested confirm), and Publish/Archive buttons wired in CourseBuilderPage header.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Create PreflightModal and PublishConfirmModal | d08aed1 | PreflightModal.tsx, PublishConfirmModal.tsx, PreflightModal.test.tsx |
| 2 | Wire Publish/Archive buttons in CourseBuilderPage | 0cfe0c1 | CourseBuilderPage.tsx, CourseBuilderPage.test.tsx |

## Decisions Made

- `api.get` returns `Promise<Response>` (not `{ data: T }`) — PreflightModal uses `.json()` method. Plan interface docs showed `api.get<T>(url): Promise<{ data: T }>` which was wrong. Auto-fixed as Rule 1.
- `PublishConfirmModal` is embedded as a nested `<Modal>` inside `PreflightModal`. No separate standalone component needed. `PublishConfirmModal.tsx` is a thin placeholder for future extraction.
- Course status fetched from `GET /api/courses/:id` on mount. `archive-btn` renders only when `courseStatus === 'published' || courseStatus === 'has_unpublished_changes'`.
- CourseBuilderPage test "renders status pill" updated: new first `api.get` call (course status) requires an additional `mockResolvedValueOnce` before the modules call.

## Verification Results

- PreflightModal: 5/5 tests pass (PUBLISH-02, PUBLISH-03, PUBLISH-04, PUBLISH-05, PUBLISH-06)
- CourseBuilderPage: 5/5 tests pass including new PUBLISH-01 assertion
- Full frontend suite: 71/72 pass (1 pre-existing useSSEStream cancel() failure, documented in STATE.md 15-04)
- TypeScript build: no errors in publish/* files; pre-existing errors in slide/* and ai/* are out of scope

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] api.get returns Response, not { data: T }**
- **Found during:** Task 1 build verification
- **Issue:** Plan's interface docs stated `api.get<T>(url): Promise<{ data: T }>` but actual `api.ts` returns `Promise<Response>` with `.json()` method
- **Fix:** Removed type arguments from `api.get` calls; replaced `.data` access with `await res.json()`; updated test mocks from `{ data: {...} }` to `{ json: async () => ({...}) }` to match real Response shape
- **Files modified:** PreflightModal.tsx, PreflightModal.test.tsx
- **Commit:** d08aed1

**2. [Rule 1 - Bug] CourseBuilderPage test mock ordering broken by new course status fetch**
- **Found during:** Task 2 test run
- **Issue:** Adding `GET /courses/:id` as first fetch broke test that used `mockResolvedValueOnce` for modules
- **Fix:** Added `mockResolvedValueOnce({ json: async () => ({ status: 'draft' }) })` as new first mock call
- **Files modified:** CourseBuilderPage.test.tsx
- **Commit:** 0cfe0c1

## Self-Check: PASSED
