---
phase: 14-slide-builder-slide-editor
plan: "05"
subsystem: frontend
tags: [narration, slide-wizard, sse-streaming, zustand, app-routing]
dependency_graph:
  requires: [14-02, 14-04]
  provides: [NarrationTab, SlideOutlineWizard, App-slide-routes]
  affects: [frontend/src/components/slide, frontend/src/pages/creator/SlideEditorPage, frontend/src/App.tsx]
tech_stack:
  added: []
  patterns: [fetch + ReadableStream SSE (NOT EventSource), JSON accumulate-then-parse pattern, Zustand 5 narrationScript binding]
key_files:
  created:
    - frontend/src/components/slide/NarrationTab.tsx
    - frontend/src/components/slide/SlideOutlineWizard.tsx
    - frontend/src/components/slide/__tests__/NarrationTab.test.tsx
    - frontend/src/components/slide/__tests__/SlideOutlineWizard.test.tsx
  modified:
    - frontend/src/pages/creator/SlideEditorPage.tsx
    - frontend/src/App.tsx
decisions:
  - "@/contexts/AuthContext import path corrected to @/context/AuthContext — project uses singular 'context' directory (Rule 1 auto-fix)"
  - "SlideOutlineWizard accumulates all SSE tokens in buffer before JSON.parse — implements research pitfall #7 correctly"
  - "App.tsx routes are purely additive — no existing routes modified"
metrics:
  duration: "~8 minutes"
  completed: "2026-05-09"
  tasks: 2/2
  files: 6
---

# Phase 14 Plan 05: NarrationTab, SlideOutlineWizard, App Routes — Summary

**One-liner:** NarrationTab with Zustand-bound textarea + SSE fetch narration generation, 4-step SlideOutlineWizard with JSON-accumulate SSE pattern, and two new App.tsx creator routes for slide builder and editor.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | NarrationTab and SlideOutlineWizard components + SlideEditorPage update | 551386b | NarrationTab.tsx, SlideOutlineWizard.tsx, SlideEditorPage.tsx |
| 2 | NarrationTab + SlideOutlineWizard tests, App.tsx route wiring | b859a44 | NarrationTab.test.tsx, SlideOutlineWizard.test.tsx, App.tsx |

## What Was Built

**NarrationTab.tsx** — Right-panel narration tab for SlideEditorPage. Textarea bound to Zustand `narrationScript` (reads/writes via `useSlideEditorStore`). `onBlur` saves to `PUT /api/slides/{id}`. "Generate" button triggers `fetch + ReadableStream` POST to `/api/slides/{id}/ai/generate-narration`, streaming tokens into textarea in real time. Error state displayed inline.

**SlideOutlineWizard.tsx** — 4-step modal wizard (fixed inset overlay). Step 1: source prompt textarea (`data-testid="wizard-step-1"`, `wizard-source-prompt`). Step 2: slide count + tone preset config. Step 3: generate button triggers SSE fetch to `/api/slides/{anchorSlideId}/ai/generate-outline` — all tokens accumulated in `buffer` string, JSON.parse called only after stream complete (avoids partial-JSON parse error). Step 4: commit loop — POST each slide to `/videos/{videoId}/slides` then POST each block to `/slides/{id}/blocks`.

**SlideEditorPage.tsx** — Narration tab placeholder replaced with `<NarrationTab slideId={Number(slideId)} />`.

**App.tsx** — Two new creator routes added after the `moduleId` route:
- `/creator/courses/:id/videos/:videoId/slides` → SlideBuilderPage
- `/creator/courses/:id/videos/:videoId/slides/:slideId/editor` → SlideEditorPage

Both wrapped in `CreatorLayout` + `ProtectedRoute creatorRoute` consistent with all other creator routes.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] @/contexts/AuthContext import path incorrect**
- **Found during:** Task 1 — vitest failed to resolve import after component creation
- **Issue:** Plan specified `@/contexts/AuthContext` but project uses singular `@/context/AuthContext` (confirmed via `find`)
- **Fix:** Changed import in NarrationTab.tsx, SlideOutlineWizard.tsx, and test mocks to `@/context/AuthContext`
- **Files modified:** NarrationTab.tsx, SlideOutlineWizard.tsx, NarrationTab.test.tsx, SlideOutlineWizard.test.tsx
- **Commit:** 551386b (components), b859a44 (tests)

## Test Results

```
Test Files  10 passed (10)
     Tests  31 passed (31)
             3 × NarrationTab (SLIDE-10: textarea, state binding; SLIDE-11: generate btn)
             4 × SlideOutlineWizard (SLIDE-12: open/close, step 1 render, step navigation)
             24 × pre-existing tests (all green)
```

Backend: 90/95 pass. 5 pre-existing failures in test_learn_router.py — documented in STATE.md from Phase 12-02, unrelated to this plan.

## Success Criteria Check

- [x] NarrationTab.tsx renders textarea bound to Zustand narrationScript, generate button triggers SSE fetch (NOT EventSource)
- [x] SlideOutlineWizard.tsx has 4-step wizard; step 3 accumulates all SSE tokens then JSON.parse on completion; step 4 commits via POST loop
- [x] App.tsx has /creator/courses/:id/videos/:videoId/slides and .../slides/:slideId/editor routes
- [x] All 7 NarrationTab + SlideOutlineWizard tests pass (3 + 4)
- [x] Full frontend test suite green (31/31)

## Self-Check: PASSED

All key files exist and commits 551386b and b859a44 verified in git history.
