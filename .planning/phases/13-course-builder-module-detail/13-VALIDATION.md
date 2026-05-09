---
phase: 13
slug: course-builder-module-detail
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-09
---

# Phase 13 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Vitest 2.1.8 (frontend) + pytest (backend) |
| **Config file** | `frontend/vitest.config.ts` (existing); `backend/pytest.ini` (existing) |
| **Quick run command** | `cd frontend && npm run test:unit` |
| **Full suite command** | `cd frontend && npm run test:unit && cd ../backend && python -m pytest tests/ -x -q` |
| **Estimated runtime** | ~10 seconds (frontend); ~25 seconds (full) |

---

## Sampling Rate

- **After every frontend task commit:** `cd frontend && npm run test:unit`
- **After every backend task commit:** `cd backend && python -m pytest tests/test_modules_router.py tests/test_modules_phase13.py -x -q`
- **After every plan wave:** Run full suite (frontend + backend)
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 13-01-01 | 01 | 0 | BUILD-01–03 | unit | `cd frontend && npm run test:unit -- --run CourseBuilderPage` | ❌ W0 | ⬜ pending |
| 13-01-02 | 01 | 0 | BUILD-04, BUILD-05 | unit | `cd frontend && npm run test:unit -- --run ModuleDetailPage` | ❌ W0 | ⬜ pending |
| 13-01-03 | 01 | 0 | BUILD-05 | integration | `cd backend && python -m pytest tests/test_modules_phase13.py -x -q` | ❌ W0 | ⬜ pending |
| 13-02-01 | 02 | 1 | BUILD-05 | integration | `cd backend && python -m pytest tests/test_modules_phase13.py -x -q` | ❌ W0 | ⬜ pending |
| 13-03-01 | 03 | 2 | BUILD-01–03, BUILD-06 | unit | `cd frontend && npm run test:unit -- --run CourseBuilderPage` | ❌ W0 | ⬜ pending |
| 13-04-01 | 04 | 3 | BUILD-04, BUILD-05 | unit | `cd frontend && npm run test:unit -- --run ModuleDetailPage` | ❌ W0 | ⬜ pending |
| 13-05-01 | 05 | 4 | BUILD-01–06 | manual | Browser walkthrough: tree, navigation, edit, reorder, AI stream | n/a | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `frontend/src/pages/creator/__tests__/CourseBuilderPage.test.tsx` — stubs for BUILD-01, BUILD-02, BUILD-03 (fail before implementation)
- [ ] `frontend/src/pages/creator/__tests__/ModuleDetailPage.test.tsx` — stubs for BUILD-04, BUILD-05 (fail before implementation)
- [ ] `backend/tests/test_modules_phase13.py` — stub for BUILD-05 SSE endpoint (fail before implementation)
- [ ] `@dnd-kit/core @dnd-kit/sortable @dnd-kit/utilities` installed in frontend/package.json

*These must exist and stubs must fail before implementation begins.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Drag module to reorder — persists after reload | BUILD-06 | Requires browser drag interaction | Open Course Builder, drag Module 2 above Module 1, reload page, confirm order preserved |
| AI description streams into field | BUILD-05 | Requires live backend + Claude API key | Open Module Detail, click "Generate description", confirm tokens stream into textarea |
| Module Detail form saves — all fields persist | BUILD-04 | Requires DB + reload verification | Edit title + duration + unlock rule, save, hard reload, confirm values unchanged |
| Navigation from tree to detail and back | BUILD-02 | Requires React Router in browser | Click module in left rail → Module Detail opens; click back → Course Builder restored |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
