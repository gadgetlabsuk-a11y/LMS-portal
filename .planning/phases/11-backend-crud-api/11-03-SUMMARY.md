---
phase: 11-backend-crud-api
plan: 03
subsystem: api
tags: [fastapi, sqlalchemy, pydantic, pytest, blocks, quizzes, questions]

# Dependency graph
requires:
  - phase: 11-02
    provides: slides router and ownership traversal patterns

provides:
  - Block CRUD router (5 endpoints, deep ownership traversal block→slide→video→module→course)
  - Quiz CRUD router (5 endpoints, module→course ownership)
  - Question CRUD + reorder router (6 endpoints including atomic reorder)
  - 14 passing tests covering all endpoints and trainee 403 checks

affects: [14-slide-editor, 16-quiz-builder]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - deep ownership traversal via multi-table join (block→slide→video→module→course) + ORM relationship chain for ownership check
    - reorder endpoint uses single db.commit() after all order_index assignments (atomic, no drift)
    - file-local setup_hierarchy fixture builds full hierarchy chain via API calls for realistic integration coverage

key-files:
  created:
    - backend/routers/blocks.py
    - backend/routers/quizzes.py
    - backend/tests/test_blocks_quizzes_router.py
  modified:
    - backend/main.py

key-decisions:
  - "blocks.py _get_slide_or_404 joins 4 tables (Slide/Video/Module/Course) then uses ORM relationship chain (slide.video.module.course) for the ownership check — consistent with slides.py pattern"
  - "quizzes.py _get_quiz_or_404 joins Quiz→Module→Course (module_id always set when created via module endpoint); video-linked quizzes out of scope for this plan"
  - "Question reorder uses identical atomic single-transaction pattern from modules.py — single db.commit() after loop"
  - "pass_rate and attempts_allowed naming used throughout (not pass_score/max_attempts)"

patterns-established:
  - "4-table join for block ownership: Block.join(Slide).join(Video).join(Module).join(Course) then ORM chain for creator_id"
  - "setup_hierarchy pytest fixture builds full ancestor hierarchy via API calls so all router endpoints can be exercised realistically"

requirements-completed: [API-04, API-05, API-07]

# Metrics
duration: 2min
completed: 2026-05-09
---

# Phase 11 Plan 03: Block + Quiz/Question CRUD Routers Summary

**Block CRUD (5 endpoints) and Quiz+Question CRUD+reorder (11 endpoints) with deep ownership traversal and 14 GREEN tests**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-05-09T09:02:29Z
- **Completed:** 2026-05-09T09:04:40Z
- **Tasks:** 2/2
- **Files modified:** 4

## Accomplishments
- blocks.py: 5 endpoints with 4-table ownership traversal (block→slide→video→module→course), no reorder (order_index is grid z-order updated via PUT)
- quizzes.py: 5 quiz endpoints + 6 question endpoints including atomic question reorder identical to the modules.py pattern
- 14 tests covering all CRUD operations, trainee 403 blocks, cascade delete, and question reorder verification
- main.py updated to register both routers; all 51 tests across modules/videos/slides/blocks/quizzes/data_models pass GREEN

## Task Commits

Each task was committed atomically:

1. **Task 1: Block + Quiz/Question routers** - `10d56e1` (feat)
2. **Task 2: Block + Quiz tests + register in main.py** - `ad8d21b` (feat)

**Plan metadata:** (docs commit — see below)

## Files Created/Modified
- `backend/routers/blocks.py` - Block CRUD (create, list, get, update, delete) with deep ownership traversal
- `backend/routers/quizzes.py` - Quiz CRUD + Question CRUD + atomic question reorder
- `backend/tests/test_blocks_quizzes_router.py` - 14 tests: block CRUD, quiz CRUD, question CRUD+reorder, trainee 403
- `backend/main.py` - Added blocks and quizzes to import and include_router calls

## Decisions Made
- `_get_slide_or_404` joins 4 tables then uses ORM relationship chain for ownership check — consistent with the slides.py single-item lookup pattern
- `_get_quiz_or_404` joins Quiz→Module→Course only (Quiz.module_id always set when created via the module endpoint); video-linked quiz ownership traversal deferred to when that use case is needed
- Atomic question reorder uses identical `single db.commit()` pattern from modules.py to prevent order_index drift (Known Pitfall #3)
- `pass_rate` and `attempts_allowed` naming used consistently per spec (not `pass_score`/`max_attempts`)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Block and Quiz/Question API complete; Phase 14 (Slide Editor) and Phase 16 (Quiz Builder) can now wire up to these endpoints
- All 51 backend router tests GREEN with no regressions

---
*Phase: 11-backend-crud-api*
*Completed: 2026-05-09*
