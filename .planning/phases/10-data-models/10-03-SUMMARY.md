---
phase: 10-data-models
plan: 03
subsystem: database
tags: [alembic, sqlite, migrations, schema, data-migration]

# Dependency graph
requires:
  - phase: 10-01
    provides: Alembic env.py with render_as_batch=True configured for SQLite
  - phase: 10-02
    provides: SQLAlchemy model classes for Module, Video, Slide, Block, Quiz, Question, Resource, AIPromptLog

provides:
  - Four Alembic migration scripts (001-004) normalising the database schema
  - courses table extended with 17 new columns plus slug unique index
  - Eight new relational tables: modules, videos, slides, blocks, quizzes, questions, resources, ai_prompt_log
  - Existing Course.content JSON migrated to Module/Video rows (2 courses, 8 videos)
  - courses.content column dropped via batch mode (SQLite safe)

affects: [11-api-endpoints, 12-course-builder-ui, 13-ai-pipeline]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - SQLite-safe DROP COLUMN via op.batch_alter_table context manager
    - PostgreSQL enum extension via autocommit_block with dialect guard
    - Graceful data migration with per-row error handling (print + continue, no raise)
    - Migration chain: None -> 001 -> 002 -> 003 -> 004 (head)

key-files:
  created:
    - backend/alembic/versions/001_extend_courses_table.py
    - backend/alembic/versions/002_create_new_tables.py
    - backend/alembic/versions/003_data_migration_retire_content.py
    - backend/alembic/versions/004_drop_content_column.py
  modified: []

key-decisions:
  - "Migration 003 uses lessons key (not videos) when parsing existing Course.content JSON — actual data uses modules[].lessons[], handled via module_data.get('videos', module_data.get('lessons', []))"
  - "Data migration 003 downgrade is intentionally a no-op — content JSON blobs cannot be reconstructed; column is restored by 004 downgrade but data is permanently gone"
  - "Unique index on courses.slug created in 001 upgrade, dropped before batch column removal in 001 downgrade to avoid SQLite constraint conflicts"

patterns-established:
  - "SQLite DROP COLUMN pattern: always use op.batch_alter_table context manager, never bare op.drop_column"
  - "PostgreSQL-only enum extension: wrap in dialect guard + autocommit_block to avoid transaction error"
  - "Data migrations: fetchall() then per-row try/except with print warning — never raise, always continue"

requirements-completed: [DATA-08, DATA-09]

# Metrics
duration: 12min
completed: 2026-05-09
---

# Phase 10 Plan 03: Alembic Migration Scripts Summary

**Four Alembic migrations normalise the LMS schema: 17 new courses columns, 8 new relational tables, Course.content JSON migrated to Module/Video rows, and content column dropped via SQLite-safe batch mode**

## Performance

- **Duration:** ~12 min
- **Started:** 2026-05-09T09:20:00Z
- **Completed:** 2026-05-09T09:32:00Z
- **Tasks:** 2/2
- **Files modified:** 4

## Accomplishments

- Wrote migrations 001 and 002: extends courses with 17 new columns (slug, summary, thumbnail_url, audience_level, learning_objectives, category, tags, estimated_duration_minutes, ai_tone_preset, ai_custom_prompt, navigation_mode, default_pass_rate, default_quiz_attempts, default_quiz_time_limit_seconds, certificate_enabled, published_at, version) and creates 8 new tables
- Wrote migration 003: inspected actual lms.db data (2 courses using `lessons` key), migrated to 2 Module rows and 8 Video rows with graceful per-row error handling
- Wrote migration 004: drops courses.content using op.batch_alter_table (SQLite safe); downgrade restores empty column
- Verified full round-trip: `alembic upgrade head`, `alembic downgrade base`, `alembic upgrade head` — all clean; 18/18 DATA tests passing

## Task Commits

Each task was committed atomically:

1. **Task 1: Write migrations 001 (extend courses) and 002 (create new tables)** - `72967f7` (feat)
2. **Task 2: Write migrations 003 (data migration) and 004 (drop content column)** - `5c7d264` (feat)

**Plan metadata:** (docs commit follows)

## Files Created/Modified

- `backend/alembic/versions/001_extend_courses_table.py` - Adds 17 new columns to courses, course_version to enrollments, unique slug index; PostgreSQL enum extension with dialect guard
- `backend/alembic/versions/002_create_new_tables.py` - Creates modules, videos, slides, blocks, quizzes, questions, resources, ai_prompt_log with all columns and indexes
- `backend/alembic/versions/003_data_migration_retire_content.py` - Migrates Course.content JSON to Module/Video rows; nulls content column; per-row error handling
- `backend/alembic/versions/004_drop_content_column.py` - Drops courses.content via batch_alter_table; downgrade adds column back empty

## Decisions Made

- Migration 003 handles `lessons` key (actual data shape) via `module_data.get('videos', module_data.get('lessons', []))` — future-proofs for either key
- Downgrade of 003 is intentionally a no-op: JSON blobs cannot be reconstructed from relational rows; documented prominently in code comment
- Unique index on courses.slug dropped before batch column removal in 001 downgrade to prevent SQLite constraint error during batch rebuild

## Deviations from Plan

None - plan executed exactly as written. The pre-inspection of lms.db confirmed the `lessons` key shape, which the migration template already handled correctly.

## Issues Encountered

None - all four migrations ran cleanly on first attempt. The `alembic current` after 002 showing `002 (head)` was expected (003/004 not yet written); resolved immediately on Task 2.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- All 4 migration scripts exist; `alembic upgrade head` runs on fresh SQLite and existing lms.db
- courses.content column absent; Module/Video rows created for existing course data
- Phase 11 (API endpoints) can now build endpoints against Module, Video, Slide, Block, Quiz, Question, Resource models
- Pre-existing bcrypt/passlib Python 3.14 errors in test_creator_router.py and test_learn_router.py are unrelated to this plan (documented in 10-02 decisions)

---
*Phase: 10-data-models*
*Completed: 2026-05-09*
