# Phase 10: Data Models - Research

**Researched:** 2026-05-08
**Domain:** SQLAlchemy ORM schema migration, Alembic setup, data migration from JSON blob to relational tables
**Confidence:** HIGH — based on direct codebase inspection

---

## Summary

Phase 10 takes the existing three-table SQLite schema (User, Course, Enrollment) and migrates it to the full relational schema required by the AI Course Builder spec. The primary challenge is threefold: (1) Alembic does not exist in this project at all — it must be bootstrapped from scratch; (2) the existing `Course.content` JSON column stores the old course structure and must be retired cleanly in a single migration with no dual-path fallback; (3) the Coolify deploy pipeline currently starts with `uvicorn main:app ...` directly, and must be changed to run `alembic upgrade head` first on every deploy.

The models package is already split into `backend/models/models.py` with a `Base` declared there. `database.py` uses `init_db()` which calls `Base.metadata.create_all(bind=engine)` — this must be replaced by Alembic control after migration. The DB URL is `sqlite:///./lms.db` in dev (config.py hardcoded default) and should be PostgreSQL in production via env var.

**Primary recommendation:** Implement Alembic with two migration scripts (extend courses table, create new tables), a one-time data migration script for existing `Course.content` JSON, then wire `alembic upgrade head` into the Coolify start command.

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| DATA-01 | Module table exists with `order_index`, `unlock_rule`, `status`, `description`, linked to Course | Full column spec confirmed in spec section 2 + ARCHITECTURE.md |
| DATA-02 | Video table exists with `type` (upload/embed/slides), `description`, `order_index`, linked to Module | Full column spec confirmed in spec section 2 + ARCHITECTURE.md |
| DATA-03 | Slide table exists with `order_index`, `status`, `layout`, `narration_script`, linked to Video | Full column spec confirmed in spec section 2 + ARCHITECTURE.md |
| DATA-04 | Block table exists with `type`, `content` (JSON), `position` (row/col/width/height), linked to Slide | Full column spec confirmed in spec section 2; `grid_position` is JSON with x,y,width,height |
| DATA-05 | Quiz table exists with `pass_score`, `max_attempts`, `show_feedback` settings, linked to Module | Full column spec confirmed; note column is `pass_rate` not `pass_score`; `attempts_allowed` not `max_attempts` |
| DATA-06 | Question table exists with `type`, `prompt`, `options` (JSON), `correct_answer`, `explanation`, linked to Quiz | Full column spec confirmed; `options` is JSON array; `correct_answer` is JSON (varies by type) |
| DATA-07 | Resource table exists for uploaded files (URL, mime type, size), linked to Course | Spec section 2 links Resource to Module (not Course); clarification: `module_id` FK |
| DATA-08 | Alembic migrations set up; all new tables created via migration (not bare `create_all`) | Confirmed: Alembic NOT installed; requires fresh setup |
| DATA-09 | `Course.content` JSON column retired; existing course data migrated to new relational structure | `content = Column(JSON, nullable=True)` confirmed in models.py; nullable so migration is safe |
</phase_requirements>

---

## What Exists Today (Confirmed by Codebase Inspection)

### Existing Models (backend/models/models.py)

| Model | Table | Key Columns | Notes |
|-------|-------|-------------|-------|
| User | users | id, username, email, hashed_password, role (Enum), is_active, mfa_* | Stable, no changes needed |
| Session | sessions | id, user_id (FK), token, ip_address, expires_at, is_active | Stable, no changes needed |
| Course | courses | id, title, description, **content (JSON)**, creator_id (FK), status (Enum: draft/published/archived), created_at | content column is the one to retire; status enum needs extending |
| Enrollment | enrollments | id, user_id (FK), course_id (FK), progress (Float), completed (Bool), enrolled_at, completed_at | Needs `course_version` anchor to prevent learner progress drift (see Pitfall 10) |
| AuditLog, ErrorLog, ApiUsage, FeatureFlag, WhiteLabelConfig, LoginAttempt, IpAllowlist | Various | Stable, no changes needed |

### Existing Infrastructure

| Component | State | Impact on Phase 10 |
|-----------|-------|-------------------|
| `database.py` `init_db()` | Calls `Base.metadata.create_all()` | Must keep for dev convenience BUT Alembic takes precedence on prod — do NOT remove `init_db()` yet; it is safe to coexist as long as Alembic migrations run first |
| `requirements.txt` | Does NOT include alembic | Must add `alembic` and `psycopg2-binary` (for prod PostgreSQL support) |
| `start.sh` | Runs `uvicorn main:app` directly — no migration step | Not the Coolify start command; see deploy note below |
| Coolify start command | Unknown from files — likely configured in Coolify dashboard, not a committed file | Must update to `alembic upgrade head && uvicorn main:app ...` |
| `models/__init__.py` | Exports `Base` from `models.models` | Alembic `env.py` must import `Base` from `models` (the package) — `from models import Base` works |
| DB URL | `sqlite:///./lms.db` hardcoded in config.py as default | Alembic `alembic.ini` must read from `settings.DB_URL` at runtime, not hardcode SQLite |
| No existing test for schema | `tests/conftest.py` uses `Base.metadata.create_all()` on test DB | After Alembic: conftest should still use `create_all` for tests (Alembic is for prod migrations, not test setup — this is standard) |

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| alembic | 1.13.x (latest stable) | Migration management, `upgrade head`, `downgrade` | The only serious migration tool for SQLAlchemy; spec and architecture docs mandate it |
| SQLAlchemy | 2.0.23 (already installed) | ORM, column definitions | Already in requirements.txt |
| psycopg2-binary | 2.9.x | PostgreSQL driver for prod | Required when DB_URL is postgresql://; binary wheel avoids libpq compile dependency |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest | 8.1.1 (already installed) | Test suite for schema smoke tests | Existing test infrastructure — extend, don't replace |

**Installation:**
```bash
# In backend/
pip install alembic psycopg2-binary
# Then add to requirements.txt:
# alembic==1.13.x
# psycopg2-binary==2.9.x
```

---

## Architecture Patterns

### Alembic Directory Structure
```
backend/
├── alembic.ini              # Alembic config — script_location, sqlalchemy.url placeholder
├── alembic/
│   ├── env.py               # Loads settings.DB_URL, imports Base, configures target_metadata
│   ├── script.py.mako       # Template for new migration scripts
│   └── versions/
│       ├── 001_extend_courses_table.py   # Migration 1: add new columns to courses
│       └── 002_create_new_tables.py      # Migration 2: all 8 new tables
├── models/
│   ├── __init__.py          # Exports Base and all models
│   └── models.py            # All SQLAlchemy model classes
├── database.py
└── config.py
```

### Pattern 1: Alembic env.py with Dynamic DB URL

The DB URL must come from `settings.DB_URL` at runtime (not hardcoded in alembic.ini) so that the same migration works in dev (SQLite) and prod (PostgreSQL).

```python
# alembic/env.py — key section
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from config import settings
from models import Base

config.set_main_option("sqlalchemy.url", settings.DB_URL)
target_metadata = Base.metadata
```

The `alembic.ini` sqlalchemy.url should be set to a placeholder:
```ini
sqlalchemy.url = sqlite:///./lms.db
```
But `env.py` overrides it at runtime via `config.set_main_option(...)` — the ini value is never used.

### Pattern 2: Two-Migration Strategy

**Migration 1 — extend courses table (nullable columns only, zero data risk):**
All new columns on `courses` are nullable or have defaults. This is a pure `ALTER TABLE ADD COLUMN` operation. Zero data migration risk. Safe to run on existing `lms.db` with live data.

**Migration 2 — create all new tables:**
Creates 8 new tables. Pure `CREATE TABLE` — no risk to existing data. No FK to new tables yet (courses still has `content` column).

**Data migration (inline in Migration 2 or separate Migration 3):**
Parse existing `Course.content` JSON and insert rows into the new Module/Video/etc. tables. Then set `content = NULL`. Drop `content` column in a final migration (Migration 4) only after verifying all data migrated correctly.

### Pattern 3: SQLite vs PostgreSQL Enum Handling

SQLite stores enums as VARCHAR — extending `CourseStatus` to add `has_unpublished_changes` is a simple `ALTER TABLE` on SQLite but requires special handling on PostgreSQL (`ALTER TYPE` with `USING` clause).

For PostgreSQL, Alembic does NOT auto-handle enum extension. The migration must include:
```python
# For PostgreSQL enum extension
from alembic import op
import sqlalchemy as sa

def upgrade():
    # SQLite: just alter column; PostgreSQL: alter type first
    op.execute("ALTER TYPE coursestatus ADD VALUE 'has_unpublished_changes'")
    # Then the column alter:
    # op.alter_column('courses', 'status', ...)
```

Since this project uses SQLite in dev and PostgreSQL in prod, the migration must detect the dialect and branch:
```python
def upgrade():
    bind = op.get_bind()
    if bind.dialect.name == 'postgresql':
        op.execute("ALTER TYPE coursestatus ADD VALUE IF NOT EXISTS 'has_unpublished_changes'")
    # SQLite handles this transparently via the server_default
```

### Pattern 4: Course.content Data Migration

The existing `Course.content` column is `nullable=True`. Most course records in the dev DB likely have a JSON blob. The migration script must:
1. Read each row from `courses` where `content IS NOT NULL`
2. Parse the JSON structure
3. Insert corresponding `modules`, `videos`, `slides`, `blocks` rows
4. Set `content = NULL` on migrated rows
5. Column drop happens in a final migration after verification

```python
# Inside Migration 3 (data migration) — schematic only
def upgrade():
    connection = op.get_bind()
    courses = connection.execute(sa.text("SELECT id, content FROM courses WHERE content IS NOT NULL")).fetchall()
    for course_id, content_json in courses:
        if content_json:
            _migrate_course_content(connection, course_id, content_json)
    connection.execute(sa.text("UPDATE courses SET content = NULL WHERE content IS NOT NULL"))
```

### Pattern 5: Coolify Start Command

Current `start.sh` runs `uvicorn main:app` directly. Coolify uses its own start command (configured in the Coolify dashboard under "Start Command" in the application settings), not `start.sh`.

The Coolify start command must become:
```bash
cd backend && alembic upgrade head && uvicorn main:app --host 0.0.0.0 --port 8000
```

If Coolify runs from the project root:
```bash
cd backend && pip install alembic psycopg2-binary -q && alembic upgrade head && uvicorn main:app --host 0.0.0.0 --port 8000
```

The `&&` chaining means Coolify aborts if `alembic upgrade head` fails — this is the correct behaviour.

### Anti-Patterns to Avoid
- **Using `Base.metadata.create_all()` for new tables in production:** `init_db()` in `database.py` calls `create_all()` on startup. After Alembic is set up, `create_all()` should not be the source of truth for schema changes. Keep `init_db()` for dev convenience and testing but Alembic migrations are the production path.
- **Hardcoding SQLite URL in alembic.ini:** Will break on PostgreSQL prod. Use `config.set_main_option()` in `env.py` to override with `settings.DB_URL`.
- **Dropping `content` column in same migration as data migration:** Two-step process — migrate data first, verify, then drop column in a separate migration.
- **Using positional `order_index` for learner progress tracking:** `order_index` is display order only. Enrollment progress must track by stable ID, never by position.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Schema migration | Manual `ALTER TABLE` SQL scripts | Alembic | Version control, downgrade, CI/CD integration — already mandated by spec |
| Enum extension on PostgreSQL | Custom ALTER TYPE logic | Alembic's dialect-aware migration with `op.execute()` | PostgreSQL enum ALTER TYPE has gotchas (cannot run inside transaction) |
| JSON-to-relational migration | Ad-hoc Python script outside migrations | Alembic data migration in `upgrade()` | Migration must be reproducible, version-controlled, and run atomically |

**Key insight:** All schema and data changes belong in Alembic migration scripts. Nothing in this phase should require manual DB intervention.

---

## Common Pitfalls

### Pitfall 1: Alembic `autogenerate` Misses SQLite-Specific Types

**What goes wrong:** Running `alembic revision --autogenerate` against the SQLite dev DB produces migrations with SQLite-specific column types (VARCHAR instead of Enum, etc.) that fail on PostgreSQL prod.

**Why it happens:** SQLAlchemy's reflection of SQLite doesn't preserve the original Python-level types. Autogenerate reads from the live DB, which has already collapsed Enum to VARCHAR.

**How to avoid:** Write migration scripts manually rather than using `--autogenerate`. The column definitions in `models.py` are the source of truth. Write the `op.create_table()` calls by hand using the exact SQLAlchemy column types.

**Warning signs:** Migration runs fine in dev (SQLite), fails on prod (PostgreSQL) with type errors.

### Pitfall 2: PostgreSQL `ALTER TYPE ... ADD VALUE` Cannot Run Inside a Transaction

**What goes wrong:** Alembic wraps migrations in transactions by default. PostgreSQL raises `ERROR: ALTER TYPE ... ADD VALUE cannot run inside a transaction block` when trying to extend an enum inside a transaction.

**Why it happens:** PostgreSQL restriction — enum modification is DDL that cannot be transactional.

**How to avoid:** Use `with op.get_context().autocommit_block():` for the enum ALTER in PostgreSQL migrations:
```python
def upgrade():
    bind = op.get_bind()
    if bind.dialect.name == 'postgresql':
        with op.get_context().autocommit_block():
            op.execute("ALTER TYPE coursestatus ADD VALUE IF NOT EXISTS 'has_unpublished_changes'")
```

**Warning signs:** Migration fails on prod with transaction block error but passes in dev.

### Pitfall 3: `init_db()` Creates Tables Before Alembic Runs

**What goes wrong:** `database.py` `init_db()` is called in `main.py`'s lifespan startup. If Alembic migrations haven't run yet (first deploy), `init_db()` creates tables using `create_all()` — but without Alembic version tracking. On the next deploy, `alembic upgrade head` sees no alembic_version table and tries to run all migrations on already-existing tables, causing errors.

**Why it happens:** Two systems managing the same schema simultaneously.

**How to avoid:** After Alembic is set up and initial migrations have run once, `init_db()` is safe because `create_all()` is idempotent (skips existing tables). On a fresh DB, `alembic upgrade head` runs first (in the Coolify start command before `uvicorn`), creating tables including `alembic_version`. Then `init_db()` runs at FastAPI startup and finds all tables already exist — no-op. This coexistence works. Do NOT remove `init_db()` (tests depend on it).

**Warning signs:** `alembic upgrade head` errors with "table already exists" on first-ever deploy of a fresh DB.

**Fix:** On a fresh DB, stamp the base after `create_all()` runs: `alembic stamp head` — but this is a one-time manual step that should be documented.

### Pitfall 4: `Course.content` Data Migration — Unknown JSON Shape

**What goes wrong:** The migration script tries to iterate `Course.content` rows but the JSON structure is inconsistent across older vs newer course records (created by different code versions).

**Why it happens:** The JSON blob schema was never formally versioned. Different features added different keys at different times.

**How to avoid:** Before writing the migration, inspect actual data in `lms.db`:
```sql
SELECT id, json_extract(content, '$') FROM courses WHERE content IS NOT NULL;
```
Write the migration to handle missing keys gracefully (`content.get('modules', [])`, etc.) rather than assuming a complete structure. Log any courses that could not be migrated.

**Warning signs:** Migration script throws `KeyError` or `TypeError` on specific course records.

### Pitfall 5: `order_index` Drift Under Concurrent Saves

**What goes wrong:** (Documented in PITFALLS.md, Pitfall 5.) Two saves in flight simultaneously result in duplicate `order_index` values.

**How to avoid:** The data model itself must enforce correctness: implement reorder as a single transaction updating ALL sibling `order_index` values atomically. Never update `order_index` in a field-level PATCH — only via dedicated reorder endpoints.

---

## Code Examples

Verified patterns from project codebase and Alembic documentation:

### Alembic Initial Setup
```bash
# Run from backend/ directory
alembic init alembic
```
Then edit `alembic/env.py` to import Base and override URL (see Pattern 1 above).

### Migration 1: Extend courses table
```python
# alembic/versions/001_extend_courses_table.py
from alembic import op
import sqlalchemy as sa

def upgrade():
    # All nullable — zero risk to existing data
    op.add_column('courses', sa.Column('slug', sa.String(200), nullable=True))
    op.add_column('courses', sa.Column('summary', sa.Text(), nullable=True))
    op.add_column('courses', sa.Column('thumbnail_url', sa.String(500), nullable=True))
    op.add_column('courses', sa.Column('audience_level', sa.String(50), nullable=True))
    op.add_column('courses', sa.Column('learning_objectives', sa.JSON(), nullable=True))
    op.add_column('courses', sa.Column('category', sa.String(100), nullable=True))
    op.add_column('courses', sa.Column('tags', sa.JSON(), nullable=True))
    op.add_column('courses', sa.Column('estimated_duration_minutes', sa.Integer(), nullable=True))
    op.add_column('courses', sa.Column('ai_tone_preset', sa.String(50), nullable=True))
    op.add_column('courses', sa.Column('ai_custom_prompt', sa.Text(), nullable=True))
    op.add_column('courses', sa.Column('navigation_mode', sa.String(20), nullable=True, server_default='sequential'))
    op.add_column('courses', sa.Column('default_pass_rate', sa.Integer(), nullable=True, server_default='80'))
    op.add_column('courses', sa.Column('default_quiz_attempts', sa.Integer(), nullable=True, server_default='3'))
    op.add_column('courses', sa.Column('default_quiz_time_limit_seconds', sa.Integer(), nullable=True))
    op.add_column('courses', sa.Column('certificate_enabled', sa.Boolean(), nullable=True, server_default='1'))
    op.add_column('courses', sa.Column('published_at', sa.DateTime(), nullable=True))
    op.add_column('courses', sa.Column('version', sa.Integer(), nullable=True, server_default='1'))

def downgrade():
    # SQLite does not support DROP COLUMN in SQLAlchemy < 2.0 on older SQLite;
    # SQLAlchemy 2.0 + SQLite 3.35+ supports it. Use batch mode for safety.
    with op.batch_alter_table('courses') as batch_op:
        for col in ['slug','summary','thumbnail_url','audience_level','learning_objectives',
                    'category','tags','estimated_duration_minutes','ai_tone_preset',
                    'ai_custom_prompt','navigation_mode','default_pass_rate',
                    'default_quiz_attempts','default_quiz_time_limit_seconds',
                    'certificate_enabled','published_at','version']:
            batch_op.drop_column(col)
```

### Migration 2: Create new tables (module table example)
```python
# alembic/versions/002_create_new_tables.py
from alembic import op
import sqlalchemy as sa

def upgrade():
    op.create_table('modules',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('course_id', sa.Integer(), sa.ForeignKey('courses.id', ondelete='CASCADE'), nullable=False),
        sa.Column('order_index', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('learning_objectives', sa.JSON(), nullable=True),
        sa.Column('estimated_duration_minutes', sa.Integer(), nullable=True),
        sa.Column('pass_rate_override', sa.Integer(), nullable=True),
        sa.Column('unlock_rule', sa.String(50), nullable=True, server_default='after_previous'),
        sa.Column('unlock_days_after_enrolment', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(20), nullable=True, server_default='draft'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_module_course_order', 'modules', ['course_id', 'order_index'])
    # ... repeat for videos, slides, blocks, quizzes, questions, resources, ai_prompt_log

def downgrade():
    op.drop_table('modules')
    # ... drop all in reverse order to respect FK dependencies
```

### IMPORTANT: Use `op.batch_alter_table` for SQLite DROP COLUMN
```python
# SQLite requires batch mode for ALTER TABLE operations
with op.batch_alter_table('courses') as batch_op:
    batch_op.drop_column('content')
```

---

## Full New Table Specifications

Authoritative column lists from spec section 2 and ARCHITECTURE.md:

### modules
| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| id | Integer PK | No | auto | |
| course_id | Integer FK(courses) | No | | CASCADE delete |
| order_index | Integer | No | 0 | |
| title | String(500) | No | | |
| description | Text | Yes | | |
| learning_objectives | JSON | Yes | | array of strings |
| estimated_duration_minutes | Integer | Yes | | auto-calculated |
| pass_rate_override | Integer | Yes | | overrides course default |
| unlock_rule | String(50) | Yes | after_previous | immediate/after_previous/scheduled_days |
| unlock_days_after_enrolment | Integer | Yes | | only for scheduled_days rule |
| status | String(20) | Yes | draft | |
| created_at | DateTime | No | now | |
| updated_at | DateTime | Yes | | |

### videos
| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| id | Integer PK | No | auto | |
| module_id | Integer FK(modules) | No | | CASCADE delete |
| order_index | Integer | No | 0 | |
| title | String(500) | No | | |
| description | Text | Yes | | |
| video_type | String(50) | No | slideshow_narrated | slideshow_narrated/slideshow_silent/talking_head/uploaded |
| estimated_duration_seconds | Integer | Yes | | auto from slides |
| narration_voice_id | String(100) | Yes | | ElevenLabs voice ID |
| source_video_url | String(500) | Yes | | for video_type=uploaded |
| status | String(20) | Yes | draft | |
| created_at | DateTime | No | now | |
| updated_at | DateTime | Yes | | |

### slides
| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| id | Integer PK | No | auto | |
| video_id | Integer FK(videos) | No | | CASCADE delete |
| order_index | Integer | No | 0 | |
| layout_id | String(50) | Yes | | references layout presets |
| duration_seconds | Integer | Yes | | creator-set or auto |
| narration_script | Text | Yes | | |
| narration_audio_url | String(500) | Yes | | generated |
| narration_script_hash | String(64) | Yes | | SHA256 for TTS cache invalidation |
| transition | String(20) | Yes | none | none/fade/slide |
| status | String(20) | Yes | draft | |
| created_at | DateTime | No | now | |
| updated_at | DateTime | Yes | | |

### blocks
| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| id | Integer PK | No | auto | |
| slide_id | Integer FK(slides) | No | | CASCADE delete |
| order_index | Integer | No | 0 | z-order / layering |
| type | String(50) | No | | text/heading/image/video_embed/code/quote/list/divider/callout |
| content | JSON | Yes | | schema varies by type |
| style | JSON | Yes | | font/color overrides |
| alt_text | String(500) | Yes | | required for image type (enforced at API layer) |
| grid_position | JSON | Yes | | {x, y, width, height} |
| created_at | DateTime | No | now | |
| updated_at | DateTime | Yes | | |

### quizzes
| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| id | Integer PK | No | auto | |
| module_id | Integer FK(modules) | Yes | | nullable — can be module or video level |
| video_id | Integer FK(videos) | Yes | | nullable — for inline knowledge checks |
| order_index | Integer | No | 0 | |
| title | String(500) | No | | |
| description | Text | Yes | | |
| quiz_type | String(50) | No | knowledge_check | knowledge_check/module_assessment/final_exam |
| pass_rate | Integer | No | 80 | percent |
| attempts_allowed | Integer | No | 3 | -1 for unlimited |
| time_limit_seconds | Integer | Yes | | null = no limit |
| shuffle_questions | Boolean | No | False | |
| show_feedback | String(20) | No | immediate | immediate/end/never |
| on_fail_action | String(20) | No | retake | retake/review/lockout |
| status | String(20) | Yes | draft | |
| created_at | DateTime | No | now | |
| updated_at | DateTime | Yes | | |

### questions
| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| id | Integer PK | No | auto | |
| quiz_id | Integer FK(quizzes) | No | | CASCADE delete |
| order_index | Integer | No | 0 | |
| type | String(50) | No | | mcq_single/mcq_multi/true_false/fill_blank/short_answer/drag_match |
| prompt | Text | No | | |
| points | Integer | No | 1 | |
| explanation | Text | Yes | | shown after answer |
| options | JSON | Yes | | array for choice types |
| correct_answer | JSON | Yes | | schema varies by type |
| linked_objective_id | Integer | Yes | | maps to course learning_objectives index |
| difficulty | String(20) | Yes | | easy/medium/hard |
| created_at | DateTime | No | now | |
| updated_at | DateTime | Yes | | |

### resources
| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| id | Integer PK | No | auto | |
| module_id | Integer FK(modules) | No | | CASCADE delete — NOTE: spec and ARCH link to module, not course |
| type | String(50) | No | | pdf/link/download/worksheet |
| title | String(500) | No | | |
| url_or_file | String(500) | No | | URL or local path |
| visible_to_learner | Boolean | No | True | |
| created_at | DateTime | No | now | |

### ai_prompt_log
| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| id | Integer PK | No | auto | |
| creator_id | Integer FK(users) | No | | |
| operation | String(100) | No | | e.g. generate_description |
| inputs | JSON | Yes | | |
| output | Text | Yes | | |
| model_tier | String(50) | Yes | | |
| tokens_used | Integer | Yes | | |
| created_at | DateTime | No | now | index this column |

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `Base.metadata.create_all()` for all schema changes | Alembic migrations for all schema changes | Phase 10 (this phase) | Enables rolling deploys, downgrade, version history |
| `Course.content` JSON blob for course structure | Relational tables (Module, Video, Slide, Block, Quiz, Question, Resource) | Phase 10 (this phase) | Enables relational queries, FK integrity, per-entity status tracking |
| `CourseStatus` with 3 values (draft/published/archived) | Extended with `has_unpublished_changes` | Phase 10 | Enables the publish flow state machine |

---

## Open Questions

1. **Does Coolify use a committed start script or a dashboard-configured start command?**
   - What we know: `start.sh` exists but just runs uvicorn directly; no Procfile or nixpacks.toml found
   - What's unclear: Where in Coolify is the start command configured — in the dashboard UI or a file?
   - Recommendation: Check Coolify dashboard for the application's "Start Command" setting. Update it to `cd backend && alembic upgrade head && uvicorn main:app --host 0.0.0.0 --port 8000`. If Coolify reads a Procfile, create one.

2. **What is the DB_URL in production (PostgreSQL)?**
   - What we know: `config.py` hardcodes `sqlite:///./lms.db` as default; settings loads from `.env`
   - What's unclear: Is a PostgreSQL URL set in Coolify environment variables? If not, prod is also running SQLite.
   - Recommendation: Verify in Coolify env vars. If PostgreSQL is not configured, prod is SQLite — acceptable for now but enum extension migration must handle both dialects.

3. **What data is in existing `Course.content` JSON blobs?**
   - What we know: The column is nullable; the old spec stored course structure there
   - What's unclear: How many courses have content? What does the JSON structure look like?
   - Recommendation: Before writing the data migration, run `SELECT id, content FROM courses WHERE content IS NOT NULL;` against `lms.db` to inspect actual shape. May be zero rows — in which case data migration is trivial (just set content=NULL and drop column).

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.1.1 |
| Config file | None (uses default discovery from `backend/` dir) |
| Quick run command | `cd backend && python -m pytest tests/ -x -q` |
| Full suite command | `cd backend && python -m pytest tests/ -v` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DATA-01 | Module table exists with correct columns | smoke | `pytest tests/test_data_models.py::test_module_table_exists -x` | Wave 0 |
| DATA-02 | Video table exists with correct columns | smoke | `pytest tests/test_data_models.py::test_video_table_exists -x` | Wave 0 |
| DATA-03 | Slide table exists with correct columns | smoke | `pytest tests/test_data_models.py::test_slide_table_exists -x` | Wave 0 |
| DATA-04 | Block table exists with correct columns | smoke | `pytest tests/test_data_models.py::test_block_table_exists -x` | Wave 0 |
| DATA-05 | Quiz table exists with correct columns | smoke | `pytest tests/test_data_models.py::test_quiz_table_exists -x` | Wave 0 |
| DATA-06 | Question table exists with correct columns | smoke | `pytest tests/test_data_models.py::test_question_table_exists -x` | Wave 0 |
| DATA-07 | Resource table exists with correct columns | smoke | `pytest tests/test_data_models.py::test_resource_table_exists -x` | Wave 0 |
| DATA-08 | alembic upgrade head runs without error | smoke | `pytest tests/test_data_models.py::test_alembic_migrations_run -x` | Wave 0 |
| DATA-09 | Course.content column absent after migration | smoke | `pytest tests/test_data_models.py::test_content_column_absent -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `cd backend && python -m pytest tests/test_data_models.py -x -q`
- **Per wave merge:** `cd backend && python -m pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `backend/tests/test_data_models.py` — covers DATA-01 through DATA-09 (all new table existence and column checks)
- [ ] Alembic install: `pip install alembic` — not in requirements.txt

Note: existing `conftest.py` uses `Base.metadata.create_all()` directly — this is correct for tests (Alembic is not needed in the test environment; tests create schema from models directly). New model classes must be imported in `conftest.py` or `models/__init__.py` to be included in `create_all()`.

---

## Sources

### Primary (HIGH confidence)
- Direct inspection of `backend/models/models.py` — confirmed exact existing schema
- Direct inspection of `backend/database.py` — confirmed `create_all()` pattern, no Alembic
- Direct inspection of `backend/requirements.txt` — confirmed Alembic NOT installed
- Direct inspection of `backend/main.py` — confirmed no migration step in startup
- Direct inspection of `backend/config.py` — confirmed SQLite default, env-var override pattern
- `LMS platform/AI_COURSE_BUILDER_SPEC.md` section 2 — authoritative column-level data model
- `.planning/research/ARCHITECTURE.md` Data Model section — confirmed column lists for all 8 new tables

### Secondary (MEDIUM confidence)
- `.planning/research/PITFALLS.md` Pitfalls 4, 5, 10 — data model migration warnings, order_index drift, versioning
- `.planning/STATE.md` Stack Decisions — "Alembic for all schema migrations" confirmed decision

### Tertiary (LOW confidence)
- Alembic PostgreSQL enum ALTER TYPE transaction restriction — known from training data; verify against Alembic docs before writing the migration

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — Alembic mandate is locked; SQLAlchemy already installed; versions confirmed in requirements.txt
- Architecture: HIGH — existing models inspected directly; Alembic not present confirmed; column specs from spec section 2
- Pitfalls: HIGH — most pitfalls derived from direct codebase inspection (init_db conflict, no Alembic, SQLite/PostgreSQL enum issue confirmed by code review)

**Research date:** 2026-05-08
**Valid until:** 2026-06-08 (30 days — SQLAlchemy/Alembic APIs are stable)
