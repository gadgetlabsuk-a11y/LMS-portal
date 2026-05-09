---
phase: 12
slug: course-identity-structure
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-09
---

# Phase 12 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (backend) + vitest (frontend) |
| **Config file** | `backend/pytest.ini` (existing); `frontend/vitest.config.ts` (existing) |
| **Quick run command** | `cd backend && python -m pytest tests/ -x -q 2>&1 \| tail -10` |
| **Full suite command** | `cd backend && python -m pytest tests/ && cd ../frontend && npm run test:unit` |
| **Estimated runtime** | ~15 seconds (backend); ~30 seconds (full) |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && python -m pytest tests/ -x -q`
- **After every plan wave:** Run full suite (backend + frontend)
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 12-01-01 | 01 | 0 | COURSE-01–03, COURSE-05 | automated | `cd backend && python -m pytest tests/test_courses_phase12.py -x -q` | ❌ W0 | ⬜ pending |
| 12-01-02 | 01 | 0 | COURSE-04 | automated | `cd frontend && npm run test:unit -- --run SkeletonTreePreview` | ❌ W0 | ⬜ pending |
| 12-02-01 | 02 | 1 | COURSE-01 | automated | `cd backend && python -m pytest tests/test_courses_phase12.py::test_create_course_with_identity -x` | ❌ W0 | ⬜ pending |
| 12-02-02 | 02 | 1 | COURSE-02 | automated | `cd backend && python -m pytest tests/test_courses_phase12.py::test_generate_description_sse -x` | ❌ W0 | ⬜ pending |
| 12-02-03 | 02 | 1 | COURSE-03 | automated | `cd backend && python -m pytest tests/test_courses_phase12.py::test_generate_objectives_sse -x` | ❌ W0 | ⬜ pending |
| 12-03-01 | 03 | 2 | COURSE-04 | automated | `cd frontend && npm run test:unit -- --run SkeletonTreePreview` | ❌ W0 | ⬜ pending |
| 12-03-02 | 03 | 2 | COURSE-05 | automated | `cd backend && python -m pytest tests/test_courses_phase12.py::test_scaffold_structure -x` | ❌ W0 | ⬜ pending |
| 12-03-03 | 03 | 2 | COURSE-04, COURSE-05 | manual | Open Modal 1B in browser, set counts, confirm skeleton updates live | n/a | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/tests/test_courses_phase12.py` — stub tests for COURSE-01, COURSE-02, COURSE-03, COURSE-05 (fail before implementation)
- [ ] `frontend/src/components/course/__tests__/SkeletonTreePreview.test.tsx` — stub unit test for live skeleton preview (COURSE-04, fail before implementation)
- [ ] `sse-starlette` added to `backend/requirements.txt` — required before any SSE streaming test can run

*These must exist and stubs must fail before implementation begins.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| AI description streams into Textarea in real time | COURSE-02 | Requires browser + live backend + Claude API key | Open Modal 1A, click "Generate description", watch text stream into field character-by-character |
| AI objectives stream into list in real time | COURSE-03 | Requires browser + live backend + Claude API key | Open Modal 1A, click "Generate objectives", watch bullet points stream in |
| Modal 1B skeleton preview updates on input change | COURSE-04 | Requires browser | Open Modal 1B, change module count from 2→4, confirm skeleton tree adds 2 module rows instantly |
| Navigating to Course Builder after scaffold | COURSE-05 | Requires browser + Phase 13 route stub | Complete Modal 1B, confirm redirect to /creator/courses/:id/builder without 404 |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
