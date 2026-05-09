---
phase: 13-course-builder-module-detail
plan: "04"
subsystem: frontend
tags: [module-detail, ai-streaming, sse, routing, course-builder]
dependency_graph:
  requires: [13-01, 13-02, 13-03]
  provides: [ModuleDetailPage, CourseBuilderPage-route, ModuleDetailPage-route]
  affects: [frontend/src/App.tsx, frontend/src/pages/creator/]
tech_stack:
  added: []
  patterns: [fetch-ReadableStream-SSE, api.get/put, React-useState-useEffect, FormData-upload]
key_files:
  created:
    - frontend/src/pages/creator/ModuleDetailPage.tsx
  modified:
    - frontend/src/App.tsx
    - frontend/src/pages/creator/__tests__/ModuleDetailPage.test.tsx
decisions:
  - Test mock uses vi.mock('@/services/api') with mocked api.get returning module fixture — same pattern as CourseBuilderPage tests
  - Input/Textarea/Select/Button all spread ...props to DOM elements so data-testid passes through without wrapper divs
key_decisions:
  - vi.mock for api module required in ModuleDetailPage tests (api.get called on mount triggers async state updates)
  - All common components (Input/Textarea/Select/Button) forward ...props so data-testid works directly on components
metrics:
  duration: ~5 min
  completed: "2026-05-09"
  tasks_completed: 2
  files_modified: 3
---

# Phase 13 Plan 04: ModuleDetailPage + Route Wiring Summary

**One-liner:** Module edit form with GET/PUT API calls and fetch+ReadableStream SSE AI description generation, plus both creator routes wired into App.tsx replacing the builder stub.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | ModuleDetailPage — form + AI streaming + tests GREEN | 91a55f5 | ModuleDetailPage.tsx, ModuleDetailPage.test.tsx |
| 2 | Wire App.tsx routes — replace stub, add ModuleDetailPage | 551f1c0 | App.tsx |

## What Was Built

### ModuleDetailPage.tsx
Full module edit form with:
- `data-testid` attributes on all key fields: `module-title-input`, `module-description-textarea`, `module-duration-input`, `module-unlock-rule-select`, `ai-generate-description-btn`
- GET `/api/modules/:moduleId` on mount via `api.get` — populates all form fields
- PUT `/api/modules/:moduleId` on form submit — sends title, description, learning_objectives (array), estimated_duration_minutes, unlock_rule, status
- AI description generation panel: fetch + ReadableStream SSE to `/api/modules/:id/ai/generate-description` with prompt, tone_preset, optional document_url
- Optional document upload: FormData POST to `/api/uploads` before AI request; passes returned URL as `document_url`
- AbortController ref for stream cancellation ("Stop" button)
- Learning objectives: up to 5 items, add/remove, maps to `learning_objectives: string[]` API field
- Inline save feedback: "Saved" (green) or "Save failed" (red), auto-clears after 3s

### App.tsx
- Replaced `<div>Course Builder Stub</div>` with `<CourseBuilderPage />` at `/creator/courses/:id/builder`
- Added new route `/creator/courses/:id/modules/:moduleId` rendering `<ModuleDetailPage />`
- Both wrapped in `<CreatorLayout><ProtectedRoute creatorRoute>`

## Verification

- ModuleDetailPage.test.tsx: 2/2 tests GREEN
- Full frontend suite: 5 files, 13 tests, all passed
- TypeScript: no errors (`npx tsc --noEmit`)
- Backend: pre-existing failure in test_learn_router (unconfirmed to this plan per STATE.md)

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check: PASSED

Files created/modified:
- FOUND: frontend/src/pages/creator/ModuleDetailPage.tsx
- FOUND: frontend/src/App.tsx (modified)
- FOUND: frontend/src/pages/creator/__tests__/ModuleDetailPage.test.tsx (modified)

Commits:
- 91a55f5: feat(13-04): implement ModuleDetailPage with form + AI streaming
- 551f1c0: feat(13-04): wire CourseBuilderPage and ModuleDetailPage routes in App.tsx
