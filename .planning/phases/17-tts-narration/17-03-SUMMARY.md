---
phase: 17-tts-narration
plan: 03
subsystem: api
tags: [tts, elevenlabs, asyncio, semaphore, caching, bulk-generation, fastapi]

# Dependency graph
requires:
  - phase: 17-02
    provides: TTSService with generate_for_slide, _bulk_semaphore at module level in tts_service.py, tts.py router skeleton
provides:
  - POST /api/videos/{video_id}/tts/bulk-generate endpoint with semaphore-bounded concurrency and script-hash caching
  - All 5 TTS backend tests green (TTS-01 through TTS-05)
affects: [17-04, 17-05, frontend TTS integration]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "asyncio.gather + asyncio.Semaphore(3) for bounded concurrent API calls"
    - "sha256 script-hash caching to skip unchanged slides on bulk re-generation"
    - "Module-level semaphore imported from service layer into router (never re-created per request)"

key-files:
  created: []
  modified:
    - backend/routers/tts.py
    - backend/tests/test_tts_phase17.py

key-decisions:
  - "bulk_generate_audio uses asyncio.gather + process_slide coroutine — all slides dispatched concurrently, semaphore limits actual ElevenLabs calls to 3"
  - "Cache check: narration_script_hash == sha256(script) AND narration_audio_url set — both conditions required to skip"
  - "creator_video fixture is file-local in test_tts_phase17.py (consistent with creator_slide, creator_quiz pattern)"
  - "test_semaphore_limits_concurrency uses AST introspection to verify _bulk_semaphore is not re-created inside tts.py"

patterns-established:
  - "Bounded bulk generation: asyncio.gather(*coroutines) + async with semaphore inside coroutine body"
  - "Script-hash caching: sha256(script.encode()).hexdigest() stored in narration_script_hash column"

requirements-completed: [TTS-02, TTS-03, TTS-04]

# Metrics
duration: 2min
completed: 2026-05-10
---

# Phase 17 Plan 03: Bulk TTS Generation Summary

**Bulk narration endpoint with asyncio.Semaphore(3) rate-limiting and sha256 script-hash caching — all 5 TTS backend tests green**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-05-10T16:59:18Z
- **Completed:** 2026-05-10T17:00:45Z
- **Tasks:** 2/2
- **Files modified:** 2

## Accomplishments
- Added `bulk_generate_audio` endpoint to `tts.py` replacing the `# TODO` stub
- Bounded concurrent ElevenLabs calls to 3 via `_bulk_semaphore` (imported from `tts_service.py`, not re-created)
- Script-hash caching: slides whose `narration_script_hash` matches `sha256(script)` and have `narration_audio_url` set are skipped
- All 5 tests in `test_tts_phase17.py` now PASS (TTS-01 through TTS-05)

## Task Commits

1. **Task 1: Add bulk_generate_audio endpoint to tts.py** - `505e50a` (feat)
2. **Task 2: Implement TTS-02/03/04 backend tests** - `8af1e4f` (feat)

## Files Created/Modified
- `backend/routers/tts.py` - Added `bulk_generate_audio` endpoint, `asyncio`/`hashlib` imports
- `backend/tests/test_tts_phase17.py` - Replaced 3 `pytest.fail()` stubs with real tests, added `creator_video` fixture

## Decisions Made
- `bulk_generate_audio` uses `asyncio.gather` with a `process_slide` inner coroutine — all slides dispatched concurrently; the `async with _bulk_semaphore` inside `process_slide` bounds actual ElevenLabs concurrency to 3
- Cache check requires both `narration_script_hash == sha256(script)` AND `narration_audio_url` being set — one without the other forces regeneration
- `test_semaphore_limits_concurrency` uses Python `ast` module to verify `_bulk_semaphore` has no module-level assignment in `tts.py` — structural, not behavioural, verification
- `creator_video` fixture is file-local in `test_tts_phase17.py` (consistent with `creator_slide`/`creator_quiz` pattern established in earlier phases)

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None. Pre-existing failure `test_learn_router.py::test_returns_only_published_courses` confirmed in STATE.md (12-02 decision); not introduced by this plan.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- TTS backend is fully tested: per-slide (TTS-01, TTS-05) and bulk (TTS-02, TTS-03, TTS-04) all green
- Ready for Plan 17-04: frontend NarrationTab wiring and TTS-06/07 frontend tests

---
*Phase: 17-tts-narration*
*Completed: 2026-05-10*
