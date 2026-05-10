---
phase: 17-tts-narration
plan: 06
subsystem: testing
tags: [pytest, sqlalchemy, sqlite, pytest-randomly, fixtures, conftest]

# Dependency graph
requires:
  - phase: 17-tts-narration
    provides: TTS backend and test suite for test_tts_phase17.py
provides:
  - Order-independent TTS test execution under pytest-randomly
  - conftest.py setup_test_db uses drop_all before create_all for idempotency
  - pytest-randomly 4.1.0 in requirements.txt

affects: [all future phases using conftest.py setup_test_db]

# Tech tracking
tech-stack:
  added: [pytest-randomly==4.1.0]
  patterns: [setup_test_db drops all tables before create_all to ensure idempotency across random test orderings]

key-files:
  created: []
  modified:
    - backend/tests/conftest.py
    - backend/requirements.txt

key-decisions:
  - "Root cause of random-order failures was setup_test_db calling create_all without first dropping tables — when db fixture used rollback (not drop_all), tables survived into the next test's setup, causing 'table already exists' OperationalError"
  - "Fix: add drop_all before create_all in setup_test_db — idempotent regardless of previous test state"
  - "db fixture connection+transaction+rollback+event.listens_for pattern was already correct and unchanged"
  - "pytest-randomly 4.1.0 installed (not 3.16.0 as plan specified — 4.1.0 is the current release, same API)"

patterns-established:
  - "setup_test_db: drop_all + create_all at setup (not just create_all) — prevents table-exists errors under any test ordering"

requirements-completed: [TTS-01, TTS-02, TTS-03, TTS-04, TTS-05]

# Metrics
duration: 15min
completed: 2026-05-10
---

# Phase 17 Plan 06: TTS Test Fixture Gap Closure Summary

**drop_all before create_all in setup_test_db makes all 7 TTS tests order-independent under pytest-randomly seeds 12345 and 99999**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-05-10T20:30:00Z
- **Completed:** 2026-05-10T20:45:00Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Diagnosed and fixed random-order test failure: `create_all` without `drop_all` first caused "table already exists" OperationalError under pytest-randomly
- All 7 TTS tests pass under `--randomly-seed=12345` and `--randomly-seed=99999`
- pytest-randomly 4.1.0 installed and added to requirements.txt

## Task Commits

1. **Task 1: Fix conftest.py setup_test_db with drop_all before create_all** - `e292fba` (fix)
2. **Task 2: Install pytest-randomly and add to requirements.txt** - `c3695c4` (chore)

## Files Created/Modified
- `backend/tests/conftest.py` - Added `Base.metadata.drop_all(bind=test_engine)` before `create_all` in `setup_test_db` autouse fixture
- `backend/requirements.txt` - Added `pytest-randomly==4.1.0` after pytest line

## Decisions Made
- Root cause was NOT in the `db` fixture itself (which already had the correct connection+SAVEPOINT+rollback pattern). The problem was `setup_test_db` calling `create_all` without first dropping tables. When a test using the `db` fixture ran, its `outer_tx.rollback()` left tables intact (since rollback doesn't drop DDL in SQLite). The next test's `setup_test_db` then called `create_all` and hit "table already exists".
- Fix: make `setup_test_db` idempotent by calling `drop_all` before `create_all`. This is safe because `drop_all` on a database with no tables is a no-op.
- pytest-randomly 4.1.0 was installed (current release) rather than 3.16.0 as plan specified. Same API, no functional difference.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Root cause was in setup_test_db, not just the db fixture**
- **Found during:** Task 1 (running tests with --randomly-seed=12345)
- **Issue:** Plan specified the fix was entirely in the `db` fixture pattern (already implemented). Actual failure was in `setup_test_db` calling `create_all` without prior `drop_all` — causing "table already exists" OperationalError under random ordering.
- **Fix:** Added `Base.metadata.drop_all(bind=test_engine)` before `create_all` in `setup_test_db`. The `db` fixture was already correct and unchanged.
- **Files modified:** backend/tests/conftest.py
- **Verification:** 7 passed under --randomly-seed=12345 and --randomly-seed=99999
- **Committed in:** e292fba (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - Bug)
**Impact on plan:** Fix was in the right file (conftest.py) as specified. The db fixture was already correct. Only the additional drop_all line was needed. No scope creep.

## Issues Encountered
- The `db` fixture with connection+SAVEPOINT+rollback pattern was already in place from a prior attempt. The missing piece was `drop_all` idempotency in `setup_test_db`.

## Next Phase Readiness
- All 7 TTS tests pass under randomised ordering. Requirements TTS-01 through TTS-05 fully verified.
- Phase 17 gap closure complete. No remaining blockers.

---
*Phase: 17-tts-narration*
*Completed: 2026-05-10*
