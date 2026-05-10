---
phase: 18
slug: preview-publish
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-10
---

# Phase 18 — Validation Strategy

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
- **After every backend task commit:** `cd backend && python -m pytest tests/test_publish_phase18.py -x -q`
- **After every plan wave:** Run full suite (frontend + backend)
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 18-01-01 | 01 | 0 | PREVIEW-01–03, PUBLISH-01–08 | integration | `cd backend && python -m pytest tests/test_publish_phase18.py -x -q` | ❌ W0 | ⬜ pending |
| 18-01-02 | 01 | 0 | PREVIEW-01, PREVIEW-02 | unit | `cd frontend && npm run test:unit -- --run PreviewMode 2>&1 \| grep -E "FAIL\|Cannot find"` | ❌ W0 | ⬜ pending |
| 18-02-01 | 02 | 1 | PUBLISH-01–08 | integration | `cd backend && python -m pytest tests/test_publish_phase18.py -x -q` | ❌ W0 | ⬜ pending |
| 18-03-01 | 03 | 2 | PREVIEW-01, PREVIEW-02, PREVIEW-03 | unit | `cd frontend && npm run test:unit -- --run PreviewMode` | ❌ W0 | ⬜ pending |
| 18-04-01 | 04 | 2 | PUBLISH-01, PUBLISH-02, PUBLISH-03 | unit | `cd frontend && npm run test:unit -- --run "PublishFlow\|PreflightChecklist"` | ❌ W0 | ⬜ pending |
| 18-05-01 | 05 | 3 | PREVIEW-01–03, PUBLISH-01–08 | manual | Browser walkthrough: preview, preflight, publish, version, archive | n/a | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/tests/test_publish_phase18.py` — stubs for PREVIEW-01–03 and PUBLISH-01–08 (fail before implementation with `pytest.fail()`)
- [ ] `frontend/src/pages/creator/__tests__/PreviewMode.test.tsx` — stubs for PREVIEW-01 (preview entry/exit) and PREVIEW-02 (draft watermark)

*No new packages required — all dependencies installed from prior phases.*
*One Alembic migration needed: `005_course_versions.py` creating `course_versions` table.*

*These must exist and stubs must fail before implementation begins.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Preview renders all block types correctly | PREVIEW-01 | Requires visual inspection of rendered content | Open Course Builder, click Preview, navigate through all modules/slides/quizzes; confirm all content renders |
| Quizzes are answerable in preview | PREVIEW-03 | Requires browser interaction | In preview mode, navigate to a quiz, answer questions, confirm quiz UI is interactive |
| Exit preview lands back exactly | PREVIEW-02 | Requires browser navigation state | Enter preview from Course Builder, exit, confirm URL and scroll position match original |
| Pre-flight deep-links work | PUBLISH-02 | Requires browser click-through | Fail a pre-flight check (e.g. no modules), click the deep-link in the checklist, confirm it navigates to the right screen |
| Published course visible to learners | PUBLISH-03 | Requires live backend + two roles | Publish a course as creator, log in as learner, confirm course appears in catalogue |
| Version pinning: enrolled learner keeps old version | PUBLISH-05 | Requires enrolment + update flow | Enrol learner on v1, update + republish as v2, confirm learner still sees v1 content |
| Archive removes from catalogue | PUBLISH-07 | Requires learner view | Archive a published course, confirm it no longer appears in learner catalogue |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
