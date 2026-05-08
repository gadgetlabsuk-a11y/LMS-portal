---
phase: 10
slug: data-models
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-08
---

# Phase 10 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (backend) |
| **Config file** | `backend/pytest.ini` or `backend/pyproject.toml` — existing |
| **Quick run command** | `cd backend && python -m pytest tests/ -x -q 2>&1 \| tail -10` |
| **Full suite command** | `cd backend && python -m pytest tests/ -v 2>&1 \| tail -20` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && python -m pytest tests/ -x -q`
- **After every plan wave:** Run full suite + `alembic upgrade head && alembic downgrade -1 && alembic upgrade head`
- **Before `/gsd:verify-work`:** Full suite must be green + all new tables confirmed via `alembic current`
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 10-01-01 | 01 | 0 | DATA-08 | automated | `cd backend && alembic --version` | ❌ W0 | ⬜ pending |
| 10-01-02 | 01 | 1 | DATA-08 | automated | `cd backend && alembic current` | ❌ W0 | ⬜ pending |
| 10-02-01 | 02 | 1 | DATA-01–07 | automated | `cd backend && python -m pytest tests/test_models.py -v` | ❌ W0 | ⬜ pending |
| 10-02-02 | 02 | 1 | DATA-08 | automated | `cd backend && alembic upgrade head && alembic current` | ❌ W0 | ⬜ pending |
| 10-03-01 | 03 | 2 | DATA-09 | automated | `cd backend && python -m pytest tests/test_migration.py -v` | ❌ W0 | ⬜ pending |
| 10-03-02 | 03 | 2 | DATA-09 | manual | Inspect DB: `Course.content` column gone, data in new tables | n/a | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/alembic.ini` — Alembic config pointing at DB_URL
- [ ] `backend/alembic/env.py` — configured to import SQLAlchemy Base + settings
- [ ] `backend/alembic/versions/` — empty directory ready for migration scripts
- [ ] `backend/tests/test_models.py` — stub tests for new table existence (fail before migration)
- [ ] `backend/tests/test_migration.py` — stub tests for Course.content migration (fail before data migration)

*These must exist and stubs must fail before implementation begins.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Course.content column gone from production DB | DATA-09 | Requires live DB inspection in Coolify | SSH into Coolify container or use Coolify DB shell: `SELECT column_name FROM information_schema.columns WHERE table_name='courses';` — confirm no `content` column |
| Existing courses still accessible by learners | DATA-09 | Requires end-to-end smoke test | Log in as trainee, visit /learn, open a course — confirm it loads |
| alembic upgrade head runs on Coolify deploy | DATA-08 | Requires Coolify start command update | Trigger a redeploy, check Coolify build logs for `alembic upgrade head` success |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
