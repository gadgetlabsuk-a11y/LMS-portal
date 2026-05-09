---
phase: 10-data-models
plan: 04
subsystem: deployment
tags: [alembic, coolify, migrations, production, deployment]

# Dependency graph
requires:
  - phase: 10-01
    provides: Alembic infrastructure with render_as_batch=True
  - phase: 10-02
    provides: SQLAlchemy model classes for all new tables
  - phase: 10-03
    provides: Four Alembic migration scripts (001–004)

provides:
  - start.sh updated with alembic upgrade head before uvicorn (local dev parity)
  - Coolify start command runs alembic upgrade head on every deploy
  - Production database schema at 004 (head) — all 8 new tables present, courses.content column dropped

affects: [11-api-endpoints]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Coolify start command pattern: cd backend && alembic upgrade head && uvicorn main:app --host 0.0.0.0 --port 8000
    - start.sh uses python3 -m alembic (not bare alembic) for venv path safety

key-files:
  modified:
    - start.sh

key-decisions:
  - "Coolify start command is configured in the Coolify dashboard (not a committed file) — human action required for each new environment"
  - "start.sh uses python3 -m alembic upgrade head with exit-on-failure guard to match production behaviour in local dev"

patterns-established:
  - "Every deploy runs alembic upgrade head before uvicorn — no manual migration steps needed"
  - "Migration chain is idempotent — running alembic upgrade head on an already-migrated DB is a no-op"

requirements-completed: [DATA-08]

# Metrics
duration: ~5min (checkpoint)
completed: 2026-05-09
---

# Phase 10 Plan 04: Coolify Start Command + Production Migration Summary

**Coolify wired to run `alembic upgrade head` before uvicorn on every deploy. Production database confirmed at `004 (head)` with all 8 new tables present.**

## Performance

- **Duration:** ~5 min (human checkpoint)
- **Completed:** 2026-05-09
- **Tasks:** 2/2
- **Files modified:** 1 (start.sh — already done in prior commit e70248e)

## Accomplishments

- start.sh already contained `python3 -m alembic upgrade head` with exit-on-failure guard (committed e70248e)
- Coolify start command updated to: `cd backend && alembic upgrade head && uvicorn main:app --host 0.0.0.0 --port 8000`
- Redeploy triggered; build logs confirmed migration ran successfully before uvicorn started
- `alembic current` on production shows `004 (head)` — all 8 new tables present, courses.content dropped
- App accessible at buildbench.uk/lms with no regression

## Task Commits

- **Task 1 (start.sh):** Already committed — `e70248e` chore(10-04): add alembic upgrade head to start.sh before uvicorn

## Files Created/Modified

- `start.sh` — prepends `python3 -m alembic upgrade head` with exit-on-failure guard before uvicorn launch

## Decisions Made

- Coolify dashboard start command is the authoritative production entrypoint — `start.sh` is local dev only
- No `alembic stamp head` needed: Alembic runs before `init_db()` (which calls `create_all()` as a no-op on an already-migrated DB)

## Deviations from Plan

None.

## Issues Encountered

None — migration ran cleanly on first deploy attempt.

## Next Phase Readiness

Phase 10 is fully complete:
- All 9 DATA requirements satisfied (DATA-01 through DATA-09)
- Production DB has Module, Video, Slide, Block, Quiz, Question, Resource, AiPromptLog tables
- courses.content column retired; existing data migrated
- Every future Coolify deploy auto-migrates
- Phase 11 (Backend CRUD API) can now build endpoints against the new schema

---
*Phase: 10-data-models*
*Completed: 2026-05-09*
