---
phase: 10-data-models
plan: "02"
subsystem: database
tags: [sqlalchemy, sqlite, postgresql, alembic, orm, models]

# Dependency graph
requires:
  - phase: 10-01
    provides: Alembic bootstrap, test stubs for DATA-01 through DATA-09

provides:
  - Module, Video, Slide, Block, Quiz, Question, Resource, AiPromptLog SQLAlchemy model classes
  - Updated Course model with 17 new columns, content column removed
  - Updated Enrollment model with course_version column
  - CourseStatus.HAS_UNPUBLISHED_CHANGES enum value
  - All new models exported from models/__init__.py
  - All 18 DATA model test stubs now pass GREEN

affects: [10-03, alembic-migrations, creator-api, learn-api]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "order_index + composite index pattern (idx_X_course_order) on all hierarchical tables"
    - "CASCADE delete on all child FK relationships (module -> video -> slide -> block chain)"
    - "video_type column name (not type) to avoid SQLAlchemy reserved word conflict"
    - "pass_rate + attempts_allowed naming (not pass_score/max_attempts) per spec research"
    - "Resource.module_id FK (not course_id) — resources belong to modules, not courses"

key-files:
  created: []
  modified:
    - backend/models/models.py
    - backend/models/__init__.py

key-decisions:
  - "Course.content column removed from model class — retired in Phase 10 per spec, no two-code-path handling"
  - "video_type used instead of type on Video model — avoids SQLAlchemy Python reserved word conflict"
  - "Quiz uses pass_rate and attempts_allowed naming per AI_COURSE_BUILDER_SPEC.md research (not pass_score/max_attempts)"
  - "Resource links to Module via module_id FK (not course_id) — spec confirmed resources belong to modules"
  - "test_creator_router.py and test_learn_router.py errors are pre-existing bcrypt/passlib Python 3.14 incompatibility — not introduced by this plan"

patterns-established:
  - "All hierarchical child tables use cascade='all, delete-orphan' and order_by on parent relationships"
  - "Composite indexes on (parent_id, order_index) for all ordered child tables"
  - "server_default used instead of default for DB-level defaults on nullable integer/string columns"

requirements-completed: [DATA-01, DATA-02, DATA-03, DATA-04, DATA-05, DATA-06, DATA-07, DATA-09]

# Metrics
duration: ~12min
completed: 2026-05-09
---

# Phase 10 Plan 02: Data Models Summary

**7 new SQLAlchemy ORM classes (Module, Video, Slide, Block, Quiz, Question, Resource, AiPromptLog) added to models.py with all spec-required columns, plus Course updated with 17 new columns and content column removed**

## Performance

- **Duration:** ~12 min
- **Started:** 2026-05-09T08:55:00Z
- **Completed:** 2026-05-09T09:07:00Z
- **Tasks:** 2/2
- **Files modified:** 2

## Accomplishments

- All 18 test stubs from Plan 01 now pass GREEN (was 18 failing RED)
- 7 new SQLAlchemy model classes with full column specs, relationships, and composite indexes
- Course model updated: content column removed, 17 new authoring columns added, modules relationship added
- Enrollment gains course_version to anchor progress snapshots to a specific published version
- CourseStatus enum extended with HAS_UNPUBLISHED_CHANGES for draft-after-publish state
- models/__init__.py updated so Base.metadata.create_all() picks up all new tables

## Task Commits

1. **Task 1: Add 7 new model classes and update Course/Enrollment** - `043580f` (feat)
2. **Task 2: Update models/__init__.py exports** - `96587c6` (feat)

## Files Created/Modified

- `backend/models/models.py` - CourseStatus extended, Course updated (content removed, 17 columns added, modules relationship), Enrollment.course_version added, 8 new model classes appended (Module, Video, Slide, Block, Quiz, Question, Resource, AiPromptLog)
- `backend/models/__init__.py` - All 8 new model classes added to imports and __all__

## Decisions Made

- **Course.content removed cleanly** — no backward-compat shim. Alembic migration (Plan 03) will handle the DB column drop.
- **video_type not type** on Video model — avoids collision with Python/SQLAlchemy `type` attribute.
- **pass_rate + attempts_allowed** naming confirmed from spec research (not pass_score/max_attempts).
- **Resource.module_id** FK (not course_id) — spec links resources to modules for granular access control.
- **Pre-existing test errors noted but not fixed** — test_creator_router.py and test_learn_router.py have bcrypt/passlib failures on Python 3.14 (confirmed pre-existing from Plan 01). Out of scope for this plan.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- **bcrypt/passlib Python 3.14 incompatibility** — test_creator_router and test_learn_router tests error on setup due to passlib's bcrypt backend not supporting Python 3.14. Confirmed pre-existing (same errors before any changes in this plan). Logged to deferred items; not introduced by this plan.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- All model classes in place — Alembic autogenerate (Plan 03) will detect all new tables and column changes
- `Base.metadata` is fully populated — create_all creates all 8 new tables correctly in test SQLite DB
- No blocking issues for Plan 03 (Alembic migration script generation)

---
*Phase: 10-data-models*
*Completed: 2026-05-09*
