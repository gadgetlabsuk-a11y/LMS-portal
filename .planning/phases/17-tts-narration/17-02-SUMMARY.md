---
phase: 17-tts-narration
plan: "02"
subsystem: backend-tts
tags: [tts, elevenlabs, per-slide, api, tests]
one_liner: "Per-slide ElevenLabs TTS endpoint with voice passthrough, 400/503 error handling, and green TTS-01/TTS-05 tests"

dependency_graph:
  requires: [17-01]
  provides: [backend/services/tts_service.py, backend/routers/tts.py]
  affects: [backend/main.py, backend/tests/test_tts_phase17.py]

tech_stack:
  added: [httpx async TTS call, asyncio.Semaphore(3) for bulk]
  patterns: [module-level singleton tts_service, lazy api_key check, patch("routers.tts.tts_service._call_elevenlabs")]

key_files:
  created:
    - backend/routers/tts.py
  modified:
    - backend/services/tts_service.py
    - backend/main.py
    - backend/tests/test_tts_phase17.py

decisions:
  - "TTSService.__init__ defers key check — no startup crash when ELEVENLABS_API_KEY unset (research pitfall #3)"
  - "tts_service = TTSService() module-level singleton in tts.py enables patch('routers.tts.tts_service._call_elevenlabs') in tests"
  - "creator_slide fixture uses HTTP 201 status codes (modules, videos, slides all return 201_CREATED)"
  - "Slide PUT returns 200 — checked with in (200, 201) for robustness"

metrics:
  duration: "~3 min"
  completed: "2026-05-10"
  tasks_completed: 2
  tasks_total: 2
  files_changed: 4
---

# Phase 17 Plan 02: TTSService Rewrite + Per-Slide Endpoint Summary

Per-slide ElevenLabs TTS endpoint with voice passthrough, 400/503 error handling, and green TTS-01/TTS-05 tests.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Rewrite TTSService and create tts.py router | ba69733 | tts_service.py, tts.py, main.py |
| 2 | Implement TTS-01 and TTS-05 tests | c110e44 | test_tts_phase17.py |

## What Was Built

**backend/services/tts_service.py** — Rewritten from scratch:
- `TTSService.__init__` sets `self.api_key` without raising (lazy check in `generate_for_slide`)
- `generate_for_slide(slide, voice_id, db)` — hashes script, writes MP3 to `uploads/audio/slide_{id}.mp3`, updates `narration_audio_url` and `narration_script_hash`, commits db
- `_call_elevenlabs(text, voice_id)` — async httpx POST with `xi-api-key` header, `eleven_flash_v2_5` model
- `AVAILABLE_VOICES` list with Rachel and Josh
- Module-level `_bulk_semaphore = asyncio.Semaphore(3)` for Plan 03 bulk endpoint

**backend/routers/tts.py** — New router:
- `POST /api/slides/{slide_id}/tts/generate` — validates api_key (503), narration_script (400), resolves voice_id, calls `tts_service.generate_for_slide()`
- Module-level `tts_service = TTSService()` singleton for test patching
- `_get_slide_or_404` and `_get_video_or_404` helpers (self-contained, no cross-router coupling)

**backend/main.py** — tts router registered after quizzes/uploads routers.

**backend/tests/test_tts_phase17.py** — 4 green tests:
- `test_generate_slide_audio` — 200, audio_url in response, .mp3 extension
- `test_voice_id_passed_to_elevenlabs` — Josh voice_id passed as second arg to `_call_elevenlabs`
- `test_generate_slide_audio_no_script` — 400 when slide has no narration_script
- `test_generate_slide_audio_no_key` — 503 when api_key is empty string

Bulk stubs (TTS-02/03/04) remain `pytest.fail()` — Plan 03 scope.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed HTTP 201 status code assertions in creator_slide fixture**
- **Found during:** Task 2
- **Issue:** Plan showed `assert mod_res.status_code == 200` but modules/videos/slides create endpoints all return HTTP 201 Created
- **Fix:** Updated assertions to use 201 for POST creates; used `in (200, 201)` for PUT which returns 200
- **Files modified:** backend/tests/test_tts_phase17.py

## Test Results

```
tests/test_tts_phase17.py::test_generate_slide_audio PASSED
tests/test_tts_phase17.py::test_voice_id_passed_to_elevenlabs PASSED
tests/test_tts_phase17.py::test_generate_slide_audio_no_script PASSED
tests/test_tts_phase17.py::test_generate_slide_audio_no_key PASSED
tests/test_tts_phase17.py::test_bulk_generate FAILED (TTS-02 not implemented)
tests/test_tts_phase17.py::test_semaphore_limits_concurrency FAILED (TTS-03 not implemented)
tests/test_tts_phase17.py::test_bulk_skips_cached_slides FAILED (TTS-04 not implemented)
4 passed, 3 failed (bulk stubs intentional — Plan 03 scope)
```

## Self-Check: PASSED

All key files exist. Both commits verified (ba69733, c110e44). 4 tests green, 3 bulk stubs red as expected.
