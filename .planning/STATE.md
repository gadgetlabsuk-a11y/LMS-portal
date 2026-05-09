---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: AI Course Builder
status: completed
last_updated: "2026-05-09T08:56:15.616Z"
last_activity: 2026-05-09 — Completed Phase 10 — Coolify verified at 004 (head), app loading cleanly
progress:
  total_phases: 10
  completed_phases: 2
  total_plans: 15
  completed_plans: 12
---

# State

## Current Position

Phase: 11 (Backend CRUD API) — Plan 04 complete (4/N plans done)
Last completed: 11-04 (uploads endpoint) — POST /api/uploads, 6 tests GREEN, bcrypt patch applied
Status: Executing Phase 11. Plans 01 (modules), 04 (uploads) complete. Plans 02, 03 pending.
Last activity: 2026-05-09 — Completed 11-04 — POST /api/uploads endpoint live with tests

## Project Reference

See: .planning/PROJECT.md (updated 2026-05-08)

**Core value:** Creators can build and publish high-quality courses without technical knowledge
**Current focus:** Milestone v1.0 — AI Course Builder (Phases 9–18)

## Performance Metrics

- Phases complete: 0/10 (v1.0)
- Plans complete: 1/TBD (09-01 done)
- Requirements mapped: 75/75

| Phase | Plan | Duration | Tasks | Files |
|-------|------|----------|-------|-------|
| 09    | 01   | ~4 min   | 2/2   | 19    |
| 09    | 02   | ~2 min   | 2/2   | 4     |
| 09    | 03   | ~6 min   | 2/2   | 7     |
| 09    | 04   | ~8 min   | 2/2   | 6     |
| 09    | 05   | ~4 min   | 2/2   | 6     |
| 09    | 06   | ~7 min   | 2/2   | 7     |
| 09    | 07   | ~10 min  | 2/2   | 3     |
| 10    | 01   | ~15 min  | 2/2   | 6     |
| 10    | 02   | ~12 min  | 2/2   | 2     |
| 10    | 03   | ~12 min  | 2/2   | 4     |
| 10    | 04   | ~5 min   | 2/2   | 1     |
| 11    | 04   | ~3 min   | 2/2   | 4     |

## Accumulated Context

### Decisions from 11-04

- No DB record created on upload — Resource table (Plan 03) handles file-to-module URL linking; uploads.py is purely a file storage primitive
- category form field maps to subfolder: uploads/{category}/{uuid8}_{safe_name} — allows logical separation (thumbnails, slides, documents)
- conftest.py bcrypt 5.0 Python 3.14 fix: monkey-patch `passlib.handlers.bcrypt.detect_wrap_bug = lambda *a, **k: False` before any passlib import — the wrap bug being tested is >10 year old, not present in modern bcrypt, patch is safe and unblocks all conftest-dependent tests project-wide

### Decisions from 10-03

- Migration 003 uses `lessons` key (not `videos`) when parsing existing Course.content JSON — actual data shape is `modules[].lessons[]`, handled via `module_data.get('videos', module_data.get('lessons', []))`
- Data migration 003 downgrade is intentionally a no-op — content JSON blobs cannot be reconstructed from relational rows; 004 downgrade restores the empty column but data is gone
- SQLite DROP COLUMN pattern established: always use `op.batch_alter_table` context manager; drop indexes before batch operation to avoid constraint conflict during batch rebuild

### Decisions from 10-02

- Course.content column removed cleanly from model class — Alembic migration (Plan 03) handles the DB column drop, no two-code-path handling
- video_type used instead of type on Video model — avoids collision with Python/SQLAlchemy reserved attribute name
- Quiz uses pass_rate and attempts_allowed naming per spec (not pass_score/max_attempts)
- Resource.module_id FK (not course_id) — resources belong to modules per spec, confirmed in research
- test_creator_router.py and test_learn_router.py errors are pre-existing bcrypt/passlib Python 3.14 incompatibility, not introduced by this plan

### Decisions from 10-01

- alembic/env.py uses sys.path.insert(0, parent_dir) so backend package imports (config, models) work without the package being installed
- render_as_batch=True required in both offline and online configure() calls — SQLite does not support DROP/ALTER COLUMN natively
- test_data_models.py uses its own module-scoped test_engine fixture — intentionally avoids conftest.py which imports main.py at module level
- psycopg2-binary in requirements.txt fails on macOS arm64 but builds correctly on Linux (production target)

### Decisions from 09-07

- router.test.tsx rewritten to wrap with AuthProvider + ToastProvider and assert real component behaviour (redirect to /login when unauthenticated) instead of Todo-placeholder text

### Decisions from 09-02

- api.ts reads localStorage 'token' directly to avoid circular dependency with AuthContext (which imports api.ts)
- fetchUserProfile uses raw fetch (not api.get) to avoid circular dependency between AuthContext and api.ts
- 401 handler uses setNavigate singleton pattern so api.ts can redirect without being a React hook
- TOKEN_KEY = 'token' constant in AuthContext enforces the key contract; changing it would log out live users

### Decisions from 09-05

- CourseManagementPage placed in pages/admin/ but has no admin-only role checks — shared safely with /creator/courses route
- File upload and blob download in CourseManagementPage use raw fetch + API_BASE — api service cannot handle multipart/FormData or streaming blob responses
- handleViewPlayer opens API_BASE player URL in new tab (not SPA navigation) since course player is a FastAPI-rendered iframe page

### Decisions from 09-06

- CourseDetail and CourseViewerPage use useParams (not useLocation + pathname.split) — SPA-correct and avoids hash/basename edge cases
- navigate(-1) replaces window.history.back() in CourseViewerPage — keeps navigation within React Router history stack
- API_BASE exported from api.ts so CourseViewerPage can build iframe src correctly without duplicating env detection
- ModuleAccordion accepts optional onLessonClick prop for future lesson-click wiring without a breaking change

### Decisions from 09-04

- LoginPage navigates to '/' on success; SmartRedirect handles role dispatch to avoid duplicating role-routing logic
- Auth guards use Navigate replace=true on all redirects to prevent back-button loops
- AdminLayout/CreatorLayout define navItems as module-level const (not inside component) for stable reference

### Decisions from 09-03

- Badge uses CSS class approach (.badge.info etc.) matching globals.css, not inline Tailwind — preserves monolith styling intent
- Textarea uses .custom-textarea CSS class for monospace font and resize:vertical, matching globals.css definition
- Form wrapper divs include mb-4 to match monolith spacing — callers should not add extra margin
- All 7 components use named exports (not default exports) for tree-shaking clarity
- Modal returns null when open=false — conditional rendering handled inside component, not at call site

### Decisions from 09-01

- vitest.config.ts uses `as any` casts on plugins to avoid vite version type mismatch
- tsconfig.node.json uses `composite: true` + `emitDeclarationOnly` (not noEmit) for tsc -b compatibility
- vite-env.d.ts required in src/ for import.meta.env type support
- frontend/.gitignore created to exclude tsbuildinfo and compiled JS artifacts from tsc -b

### Architecture Decisions

- Backend is stable and well-tested. No breaking changes expected.
- Frontend migration to Vite + React is the first gate — all new UI work goes in the new structure.
- The AI_COURSE_BUILDER_SPEC.md is the authoritative design document for the creator authoring experience.
- Vite + React build output must serve as static files under the `/lms` path prefix (same as current nginx setup).
- `base: '/lms/'` in vite.config.ts (trailing slash required); `basename="/lms"` in BrowserRouter (no trailing slash). These are distinct.
- The existing FastAPI backend already has course CRUD endpoints. New data model (Module, Video, Slide, Block, Quiz) requires Alembic migrations + new API endpoints.

### Known Pitfalls (from research)

1. Vite base/React Router basename mismatch — five nginx emergency commits in this repo confirm this hazard.
2. `Course.content` JSON must be retired in one clean Alembic migration — no two-code-path handling.
3. `order_index` drift under concurrent reorder — use single atomic transaction for all siblings.
4. SSE generators must check `await request.is_disconnected()` at every yield to prevent orphaned Claude API tokens.
5. Slide canvas autosave race — flush pending saves on route change; write block positions only on `onDragEnd`, not during drag.
6. TTS bulk generation storms — use `asyncio.Semaphore(3)`; cache by `narration_script_hash`; update model to `eleven_turbo_v2_5`.
7. PDF extraction — replace raw UTF-8 decode in `document_service.py` with PyMuPDF before connecting to AI pipeline.

### Open Decisions

- TTS provider: ElevenLabs vs OpenAI TTS — resolve before Phase 17. REQUIREMENTS.md specifies ElevenLabs; confirm API key exists.
- SQLite vs PostgreSQL — if more than one creator will author simultaneously at launch, migrate to PostgreSQL before Phase 15 (concurrent SSE + autosave + TTS write lock contention).

### Stack Decisions

- Vite 6 + React 18.3 + TypeScript 5
- shadcn/ui + Tailwind 3.4 (not Mantine — conflicts with Tailwind)
- dnd-kit/sortable for list reordering; react-grid-layout for slide canvas (do not mix)
- TipTap v3 for rich text
- Zustand 5 (editor/UI state) + TanStack Query 5 (server state)
- sse-starlette 2.x for backend SSE
- PyMuPDF (fitz) 1.26 for PDF extraction
- Alembic for all schema migrations

## Session Continuity

Phase 09 complete. All 7 plans (09-01 through 09-07) done. All 27 monolith components extracted, integrated, and deployed. Smoke test passed on buildbench.uk/lms. Next: Phase 10.
