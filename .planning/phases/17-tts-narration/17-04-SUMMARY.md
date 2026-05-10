---
phase: 17-tts-narration
plan: "04"
subsystem: frontend
tags: [tts, narration, audio-player, bulk-generate, voice-selector]
dependency_graph:
  requires: [17-02]
  provides: [TTS-01-frontend, TTS-02-frontend, TTS-05-frontend]
  affects: [NarrationTab, SlideBuilderPage]
tech_stack:
  added: []
  patterns: [api.post-json-pattern, API_BASE-audio-src, useState-for-async-ui]
key_files:
  created: []
  modified:
    - frontend/src/components/slide/NarrationTab.tsx
    - frontend/src/components/slide/__tests__/NarrationTab.test.tsx
    - frontend/src/pages/creator/SlideBuilderPage.tsx
    - frontend/src/pages/creator/__tests__/SlideBuilderPage.test.tsx
decisions:
  - narration_audio_url added as optional field (?) in SlideBuilderPage Slide interface — required field caused TypeScript incompatibility with setSlides dispatch passed as onSlidesChange to VideoSlideStrip (two Slide types with same name but different shapes)
  - VOICE_OPTIONS const defined outside NarrationTab component — stable reference, not recreated on each render
  - Audio player only renders after successful generate click (audioUrl state set) — not rendered on initial mount
  - handleBulkGenerate silently catches errors — prevents crash; creator sees 0 generated count in result banner
metrics:
  duration: ~7min
  completed_date: "2026-05-10"
  tasks_completed: 2
  tasks_total: 2
  files_modified: 4
---

# Phase 17 Plan 04: TTS Frontend — NarrationTab + Bulk Narration Summary

TTS frontend complete: NarrationTab gains voice selector (Rachel/Josh), generate-audio button, and audio player; SlideBuilderPage bulk-narration-btn wired to POST /api/videos/{id}/tts/bulk-generate with result summary banner.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Extend NarrationTab with audio player, generate-audio button, voice selector | f343f32 | NarrationTab.tsx, NarrationTab.test.tsx |
| 2 | Wire bulk narration button in SlideBuilderPage | 9b5f935 | SlideBuilderPage.tsx, SlideBuilderPage.test.tsx |

## Verification

- All 5 NarrationTab tests pass (3 original SLIDE-10/11 + 2 new TTS-01)
- Full frontend suite: 61/62 pass — 1 pre-existing failure (useSSEStream cancel() documented in STATE.md 15-04/16-04, out of scope)
- SLIDE-03 test updated: asserts button is NOT disabled
- TypeScript: no new errors introduced (pre-existing TS6133 unused imports and SlideCanvas/SlideEditorPage errors remain)

## Requirements Closed

- TTS-01 frontend: NarrationTab renders generate-audio-btn; narration-audio-player appears after clicking
- TTS-02 frontend: SlideBuilderPage bulk-narration-btn wired; result summary banner shows generated/skipped/cached counts
- TTS-05 frontend: Voice selector (Rachel / Josh) present in NarrationTab

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Made narration_audio_url optional in Slide interface**
- **Found during:** Task 2 TypeScript check
- **Issue:** Adding `narration_audio_url: string | null` (required) to SlideBuilderPage's Slide interface caused TS2322 — `setSlides` (Dispatch<SetStateAction<Slide[]>>) passed as `onSlidesChange` to VideoSlideStrip, which expects its own `Slide[]` type; the two Slide types became structurally incompatible due to the new required field
- **Fix:** Changed to `narration_audio_url?: string | null` (optional) — API responses without the field still satisfy the type; plan note says "for future use" so optional is semantically correct
- **Files modified:** frontend/src/pages/creator/SlideBuilderPage.tsx
- **Commit:** 9b5f935

## Self-Check: PASSED
