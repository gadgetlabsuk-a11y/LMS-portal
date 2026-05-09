---
phase: 14
slug: slide-builder-slide-editor
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-09
---

# Phase 14 — Validation Strategy

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
- **After every backend task commit:** `cd backend && python -m pytest tests/test_slides_phase14.py -x -q`
- **After every plan wave:** Run full suite (frontend + backend)
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 14-01-01 | 01 | 0 | SLIDE-01–12 | unit | `cd frontend && npm run test:unit -- --run SlideBuilderPage` | ❌ W0 | ⬜ pending |
| 14-01-02 | 01 | 0 | SLIDE-04–08 | unit | `cd frontend && npm run test:unit -- --run SlideEditorPage` | ❌ W0 | ⬜ pending |
| 14-01-03 | 01 | 0 | SLIDE-11 | integration | `cd backend && python -m pytest tests/test_slides_phase14.py -x -q` | ❌ W0 | ⬜ pending |
| 14-02-01 | 02 | 1 | SLIDE-11, SLIDE-12 | integration | `cd backend && python -m pytest tests/test_slides_phase14.py -x -q` | ❌ W0 | ⬜ pending |
| 14-03-01 | 03 | 2 | SLIDE-01, SLIDE-02 | unit | `cd frontend && npm run test:unit -- --run SlideBuilderPage` | ❌ W0 | ⬜ pending |
| 14-04-01 | 04 | 3 | SLIDE-04–08 | unit | `cd frontend && npm run test:unit -- --run SlideEditorPage` | ❌ W0 | ⬜ pending |
| 14-05-01 | 05 | 4 | SLIDE-09–12 | unit | `cd frontend && npm run test:unit -- --run NarrationTab` | ❌ W0 | ⬜ pending |
| 14-06-01 | 06 | 5 | SLIDE-01–12 | manual | Browser walkthrough: strip, canvas, undo/redo, autosave, narration, wizard | n/a | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `frontend/src/pages/creator/__tests__/SlideBuilderPage.test.tsx` — stubs for SLIDE-01, SLIDE-02, SLIDE-03 (fail before implementation)
- [ ] `frontend/src/pages/creator/__tests__/SlideEditorPage.test.tsx` — stubs for SLIDE-04 through SLIDE-08 (fail before implementation)
- [ ] `frontend/src/components/slide/__tests__/NarrationTab.test.tsx` — stubs for SLIDE-10, SLIDE-11, SLIDE-12 (fail before implementation)
- [ ] `backend/tests/test_slides_phase14.py` — stub tests for SLIDE-11 SSE endpoint and SLIDE-12 outline endpoint (fail before implementation)
- [ ] `react-grid-layout`, `zustand`, `@tiptap/react`, `@tiptap/starter-kit`, `@types/react-grid-layout` installed in frontend/package.json

*These must exist and stubs must fail before implementation begins.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Drag block from palette onto canvas — snaps to 12-column grid | SLIDE-05 | Requires browser drag interaction | Open Slide Editor, drag a Text block from the palette, confirm it lands snapped to grid |
| Resize block on canvas — position persists after reload | SLIDE-06 | Requires browser drag + resize handles | Drag-resize a block, navigate away, return, confirm size unchanged |
| Undo/redo 20 steps — correct state restored | SLIDE-07 | Requires browser interaction | Add 5 blocks, undo 5 times to empty canvas, redo 5 times, confirm all 5 restored |
| Autosave indicator shows "Saved" after idle | SLIDE-08 | Requires browser + timing | Edit block content, wait 1s, confirm "Saved" badge appears |
| Navigation away flushes pending save | SLIDE-08 | Requires browser + route change | Edit block, immediately click Back, confirm no data loss on return |
| AI narration streams into textarea | SLIDE-11 | Requires live backend + Claude API key | Open Narration tab, click "Generate narration", confirm tokens stream in |
| 4-step slide outline wizard generates and commits slides | SLIDE-12 | Requires live backend + Claude API | Open wizard, enter prompt, complete 4 steps, confirm new slides appear in strip |
| Layout preset replaces canvas blocks | SLIDE-09 | Requires browser | Select a preset from picker, confirm canvas updates to match preset layout |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
