---
phase: 16
slug: quiz-builder
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-10
---

# Phase 16 — Validation Strategy

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
- **After every backend task commit:** `cd backend && python -m pytest tests/test_quiz_phase16.py -x -q`
- **After every plan wave:** Run full suite (frontend + backend)
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 16-01-01 | 01 | 0 | QUIZ-01–08 | unit | `cd frontend && npm run test:unit -- --run QuizBuilderPage 2>&1 \| grep -E "FAIL\|Cannot find"` | ❌ W0 | ⬜ pending |
| 16-01-02 | 01 | 0 | QUIZ-02–06 | unit | `cd frontend && npm run test:unit -- --run QuestionForm 2>&1 \| grep -E "FAIL\|Cannot find"` | ❌ W0 | ⬜ pending |
| 16-01-03 | 01 | 0 | QUIZ-01–08 | integration | `cd backend && python -m pytest tests/test_quiz_phase16.py -x -q` | ❌ W0 | ⬜ pending |
| 16-02-01 | 02 | 1 | QUIZ-08 | integration | `cd backend && python -m pytest tests/test_quiz_phase16.py -x -q` | ❌ W0 | ⬜ pending |
| 16-03-01 | 03 | 2 | QUIZ-01–06 | unit | `cd frontend && npm run test:unit -- --run "QuizBuilderPage\|QuestionForm"` | ❌ W0 | ⬜ pending |
| 16-04-01 | 04 | 3 | QUIZ-07, QUIZ-08 | unit | `cd frontend && npm run test:unit -- --run QuizBuilderPage` | ❌ W0 | ⬜ pending |
| 16-05-01 | 05 | 4 | QUIZ-01–08 | manual | Browser walkthrough: quiz create, all question types, reorder, AI generate | n/a | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `frontend/src/pages/creator/__tests__/QuizBuilderPage.test.tsx` — stubs for QUIZ-01, QUIZ-07, QUIZ-08 (fail before implementation)
- [ ] `frontend/src/components/quiz/__tests__/QuestionForm.test.tsx` — stubs for QUIZ-02 through QUIZ-06 (fail before implementation)
- [ ] `backend/tests/test_quiz_phase16.py` — stubs for QUIZ-01 through QUIZ-08 (fail before implementation)

*No new packages required — dnd-kit, useSSEStream, SideDrawer all installed from Phases 13–15.*

*These must exist and stubs must fail before implementation begins.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Create quiz → configure pass_rate, attempts_allowed, show_feedback | QUIZ-01 | Requires browser + live backend | Navigate to module detail, create quiz, set pass rate 70%, attempts 3, toggle feedback; save and reload; confirm persists |
| Add MCQ single, MCQ multi, true/false, short answer questions | QUIZ-02–05 | Requires browser + form interaction | Add one question of each type; fill correct answers; save; reload; confirm all 4 persist with correct types |
| Explanation text saved per question | QUIZ-06 | Requires browser + live backend | Add explanation to a question; save; reload; confirm explanation text persists |
| Drag questions to reorder — persists after reload | QUIZ-07 | Requires browser drag interaction | Add 3 questions; drag Q3 to top; reload; confirm Q3 still first |
| AI generation streams question batch; confirm button commits | QUIZ-08 | Requires live backend + Claude API | Click "Generate questions with AI" in SideDrawer; see questions stream in; click "Add questions"; confirm questions added to list |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
