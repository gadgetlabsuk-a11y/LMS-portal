---
phase: 16-quiz-builder
plan: 04
subsystem: ui
tags: [react, dnd-kit, sse, quiz, drag-drop, ai-generation]

requires:
  - phase: 16-quiz-builder/16-02
    provides: SSE endpoint POST /api/quizzes/{quiz_id}/ai/generate-questions
  - phase: 16-quiz-builder/16-03
    provides: QuizBuilderPage base + QuestionForm component

provides:
  - SortableQuestionRow with dnd-kit useSortable and explicit drag handle
  - QuizBuilderPage: drag-to-reorder via DndContext + SortableContext + PointerSensor(distance:8)
  - QuizBuilderPage: AI SideDrawer with bufferRef accumulation, pendingQuestions preview, confirm-to-POST all
  - CourseTreeRail quiz items navigate to /creator/courses/:courseId/quizzes/:quizId
  - App.tsx route /creator/courses/:id/quizzes/:quizId registered in CreatorLayout + ProtectedRoute
  - QUIZ-07: test_reorder_questions GREEN

affects: [16-05, learner-quiz-player, phase-17]

tech-stack:
  added: []
  patterns:
    - "bufferRef accumulation: bufferRef.current += token in onToken, JSON.parse ONLY after startStream() resolves"
    - "PointerSensor activationConstraint distance:8 — prevents accidental drag when clicking form inputs"
    - "SortableQuestionRow separates drag handle from content area so button/input clicks don't initiate drag"

key-files:
  created:
    - frontend/src/components/quiz/SortableQuestionRow.tsx
  modified:
    - frontend/src/pages/creator/QuizBuilderPage.tsx
    - frontend/src/pages/creator/__tests__/QuizBuilderPage.test.tsx
    - frontend/src/components/builder/CourseTreeRail.tsx
    - frontend/src/App.tsx
    - backend/tests/test_quiz_phase16.py

key-decisions:
  - "vi.mock('@dnd-kit/core') + vi.mock('@dnd-kit/sortable') required in QuizBuilderPage tests — dnd-kit uses browser pointer events unavailable in jsdom"
  - "React import added to test file for JSX in mock implementations (SortableContext, DndContext passthrough mocks)"
  - "useSSEStream cancel() failure is pre-existing (STATE.md 15-04 decision) — out of scope, not introduced by this plan"

patterns-established:
  - "Pattern: dnd-kit mocks in vitest — mock both @dnd-kit/core and @dnd-kit/sortable with passthrough JSX wrappers"
  - "Pattern: bufferRef SSE accumulation — always pair bufferRef.current = '' reset before startStream(), += in onToken, JSON.parse after await resolves"

requirements-completed: [QUIZ-07, QUIZ-08]

duration: 2min
completed: 2026-05-10
---

# Phase 16 Plan 04: Quiz Builder Interactivity Summary

**dnd-kit drag-to-reorder with bufferRef AI question generation, CourseTreeRail quiz navigation, and App.tsx route wired into QuizBuilderPage**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-05-10T16:16:37Z
- **Completed:** 2026-05-10T16:18:47Z
- **Tasks:** 2/2
- **Files modified:** 6

## Accomplishments
- SortableQuestionRow with PointerSensor(distance:8) prevents accidental drag on form inputs
- AI SideDrawer with bufferRef accumulation pattern — JSON.parse only after stream completion, pending questions preview with Add All confirm
- QUIZ-07 backend test_reorder_questions GREEN (was pytest.fail stub); all 9 QUIZ tests pass
- CourseTreeRail quiz rows now navigate to quiz builder route on click
- App.tsx route registered; 4/4 QuizBuilderPage frontend tests GREEN

## Task Commits

1. **Task 1: SortableQuestionRow + dnd-kit reorder + QUIZ-07 GREEN** - `178e501` (feat)
2. **Task 2: AI SideDrawer + CourseTreeRail nav + App.tsx route** - `0a44d4e` (feat)

## Files Created/Modified
- `frontend/src/components/quiz/SortableQuestionRow.tsx` - dnd-kit useSortable wrapper with explicit drag handle button
- `frontend/src/pages/creator/QuizBuilderPage.tsx` - DndContext + SortableContext + AI SideDrawer + bufferRef generation flow
- `frontend/src/pages/creator/__tests__/QuizBuilderPage.test.tsx` - dnd-kit mocks + useSSEStream mock + SideDrawer open/close test
- `frontend/src/components/builder/CourseTreeRail.tsx` - quiz rows navigate to /creator/courses/:courseId/quizzes/:quizId
- `frontend/src/App.tsx` - route /creator/courses/:id/quizzes/:quizId
- `backend/tests/test_quiz_phase16.py` - QUIZ-07 stub replaced with real 3-question reorder integration test

## Decisions Made
- `vi.mock('@dnd-kit/core')` and `vi.mock('@dnd-kit/sortable')` required — dnd-kit uses PointerEvent browser APIs unavailable in jsdom; passthrough JSX wrappers keep component tree intact
- `React` import added to test file to support JSX in mock factory functions for SortableContext/DndContext passthroughs
- Pre-existing `useSSEStream cancel()` test failure confirmed out of scope per STATE.md 15-04 decision — not introduced by this plan

## Deviations from Plan

None — plan executed exactly as written. The dnd-kit mocking pattern was anticipated (constraint #9 in plan), and React import for JSX mocks is a standard vitest requirement.

## Issues Encountered
None — all tests passed on first run.

## Next Phase Readiness
- QuizBuilderPage feature set complete: settings, question CRUD (4 types), drag-to-reorder, AI generation
- QUIZ-01 through QUIZ-08 all GREEN (backend + frontend)
- Ready for 16-05 (phase wrap-up / verification pass)

---
*Phase: 16-quiz-builder*
*Completed: 2026-05-10*
