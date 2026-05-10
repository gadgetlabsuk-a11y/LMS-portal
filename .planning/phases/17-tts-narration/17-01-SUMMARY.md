---
phase: 17-tts-narration
plan: 01
subsystem: testing
tags: [tts, elevenlabs, pytest, vitest, tdd, wave-0]

# Dependency graph
requires:
  - phase: 16-quiz-builder
    provides: creator fixture chain pattern (creator_quiz), reset_sse_state, Phase 16 COMPLETE
provides:
  - Wave 0 RED baseline for TTS: 5 pytest.fail() stubs covering TTS-01 through TTS-05
  - 2 failing vitest stubs for audio player + generate-audio-btn in NarrationTab
  - commented-out creator_slide fixture chain skeleton for Plan 02
  - api.post mock wired into NarrationTab test vi.mock block
affects: [17-02, 17-03, 17-04, 17-05]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Wave 0 TDD RED: pytest.fail() stubs with no implementation imports — clean FAILED not ERROR"
    - "Wave 0 TDD RED: vitest stubs reference non-existent testids (getByTestId) — fails at execution not collection"
    - "Commented-out fixture skeleton for fixture chain ready for Plan 02 without refactoring"

key-files:
  created:
    - backend/tests/test_tts_phase17.py
  modified:
    - frontend/src/components/slide/__tests__/NarrationTab.test.tsx

key-decisions:
  - "No import from routers.tts in test_tts_phase17.py — that file does not exist yet; import would cause ERROR not FAILED"
  - "creator_slide fixture chain left as commented-out skeleton — only needed once Plan 02 test bodies are written"
  - "api.post mock added to vi.mock('@/services/api') now so Plan 04 can use it without touching the mock block"
  - "2 new vitest stubs use getByTestId for non-existent elements — fails at execution giving clean FAILED state"

patterns-established:
  - "Phase 17 Wave 0 pattern matches Phase 14-16: pytest.fail() for backend, getByTestId for missing elements on frontend"

requirements-completed: [TTS-01, TTS-02, TTS-03, TTS-04, TTS-05]

# Metrics
duration: 5min
completed: 2026-05-10
---

# Phase 17 Plan 01: TTS Narration Wave 0 Summary

**pytest.fail() RED baseline for TTS-01 through TTS-05 plus 2 failing NarrationTab vitest stubs for audio player and generate-audio-btn**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-05-10T16:52:12Z
- **Completed:** 2026-05-10T16:54:00Z
- **Tasks:** 2/2
- **Files modified:** 2

## Accomplishments
- Created `backend/tests/test_tts_phase17.py` with 5 pytest.fail() stubs (TTS-01 through TTS-05); all 5 report FAILED, 0 ERROR
- Extended `NarrationTab.test.tsx` with 2 new failing TTS-01 stubs; 3 existing SLIDE-10/11 tests remain passing
- Added `api.post` mock to vi.mock block in NarrationTab tests for Plan 04 readiness
- Included commented-out creator_slide fixture chain skeleton in test file for Plan 02 without refactoring

## Task Commits

Each task was committed atomically:

1. **Task 1: Backend pytest.fail() stubs for TTS-01 through TTS-05** - `bd0f162` (test)
2. **Task 2: Frontend 2 failing audio player stubs in NarrationTab.test.tsx** - `4f66ef3` (test)

**Plan metadata:** (docs commit follows)

## Files Created/Modified
- `backend/tests/test_tts_phase17.py` - 5 pytest.fail() TTS stubs + commented creator_slide fixture skeleton
- `frontend/src/components/slide/__tests__/NarrationTab.test.tsx` - api.post mock + 2 new TTS-01 failing stubs

## Decisions Made
- No import from `routers.tts` in backend stubs — that file does not exist yet; any import would cause ERROR not FAILED (consistent with Phase 12-16 Wave 0 pattern)
- `creator_slide` fixture chain left as a commented-out block — the fixture is only needed once Plan 02 fills in test bodies; leaving it uncommented now would cause a collection error since the route imports don't exist yet
- `api.post` mock added now to the existing `vi.mock('@/services/api')` block so Plan 04 doesn't need to touch the mock section
- Frontend stubs use `getByTestId('generate-audio-btn')` and `getByTestId('narration-audio-player')` — neither testid exists in NarrationTab.tsx yet, giving a clean FAILED (not ERROR) state at execution time

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Wave 0 RED baseline established: 5 backend + 2 frontend failing stubs ready as green targets for Plans 02-04
- Plan 02: Rewrite TTSService for per-slide generation + new tts.py router + fill in test bodies
- Plan 03: Extend NarrationTab with audio player + generate-audio-btn (makes frontend stubs go GREEN)
- Plan 04: Wire bulk narration button in SlideBuilderPage + voice selector

---
*Phase: 17-tts-narration*
*Completed: 2026-05-10*
