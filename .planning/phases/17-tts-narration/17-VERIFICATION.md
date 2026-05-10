---
phase: 17-tts-narration
verified: 2026-05-10T22:30:00Z
status: passed
score: 10/10 must-haves verified
re_verification:
  previous_status: gaps_found
  previous_score: 9/10
  gaps_closed:
    - "All 7 backend TTS tests pass reliably in any execution order"
  gaps_remaining: []
  regressions: []
---

# Phase 17: TTS Narration Verification Report

**Phase Goal:** Creators can generate ElevenLabs narration audio for individual slides or in bulk for an entire video, with rate limiting preventing API storms and caching preventing redundant regeneration.
**Verified:** 2026-05-10T22:30:00Z
**Status:** passed
**Re-verification:** Yes — after gap closure (fixture ordering fragility resolved)

## Re-verification Summary

Previous gap: `test_generate_slide_audio`, `test_voice_id_passed_to_elevenlabs`, and `test_bulk_skips_cached_slides` produced ERROR on fixture setup when pytest randomised execution order.

Fix applied (commit `e292fba`): `setup_test_db` in `conftest.py` now calls `Base.metadata.drop_all(bind=test_engine)` before `create_all`, making each test's DB state idempotent regardless of order. `pytest-randomly==4.1.0` is installed in the venv (`backend/venv/lib/python3.14/site-packages`).

Verification run: tests executed under three distinct random seeds — 12345, 99999, and `last` — all returned **7 passed, 0 errors**.

No regressions introduced. Five pre-existing failures in `test_learn_router.py` (`'Course' object has no attribute 'content'`) were confirmed pre-existing via git log (last touched at `d8758aa`, before phase 17 began) and fail identically in isolation with `-p no:randomly`, independent of ordering.

## Goal Achievement

### Observable Truths

| #  | Truth | Status | Evidence |
|----|-------|--------|---------|
| 1  | POST /api/slides/{id}/tts/generate returns 200 with audio_url when script exists | VERIFIED | `tts.py` lines 59-92; endpoint validates api_key, narration_script, calls `tts_service.generate_for_slide()`, returns `{audio_url, slide_id}` |
| 2  | POST /api/slides/{id}/tts/generate returns 400 when slide has no narration_script | VERIFIED | `tts.py` lines 75-76; `test_generate_slide_audio_no_script` PASSED |
| 3  | POST /api/slides/{id}/tts/generate returns 503 when ELEVENLABS_API_KEY is empty | VERIFIED | `tts.py` lines 67-71; `test_generate_slide_audio_no_key` PASSED |
| 4  | Voice ID passed to ElevenLabs API matches request body voice_id | VERIFIED | `tts.py` lines 78-82; `test_voice_id_passed_to_elevenlabs` PASSED under all random seeds |
| 5  | Slide.narration_audio_url and Slide.narration_script_hash updated after generation | VERIFIED | `tts_service.py` lines 55-58; sha256 hash computed, both fields committed atomically |
| 6  | POST /api/videos/{id}/tts/bulk-generate returns generated/skipped/errors counts | VERIFIED | `tts.py` lines 95-137; `test_bulk_generate` PASSED |
| 7  | Slides with matching sha256 hash are skipped in bulk (cached) | VERIFIED | `tts.py` lines 124-127; `test_bulk_skips_cached_slides` PASSED under all random seeds |
| 8  | asyncio.Semaphore(3) at module level bounds ElevenLabs concurrency | VERIFIED | `tts_service.py` line 17; `_bulk_semaphore` imported into `tts.py` line 18; `test_semaphore_limits_concurrency` PASSED |
| 9  | NarrationTab renders generate-audio-btn + narration-audio-player + voice selector | VERIFIED | `NarrationTab.tsx` lines 8-11, 128-155; `data-testid="generate-audio-btn"`, `data-testid="narration-audio-player"`, `data-testid="voice-selector"` all present |
| 10 | All 7 backend TTS tests pass reliably in any execution order | VERIFIED | 7/7 PASSED under seeds 12345, 99999, and last. `setup_test_db` `drop_all` guard + `pytest-randomly==4.1.0` installed in venv. |

**Score:** 10/10 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `backend/services/tts_service.py` | TTSService with generate_for_slide(), _call_elevenlabs(), AVAILABLE_VOICES, _bulk_semaphore | VERIFIED | 81 lines; all required exports present; no stubs |
| `backend/routers/tts.py` | POST /slides/{id}/tts/generate + POST /videos/{id}/tts/bulk-generate, tts_service singleton | VERIFIED | 138 lines; both endpoints implemented; module-level tts_service singleton |
| `backend/main.py` | tts router registered via include_router | VERIFIED | Line 26: import as `tts_router_module`; line 213: `app.include_router(tts_router_module.router)` |
| `backend/tests/test_tts_phase17.py` | 7 tests covering TTS-01 through TTS-05 | VERIFIED | 318 lines; 7 tests substantive; 7/7 PASS under randomised ordering (3 seeds confirmed) |
| `backend/tests/conftest.py` | setup_test_db calls drop_all before create_all | VERIFIED | Lines 55-56: `Base.metadata.drop_all(bind=test_engine)` then `create_all`; docstring documents rationale |
| `frontend/src/components/slide/NarrationTab.tsx` | generate-audio-btn, narration-audio-player, voice selector | VERIFIED | 165 lines; all three testids present; handleGenerateAudio wired |
| `frontend/src/pages/creator/SlideBuilderPage.tsx` | Wired bulk-narration-btn + bulk-result-banner | VERIFIED | bulk-narration-btn calls handleBulkGenerate; bulk-result-banner renders after completion |
| `frontend/src/components/slide/__tests__/NarrationTab.test.tsx` | 5 tests: 3 original SLIDE-10/11 + 2 TTS-01 | VERIFIED | 53 lines; all 5 tests present with real assertions |
| `frontend/src/pages/creator/__tests__/SlideBuilderPage.test.tsx` | SLIDE-03 asserts button NOT disabled | VERIFIED | Line 63: `expect(btn).not.toBeDisabled()` — correctly updated from disabled assertion |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `backend/routers/tts.py` | `backend/services/tts_service.py` | `tts_service = TTSService()` module-level singleton | WIRED | Line 25: singleton declared; line 85: `tts_service.generate_for_slide()` called |
| `backend/routers/tts.py` | `tts_service._bulk_semaphore` | `async with _bulk_semaphore` inside `process_slide` coroutine | WIRED | Line 18: imported from tts_service; line 128: `async with _bulk_semaphore` inside process_slide |
| `backend/services/tts_service.py` | `uploads/audio/slide_{id}.mp3` | `Path(settings.UPLOAD_DIR) / 'audio'` | WIRED | Lines 47-49; dir created with `mkdir(parents=True, exist_ok=True)` |
| `NarrationTab.tsx generate-audio-btn` | `POST /api/slides/{id}/tts/generate` | `api.post` in `handleGenerateAudio` | WIRED | Line 61: `api.post('/slides/${slideId}/tts/generate', ...)` |
| `SlideBuilderPage.tsx bulk-narration-btn` | `POST /api/videos/{id}/tts/bulk-generate` | `api.post` in `handleBulkGenerate` | WIRED | Line 43: `api.post('/videos/${videoId}/tts/bulk-generate', ...)` |
| `NarrationTab audio player` | ElevenLabs MP3 file | `API_BASE + narration_audio_url` | WIRED | Line 2: `API_BASE` imported; line 152: `src={`${API_BASE}${audioUrl}`}` |

### Requirements Coverage

| Requirement | Source Plan(s) | Description | Status | Evidence |
|-------------|----------------|-------------|--------|---------|
| TTS-01 | 17-01, 17-02, 17-04 | Creator can generate narration audio for a slide from its narration script | SATISFIED | `POST /api/slides/{id}/tts/generate` endpoint; NarrationTab generate-audio-btn + audio player |
| TTS-02 | 17-03, 17-04 | Creator can bulk generate narration audio for all slides in a video | SATISFIED | `POST /api/videos/{id}/tts/bulk-generate` endpoint; SlideBuilderPage bulk-narration-btn wired |
| TTS-03 | 17-03 | TTS service uses a semaphore to rate-limit concurrent requests | SATISFIED | `_bulk_semaphore = asyncio.Semaphore(3)` in tts_service.py; `async with _bulk_semaphore` in process_slide |
| TTS-04 | 17-03 | Generated narration audio cached; bulk re-generate only reprocesses changed scripts | SATISFIED | sha256 hash comparison on lines 124-127 of tts.py; `narration_script_hash` column updated after generation |
| TTS-05 | 17-02, 17-04 | Creator can select from available ElevenLabs voice options | SATISFIED | AVAILABLE_VOICES list (Rachel, Josh) in tts_service.py; voice-selector in NarrationTab.tsx; voice_id passed through endpoint |
| SLIDE-03 | 17-04 | Creator can trigger bulk narration audio generation (deferred from Phase 14) | SATISFIED | bulk-narration-btn no longer disabled; wired to handleBulkGenerate; SLIDE-03 test updated |

All 5 TTS requirements and the deferred SLIDE-03 requirement are satisfied by implementation.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `NarrationTab.tsx` | 87, 122 | `placeholder=` on textarea/input | Info | Legitimate HTML placeholder attributes, not implementation stubs |
| `SlideBuilderPage.tsx` | 49 | `// Silent error` comment in catch block | Info | Intentional design decision per Plan 04; no crash but creator may see 0 generated count with no feedback |

No blocker or warning-level anti-patterns found.

### Pre-existing Failures (Not Phase 17)

5 tests in `test_learn_router.py` fail with `'Course' object has no attribute 'content'`. These are unrelated to phase 17: last modified at commit `d8758aa` (before phase 17); fail identically in isolation with `-p no:randomly`; caused by a schema mismatch in the learn router. These are not regressions.

### Human Verification Required

The live ElevenLabs API end-to-end test was conducted as part of Plan 05 on 2026-05-10. The creator confirmed all 5 browser checks passed (per 17-05-SUMMARY.md). No outstanding human verification items remain.

---

_Verified: 2026-05-10T22:30:00Z_
_Verifier: Claude (gsd-verifier)_
