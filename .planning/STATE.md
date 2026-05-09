---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: AI Course Builder
status: completed
last_updated: "2026-05-09T17:59:00Z"
last_activity: 2026-05-09 — Completed 14-02 — SLIDE-11 and SLIDE-12 SSE endpoints GREEN
progress:
  total_phases: 10
  completed_phases: 5
  total_plans: 31
  completed_plans: 27
---

# State

## Current Position

Phase: 14 (Slide Builder & Slide Editor) — IN PROGRESS (2/6 plans done)
Last completed: 14-02 — SLIDE-11 and SLIDE-12 SSE endpoints GREEN (generate-narration, generate-outline).
Status: Phase 14 Plan 02 COMPLETE. Ready for Plan 14-03 (block CRUD).
Last activity: 2026-05-09 — Completed 14-02 — SLIDE-11 and SLIDE-12 SSE endpoints GREEN

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
| 11    | 01   | ~3 min   | 2/2   | 4     |
| Phase 11 P02 | 2 | 2 tasks | 4 files |
| Phase 11 P03 | 2min | 2 tasks | 4 files |
| Phase 12 P01 | 12min | 3 tasks | 3 files |
| Phase 12 P02 | 18min | 2 tasks | 3 files |
| Phase 12 P03 | 22min | 1 tasks | 1 files |
| Phase 12 P04 | 15min | 2 tasks | 4 files |
| Phase 12 P05 | 5min | 2 tasks | 0 files |
| Phase 13 P01 | 2min | 3 tasks | 5 files |
| Phase 13 P02 | 2min | 2 tasks | 2 files |
| Phase 13 P03 | 3 | 3 tasks | 5 files |
| Phase 13 P04 | 5 | 2 tasks | 3 files |
| Phase 13 P05 | 5 | 2 tasks | 0 files |
| Phase 14 P01 | 45min | 3 tasks | 8 files |
| Phase 14 P02 | 15min | 2 tasks | 2 files |
| Phase 14 P02 | 15min | 2 tasks | 2 files |

## Accumulated Context

### Decisions from 14-02

- SSE routes POST /api/slides/{slide_id}/ai/* declared BEFORE GET /api/slides/{slide_id} wildcard — FastAPI declaration-order path matching; same pattern as modules.py from Phase 12-02
- _get_slide_or_404 helper added to slides.py (logic duplicated from blocks.py) — keeps SSE endpoints self-contained, avoids cross-router import coupling
- Block content text assembled via `content.get("text") or content.get("html")` — handles both plain-text and TipTap HTML block types
- Stale test_lms_tmp.db from interrupted prior run blocked first create_all; deleted before running tests (conftest drops/recreates per test, but can't recover from pre-existing tables)

### Decisions from 14-01

- Frontend TDD RED state: import non-existent files — vitest fails at collection with import resolution error (consistent with Phase 13 pattern)
- Backend TDD RED state: pytest.fail() directly in test functions — produces FAILED not ERROR (consistent with Phase 12/13 pattern)
- New test directories created: frontend/src/components/slide/__tests__/ and frontend/src/store/__tests__/
- react-grid-layout ^2.2.3 (slide canvas), zustand ^5.0.13 (editor store), @tiptap/react+starter-kit ^3.23.1 (rich text) all installed

### Decisions from 13-05

- All 5 browser checks (tree visible, navigation, form save/persist, drag-drop reorder persist, AI SSE streaming) passed on first attempt — no rework required after human verification
- Phase 13 complete: BUILD-01 through BUILD-06 all verified end-to-end in browser

### Decisions from 13-04

- vi.mock('@/services/api') required in ModuleDetailPage tests — api.get called on mount triggers async state updates, test must mock before render
- All common components (Input/Textarea/Select/Button) spread ...props to DOM elements so data-testid attributes pass through directly without wrapper divs
- estimated_duration_minutes stored as string in local state (for controlled Input[type=number]) then parseInt before PUT — avoids React controlled input warning

### Decisions from 13-03

- Shared builder/types.ts exports BuilderModule, BuilderVideo, BuilderQuiz — avoids TS2719 "two types with same name" error when Module/Video interfaces defined locally in multiple builder files
- Badge uses `variant` prop ('info'|'success'|'warning'|'danger'), not `className` — status pills wrapped in `<span data-testid="...">` to expose testid to test queries
- Tests updated with vi.mock('@/services/api') + findByTestId (async) assertions — CourseBuilderPage shows loading state gate until API fetch resolves; synchronous getByTestId fails before resolve
- SortableModuleRow calls useSensors internally (not via prop) — each module gets its own sensor instance, prevents drag events leaking between module DndContexts

### Decisions from 13-02

- creator_course conftest fixture returns an ORM object — use `.id` attribute access, not `['id']` dict subscript (plan sample code used dict notation)
- AppStatus.should_exit_event = None reset applied to all SSE tests (sse-starlette 2.x anyio.Event cross-loop RuntimeError fix, same as 12-02 decision)
- _stream_text mock uses `side_effect=async_gen_fn` pattern (not `return_value=...`) in SSE integration tests

### Decisions from 13-01

- Frontend TDD RED state: import non-existent ../CourseBuilderPage and ../ModuleDetailPage — vitest fails at collection with import resolution error (correct RED state; no test body code needed)
- Backend TDD RED state: pytest.fail() directly in test functions — produces FAILED not ERROR, consistent with Phase 12 Wave 0 pattern from STATE.md
- venv activation required for backend pytest — pyotp and other deps not on system path (use `source venv/bin/activate` or `python3 -m pytest` from venv)

### Decisions from 12-04

- Select component uses `options` prop (array of `{value, label}`) not JSX children — actual Select.tsx interface; plan showed child `<option>` pseudo-code
- Objectives SSE streaming accumulates all tokens into local string then parses "- " prefixed lines on completion — avoids partial-line state updates creating malformed objective arrays
- Builder stub route wrapped in CreatorLayout + ProtectedRoute(creatorRoute) for consistent auth/layout — bare div stub would bypass auth
- CreatorCourseListPage handles both API response shapes: array or `{courses: []}` — defensive against minor backend format variation

### Decisions from 12-02

- Module-level `claude_service = ClaudeService()` singleton in courses.py; function-local instantiations in legacy generate handlers left unchanged to avoid regression
- SSE routes /ai/generate-description and /ai/generate-objectives declared BEFORE /{course_id} routes — FastAPI path collision prevention
- `AppStatus.should_exit_event = None` reset before each SSE test — sse-starlette 2.x creates anyio.Event class-level attribute; TestClient cycles event loops between tests causing cross-loop RuntimeError
- CourseResponse extended with audience_level, learning_objectives (Optional[List[str]]), ai_tone_preset — all Optional for backward compatibility
- test_learn_router.py::test_returns_only_published_courses confirmed pre-existing failure (unrelated to 12-02)

### Decisions from 12-03

- NODE_BADGE map uses "assessment" for quiz type so badge text does not collide with /Quiz/i label match in tests — prevents getAllByText count off-by-one
- SkeletonTreePreview uses inline styles (not Tailwind classes) — jsdom test environment does not process PostCSS; inline styles ensure component is self-contained in test runs
- buildSkeletonNodes caps moduleCount and videosPerModule at 20 — prevents DOM bloat without throwing errors

### Decisions from 12-01

- Backend stubs use pytest.fail() directly (no Phase 12 imports) — ensures clean FAILED state (not ImportError/ERROR) before any implementation exists
- Frontend Wave 0 stub uses direct import of non-existent SkeletonTreePreview.tsx — vitest import failure at collection is the acceptable RED state
- sse-starlette==2.1.3 added to requirements.txt after httpx (grouped with async/HTTP dependencies); required for COURSE-02 and COURSE-03 SSE endpoints

### Decisions from 11-03

- blocks.py _get_slide_or_404 joins 4 tables (Slide→Video→Module→Course) then uses ORM relationship chain (slide.video.module.course) for ownership check — consistent with the slides.py single-item lookup pattern
- quizzes.py _get_quiz_or_404 joins Quiz→Module→Course only (Quiz.module_id always set when created via module endpoint); video-linked quiz ownership traversal deferred
- Question reorder uses identical atomic single-transaction pattern from modules.py — single db.commit() after loop, prevents order_index drift
- pass_rate and attempts_allowed naming confirmed throughout (not pass_score/max_attempts)
- setup_hierarchy fixture in test file builds full course→module→video→slide chain via API calls for realistic integration coverage

### Decisions from 11-02

- videos.py uses _get_module_or_404 helper (module.join(Course)) for create/list/reorder; get/update/delete use inline join for single-item fetch — consistent with modules.py pattern
- slides.py uses _get_video_or_404 helper (video.join(Module).join(Course)) for create/list/reorder; four-table Slide.join(Video).join(Module).join(Course) for single-item operations
- Test fixtures chain via API calls (creator_module → creator_video → creator_slide) for realistic integration coverage; creator_course reused from conftest

### Decisions from 11-01

- Module router uses single APIRouter with no prefix and explicit /api/courses/... and /api/modules/... paths — avoids prefix collision with courses.py which already owns /api/courses prefix
- Reorder uses single db.commit() after all order_index assignments in loop — atomicity guarantee, prevents drift (State pitfall #3)
- conftest.py Course fixtures had stale content= kwarg (column removed in Phase 10 migration 003); removed to unblock all conftest-dependent tests

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
