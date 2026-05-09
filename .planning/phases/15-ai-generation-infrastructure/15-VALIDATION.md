---
phase: 15
slug: ai-generation-infrastructure
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-09
---

# Phase 15 — Validation Strategy

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
- **After every backend task commit:** `cd backend && python -m pytest tests/test_ai_phase15.py -x -q`
- **After every plan wave:** Run full suite (frontend + backend)
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 15-01-01 | 01 | 0 | AI-01–07 | unit | `cd frontend && npm run test:unit -- --run useSSEStream 2>&1 \| grep -E "FAIL\|Cannot find"` | ❌ W0 | ⬜ pending |
| 15-01-02 | 01 | 0 | AI-01–07 | unit | `cd frontend && npm run test:unit -- --run SideDrawer 2>&1 \| grep -E "FAIL\|Cannot find"` | ❌ W0 | ⬜ pending |
| 15-01-03 | 01 | 0 | AI-03, AI-04 | integration | `cd backend && python -m pytest tests/test_ai_phase15.py -x -q` | ❌ W0 | ⬜ pending |
| 15-02-01 | 02 | 1 | AI-03, AI-04 | integration | `cd backend && python -m pytest tests/test_ai_phase15.py -x -q` | ❌ W0 | ⬜ pending |
| 15-03-01 | 03 | 2 | AI-01, AI-02 | unit | `cd frontend && npm run test:unit -- --run "useSSEStream\|SideDrawer\|StreamingTextOutput"` | ❌ W0 | ⬜ pending |
| 15-03-02 | 03 | 2 | AI-01, AI-02 | unit | `cd frontend && npm run test:unit -- --run "CourseIdentityModal\|ModuleDetailPage\|NarrationTab"` | ❌ W0 | ⬜ pending |
| 15-04-01 | 04 | 3 | AI-06, AI-07 | unit | `cd frontend && npm run test:unit -- --run AISuggestionsRail` | ❌ W0 | ⬜ pending |
| 15-05-01 | 05 | 4 | AI-01–07 | manual | Browser walkthrough: shared drawer on all surfaces, PDF upload, suggestions rail, tone, disconnect | n/a | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `frontend/src/hooks/__tests__/useSSEStream.test.ts` — stub for AI-01 (fail before implementation)
- [ ] `frontend/src/components/ai/__tests__/SideDrawer.test.tsx` — stub for AI-01, AI-02 (fail before implementation)
- [ ] `frontend/src/components/ai/__tests__/AISuggestionsRail.test.tsx` — stub for AI-06 (fail before implementation)
- [ ] `backend/tests/test_ai_phase15.py` — stubs for AI-03 (document ingestion) and AI-04 (PDF extraction via PyMuPDF, fail before implementation)
- [ ] `pymupdf==1.26.0` added to `backend/requirements.txt`

*These must exist and stubs must fail before implementation begins.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| All AI generation surfaces use shared SideDrawer | AI-01 | Requires visual inspection across all pages | Open each surface (Course Identity, Module Detail, Narration, Slide Outline), confirm consistent drawer UI with StreamingTextOutput |
| PDF upload → structured outline | AI-04 | Requires live backend + real PDF | In Slide Outline wizard, upload a PDF, confirm slide titles extracted from document content |
| DOCX upload → structured outline | AI-04 | Requires live backend + real DOCX | In Slide Outline wizard, upload a DOCX, confirm content parsed correctly |
| AI suggestions rail shows nudges | AI-06 | Requires browser + real course data | Open Course Builder for course with missing descriptions, confirm rail shows contextual suggestions |
| Tone preset affects generation phrasing | AI-07 | Requires live Claude API | Set tone to "formal" vs "casual" in Modal 1A, generate description, compare wording differs meaningfully |
| Disconnect stops server SSE generation | AI-05 | Requires browser devtools + live backend | Start generation, close browser tab mid-stream, confirm backend logs show disconnection detected and generator stopped |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
