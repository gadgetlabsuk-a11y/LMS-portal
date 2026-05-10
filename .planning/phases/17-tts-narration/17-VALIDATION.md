---
phase: 17
slug: tts-narration
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-10
---

# Phase 17 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Vitest 2.1.8 (frontend) + pytest (backend) |
| **Config file** | `frontend/vitest.config.ts` (existing); `backend/pytest.ini` (existing) |
| **Quick run command** | `cd frontend && npm run test:unit` |
| **Full suite command** | `cd frontend && npm run test:unit && cd ../backend && python -m pytest tests/ -x -q` |
| **Estimated runtime** | ~10 seconds (frontend); ~30 seconds (full) |

---

## Sampling Rate

- **After every frontend task commit:** `cd frontend && npm run test:unit`
- **After every backend task commit:** `cd backend && python -m pytest tests/test_tts_phase17.py -x -q`
- **After every plan wave:** Run full suite (frontend + backend)
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 17-01-01 | 01 | 0 | TTS-01–05 | integration | `cd backend && python -m pytest tests/test_tts_phase17.py -x -q` | ❌ W0 | ⬜ pending |
| 17-01-02 | 01 | 0 | TTS-01 (FE) | unit | `cd frontend && npm run test:unit -- --run NarrationTab 2>&1 \| grep -E "FAIL\|Cannot find"` | ❌ W0 | ⬜ pending |
| 17-02-01 | 02 | 1 | TTS-01, TTS-05 | integration | `cd backend && python -m pytest tests/test_tts_phase17.py::test_generate_slide_audio tests/test_tts_phase17.py::test_voice_id_passed_to_elevenlabs -x -q` | ❌ W0 | ⬜ pending |
| 17-02-02 | 02 | 1 | TTS-01, TTS-05 | unit | `cd backend && python -m pytest tests/test_tts_phase17.py -x -q` | ❌ W0 | ⬜ pending |
| 17-03-01 | 03 | 2 | TTS-02, TTS-03, TTS-04 | integration | `cd backend && python -m pytest tests/test_tts_phase17.py -x -q` | ❌ W0 | ⬜ pending |
| 17-04-01 | 04 | 3 | TTS-01 (FE), TTS-02 (FE) | unit | `cd frontend && npm run test:unit -- --run NarrationTab` | ❌ W0 | ⬜ pending |
| 17-05-01 | 05 | 4 | TTS-01–05 | manual | Browser walkthrough: per-slide audio, bulk, cache, voice selection | n/a | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/tests/test_tts_phase17.py` — stubs for TTS-01 through TTS-05 (fail before implementation with `pytest.fail()`)
- [ ] `frontend/src/components/slide/__tests__/NarrationTab.test.tsx` — add stubs for audio player (TTS-01 FE) — file already exists, add new failing test stubs

*No new packages required — httpx and hashlib (stdlib) cover all ElevenLabs and hashing needs. No Alembic migration needed — `narration_audio_url`, `narration_script_hash`, and `narration_voice_id` columns already exist.*

*These must exist and stubs must fail before implementation begins.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Click "Generate audio" → audio plays in player | TTS-01 | Requires live ElevenLabs API key | Open Slide Editor, go to Narration tab, enter script text, click "Generate audio", confirm audio player appears and plays |
| Bulk generate all slides in a video | TTS-02 | Requires live backend + ElevenLabs | Open Slide Builder, click "Generate Narration" bulk button, set voice, confirm progress shown, all slides with scripts get audio URLs |
| Bulk skips slides with no script | TTS-02 | Requires browser inspection | Add a slide with no script, trigger bulk; confirm it is skipped in the result counts |
| Running bulk twice skips unchanged slides | TTS-04 | Requires live backend (hash comparison) | Run bulk → edit one slide script → run bulk again; confirm only the edited slide was re-generated |
| Voice selection affects generation | TTS-05 | Requires live ElevenLabs API | Select "Josh" voice before generating; confirm resulting audio sounds different from "Rachel" voice |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
