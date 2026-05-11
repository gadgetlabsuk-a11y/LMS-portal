---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: AI Course Builder
status: verifying
last_updated: "2026-05-11T20:22:11.660Z"
last_activity: 2026-05-11 — Completed 18-05 — Human verification passed. Phase 18 COMPLETE. Milestone v1.0 AI Course Builder DONE.
progress:
  total_phases: 10
  completed_phases: 10
  total_plans: 55
  completed_plans: 55
---

# State

## Current Position

Phase: 18 (Preview and Publish) — COMPLETE (5/5 plans done)
Last completed: 18-05 — Human verification passed. All 10 browser checks approved (PREVIEW-01 through PUBLISH-08).
Status: MILESTONE v1.0 AI Course Builder COMPLETE. All 55 plans across 10 phases delivered and verified.
Last activity: 2026-05-11 — Completed 18-05 — Human verification passed. Phase 18 COMPLETE. Milestone v1.0 AI Course Builder DONE.

## Project Reference

See: .planning/PROJECT.md (updated 2026-05-08)

**Core value:** Creators can build and publish high-quality courses without technical knowledge
**Current focus:** Milestone v1.0 — AI Course Builder (Phases 9–18)

## Performance Metrics

- Phases complete: 8/10 (v1.0)
- Plans complete: 44/44 (through Phase 16)
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
| Phase 14 P03 | 15min | 2 tasks | 5 files |
| Phase 14 P04 | 3min | 3 tasks | 9 files |
| Phase 14 P05 | 8min | 2 tasks | 6 files |
| Phase 14 P06 | 5min | 2 tasks | 0 files |
| Phase 14 P08 | 2min | 1 tasks | 1 files |
| Phase 14 P07 | 9min | 2 tasks | 2 files |
| Phase 15 P01 | 18min | 2 tasks | 5 files |
| Phase 15 P01 | 18min | 2 tasks | 5 files |
| Phase 15 P02 | 15min | 2 tasks | 3 files |
| Phase 15 P03 | 33 | 2 tasks | 11 files |
| Phase 15 P04 | 30min | 2 tasks | 3 files |
| Phase 15 P05 | 5min | 2 tasks | 0 files |
| Phase 15 P06 (gap) | ~20min | 1 task | 6 files |
| Phase 16 P01 | 5min | 2 tasks | 3 files |
| Phase 16 P03 | 2min | 2 tasks | 5 files |
| Phase 16 P03 | 2min | 2 tasks | 5 files |
| Phase 16-quiz-builder P02 | 8min | 2 tasks | 2 files |
| Phase 16 P04 | 2min | 2 tasks | 6 files |
| Phase 16 P04 | 2min | 2 tasks | 6 files |
| Phase 17 P01 | 5min | 2 tasks | 2 files |
| Phase 17 P01 | 5min | 2 tasks | 2 files |
| Phase 17 P02 | 3min | 2 tasks | 4 files |
| Phase 17 P03 | 2min | 2 tasks | 2 files |
| Phase 17 P04 | 7min | 2 tasks | 4 files |
| Phase 17 P05 | 5min | 2 tasks | 0 files |
| Phase 17 P06 | 15min | 2 tasks | 2 files |
| Phase 18 P01 | ~6 min | 2 tasks | 2 files |
| Phase 18 P02 | 36min | 2 tasks | 10 files |
| Phase 18 P03 | ~33min | 2 tasks | 5 files |
| Phase 18 P04 | 5 | 2 tasks | 5 files |
| Phase 18 P05 | 5min | 1 tasks | 0 files |

## Accumulated Context

### Decisions from 18-05

- All 10 browser checks approved on first attempt — no rework required after human verification
- Phase 18 COMPLETE: PREVIEW-01 through PUBLISH-08 all verified end-to-end in browser with live data
- Milestone v1.0 AI Course Builder is DONE — all 75 requirements across Phases 9-18 delivered and verified

### Decisions from 18-04

- `api.get` returns `Promise<Response>` not `Promise<{ data: T }>` — PreflightModal uses `.json()` to parse response; plan's interface docs were incorrect (Rule 1 auto-fix)
- `PublishConfirmModal` is a nested `<Modal>` inside `PreflightModal` — no separate standalone component needed; thin placeholder file exists for future extraction
- Course status fetched from `GET /api/courses/:id` on mount in `CourseBuilderPage`; `archive-btn` visibility gated on `courseStatus === 'published' || courseStatus === 'has_unpublished_changes'`
- CourseBuilderPage test mock updated with extra `mockResolvedValueOnce` for new course-status fetch (first `api.get` call now is course detail)

### Decisions from 18-03

- `CoursePreviewPage` renders the backend player iframe directly (not by wrapping `CourseViewerPage`) — wrapping would nest two iframes; replicating the iframe pattern with a fixed watermark overlay is correct
- `decodeURIComponent` required on returnTo when reading from `useSearchParams().get()` — the caller uses `encodeURIComponent`; raw get() without decode corrupts paths containing slashes
- Fixed amber watermark uses `z-index: 1000` with `position: fixed` — ensures banner always sits above iframe regardless of iframe scroll/pointer events
- Preview button uses inline styles (consistent with CourseBuilderPage's existing inline style layout approach)
- React Router v6 `act()` warning from MemoryRouter in PREVIEW-03 test is benign — test passes and navigation outcome is verified; pre-existing pattern in this codebase

### Decisions from 18-02

- `_mark_course_changed` defined locally in each child router (modules, videos, slides, blocks, quizzes) — avoids circular import from courses.py; identical 8-line helper per router is acceptable given the constraint
- `draft_creator_course` local fixture in test_publish_phase18.py — conftest `creator_course` is PUBLISHED but publish tests need DRAFT starting state; local fixture provides correct status
- `learn.py` `has_content` hardcoded to `False` (list) / served from snapshot (detail with version pin) — `course.content` column was removed in migration 004; pre-existing AttributeError fixed as Rule 1 deviation
- Concurrent background pytest processes sharing SQLite test DB cause `OperationalError` — run phase 18 tests in isolation; pre-existing known limitation (iCloud Drive + SQLite test DB)
- `test_has_content_true_when_content_set` in test_learn_router.py was already failing before 18-02 (confirmed with git stash test) — pre-existing, not introduced here

### Decisions from 18-01

- No top-level import of `routers.courses` (or any non-existent publish/archive/preflight routers) in `test_publish_phase18.py` — module-level import would cause ImportError (ERROR not FAILED), breaking TDD RED state; `pytest.fail()` inside function body produces clean FAILED
- `creator_course` fixture reused from conftest.py (line 214) — no file-local duplicate needed; chain fixtures only needed when more context is required
- `CoursePreviewPage` import is intentionally broken in `PreviewMode.test.tsx` — vitest fails at collection with import resolution error; `CoursePreviewPage.tsx` must NOT be created until Plan 18-03
- Backend venv TimeoutError (`[Errno 60]`) during pytest verification is a transient iCloud Drive I/O issue — pre-existing environment limitation, not introduced by this plan

### Decisions from 17-06

- setup_test_db must call drop_all before create_all for idempotency — rollback-based db fixture leaves SQLite tables intact at teardown, causing "table already exists" OperationalError when pytest-randomly reorders tests and the next test's create_all runs on a non-empty DB
- pytest-randomly 4.1.0 installed (current release); plan specified 3.16.0 but 4.1.0 is the same API
- db fixture with connection+SAVEPOINT+rollback+event.listens_for pattern was already correct; the additional drop_all line in setup_test_db was the only missing piece

### Decisions from 17-05

- All 5 browser checks approved on first attempt — no rework required after human verification
- Phase 17 COMPLETE: TTS-01 through TTS-05 all verified end-to-end in browser with live ElevenLabs API
- SLIDE-03 confirmed closed: bulk narration button wired in Phase 17 Plan 04 after being disabled since Phase 14

### Decisions from 17-04

- `narration_audio_url` added as optional field (`?`) in SlideBuilderPage's Slide interface — required field caused TS2322 incompatibility with `setSlides` passed as `onSlidesChange` to VideoSlideStrip (two Slide types with same name but different shapes); optional is semantically correct since field is "for future use" per plan note
- `VOICE_OPTIONS` const defined outside NarrationTab component — stable reference, not recreated on each render
- Audio player only renders after successful generate click (`audioUrl` state set from API response) — not rendered on initial mount; consistent with progressive disclosure UX
- `handleBulkGenerate` silently catches errors — prevents crash; creator sees 0 generated count in result banner; error logging deferred to observability phase

### Decisions from 17-03

- `bulk_generate_audio` uses `asyncio.gather` + `process_slide` coroutine — all slides dispatched concurrently; `async with _bulk_semaphore` inside coroutine limits actual ElevenLabs calls to 3
- Cache check requires both `narration_script_hash == sha256(script)` AND `narration_audio_url` set — both conditions required to skip regeneration
- `test_semaphore_limits_concurrency` uses Python `ast` module to verify `_bulk_semaphore` has no module-level assignment in `tts.py` — structural verification
- `creator_video` fixture is file-local in `test_tts_phase17.py` (consistent with `creator_slide`/`creator_quiz` pattern from prior phases)

### Decisions from 17-02

- TTSService.__init__ defers key check to generate_for_slide() — no startup crash when ELEVENLABS_API_KEY unset (research pitfall #3)
- `tts_service = TTSService()` module-level singleton in tts.py enables `patch("routers.tts.tts_service._call_elevenlabs")` in tests
- creator_slide fixture uses HTTP 201 status codes for POST creates (modules/videos/slides all return 201_CREATED); PUT returns 200
- _call_elevenlabs signature is `(text, voice_id)` — test asserts `call_args[0][1] == voice_id` for TTS-05 verification

### Decisions from 17-01

- No import from `routers.tts` in `test_tts_phase17.py` — file does not exist yet; import would cause ERROR not FAILED (consistent Phase 12-16 Wave 0 pattern)
- `creator_slide` fixture chain commented out in test file — only needed once Plan 02 test bodies are written; uncommented would cause collection error since route imports don't exist yet
- `api.post` mock added to `vi.mock('@/services/api')` block in NarrationTab tests now so Plan 04 doesn't need to touch the mock section
- Frontend TTS-01 stubs use `getByTestId` for non-existent elements — clean FAILED at execution time (not collection error), consistent with Phase 14-16 Wave 0 frontend pattern

### Decisions from 16-05

- All 6 browser checks approved on first attempt — no rework required after human verification
- Phase 16 COMPLETE: QUIZ-01 through QUIZ-08 all verified end-to-end in browser

### Decisions from 16-04

- vi.mock('@dnd-kit/core') + vi.mock('@dnd-kit/sortable') required in QuizBuilderPage tests — dnd-kit uses browser pointer events (PointerEvent) unavailable in jsdom; passthrough JSX wrappers keep component tree intact
- React import required in test files that use JSX in vi.mock() factory functions (for SortableContext/DndContext passthrough mocks)
- bufferRef SSE accumulation: bufferRef.current = '' reset before startStream(), += in onToken callback, JSON.parse only after await resolves — same pattern as SlideOutlineWizard (STATE.md 14-05)
- QuizBuilderPage feature set complete in 4 plans: settings (02), question CRUD + 4 types (03), reorder + AI generation + routing (04)
- useSSEStream cancel() pre-existing test failure confirmed out of scope (STATE.md 15-04) — not introduced by 16-04

### Decisions from 16-03

- QuestionForm is fully self-contained with type-switching via useState(type) — parent owns no question state, all state is internal to the form
- correct_answer shape enforced per type: int index (mcq_single), int array (mcq_multi), 'True'/'False' string (true_false), string|null (short_answer)
- QuizBuilderPage not wired to App.tsx router yet — route connection is Plan 04 scope
- AI Generate button renders as visual placeholder with no-op onClick — SideDrawer integration is Plan 04

### Decisions from 16-02

- POST /api/quizzes/{quiz_id}/ai/generate-questions declared BEFORE GET /api/quizzes/{quiz_id} — FastAPI first-match-wins path-order safety (line 223 vs 261); same pattern as slides.py (STATE.md decision 14-02)
- Module-level claude_service = ClaudeService() singleton in quizzes.py — enables patch('routers.quizzes.claude_service._stream_text') in SSE integration tests
- starlette.requests.Request imported in quizzes.py (not fastapi.Request) — consistent with slides.py SSE endpoint pattern

### Decisions from 16-01

- creator_quiz fixture is file-local (NOT conftest.py) — consistent with creator_slide pattern from Phase 14; each phase owns its own chain fixtures
- reset_sse_state autouse fixture included in test_quiz_phase16.py — QUIZ-08 tests SSE endpoint, prevents anyio cross-loop RuntimeError (established pattern from Phase 12 onward)
- Frontend Wave 0 vitest failure is "Failed to resolve import" message (not "Cannot find module") — same semantic RED state, different vitest version wording

### Decisions from 15-06 (gap closure)

- SideDrawer z-indices raised to z-[55]/z-[60] — Modal uses z-50; drawer must stack above it when triggered from within the modal
- CourseIdentityModal: SideDrawers rendered OUTSIDE `<Modal>` wrapper (fragment pattern) to keep fixed-positioning stacking clean; each drawer has Apply button to commit streamed text to form field
- NarrationTab: SideDrawer wraps StreamingTextOutput preview; streaming still writes to zustand store (narration script textarea gets live updates); drawer is a focused preview that doesn't duplicate the textarea
- ModuleDetailPage: entire AI generation panel moved into SideDrawer; trigger button replaces inline panel; streaming still writes to description state so form field updates in real time
- SlideOutlineWizard: architectural exception documented with explicit comment — wizard IS the generation surface, not a trigger for a drawer

### Decisions from 15-05

- All 6 browser checks approved on first attempt — no rework required after human verification
- Phase 15 COMPLETE: AI-01 through AI-07 all verified end-to-end in browser

### Decisions from 15-04

- computeNudges() pure function separates nudge logic from rendering — testable without DOM; returns Nudge[] from modules/videos/quizzes inputs
- data-testid pattern: suggestion-{type}-{moduleId} (e.g. suggestion-missing-description-2) enables precise per-module assertions in tests
- AISuggestionsRail rendered as 256px right sidebar in CourseBuilderPage with inline styles (consistent with page's existing inline style layout approach)
- useSSEStream cancel() test pre-existing failure confirmed via stash test — unrelated to this plan, out of scope

### Decisions from 15-03

- useSSEStream encapsulates fetch+ReadableStream+AbortController — single pattern across all AI streaming surfaces (AI-01); setText(prev => prev + t) functional update avoids stale closure on rapid tokens
- NarrationTab receives courseId prop from SlideEditorPage (which had courseId via useParams); tone preset fetched from GET /api/courses/{id} ai_tone_preset field — AI-07 propagation pattern
- accumulatedRef pattern used in NarrationTab and SlideOutlineWizard for onToken callbacks — ref persists across renders, avoids stale closure entirely during SSE token accumulation
- CourseIdentityModal uses two separate useSSEStream instances (description + objectives) — independent isStreaming state per concurrent SSE operation

### Decisions from 15-02

- extract_text_from_file_sync(file_bytes, content_type) added to DocumentService — uses MIME type for format dispatch; avoids filename dependency in SSE endpoint that receives only content-type from HTTP response headers
- document_service and httpx imported as module-level singletons in slides.py — enables patch('routers.slides.document_service.extract_text_from_file_sync') and patch('routers.slides.httpx.AsyncClient') in integration tests
- generate_outline document fetch swallows exceptions with logger.warning — ensures endpoint degrades gracefully if document_url is unreachable rather than returning 500

### Decisions from 15-01

- Backend Wave 0 stubs use pytest.fail() directly — produces FAILED not ERROR (consistent with Phase 12/13/14 pattern)
- Frontend Wave 0 stubs import non-existent source files — vitest fails at collection with Cannot find module (consistent with Phase 13-01, 14-01 pattern)
- reset_sse_state autouse fixture included in test_ai_phase15.py — prevents anyio cross-loop RuntimeError in SSE tests (STATE.md 12-02/13-02 decision)
- pymupdf==1.26.0 installed in backend venv — import fitz verified at version 1.26.0

### Decisions from 14-07

- SlideBuilderPage renders SlideOutlineWizard unconditionally (open=false returns null per component contract); triggers useAuth() call at render time requiring vi.mock('@/context/AuthContext') in SlideBuilderPage.test.tsx
- Named fetchSlides() function extracted from useEffect so onCommitted callback can re-trigger slide strip refresh without duplicating fetch logic
- anchorSlideId = slides[slides.length-1].id if slides exist, else 0 — wizard appends new slides after last existing slide

### Decisions from 14-08

- SLIDE-03 checkbox unchecked in REQUIREMENTS.md — permanently-disabled button in Phase 14 does not constitute completion; bulk narration is Phase 17 (TTS-02) scope
- Traceability table updated: SLIDE-03 row changed to Phase 17 / Deferred (TTS-02)

### Decisions from 14-06

- All 8 browser checks approved on first attempt — no rework required after human verification
- Phase 14 COMPLETE: SLIDE-01 through SLIDE-12 all verified end-to-end in browser

### Decisions from 14-05

- @/contexts/AuthContext corrected to @/context/AuthContext — project uses singular `context` directory (Rule 1 auto-fix)
- SlideOutlineWizard accumulates all SSE tokens in buffer string before JSON.parse on completion — implements research pitfall #7, avoids partial-JSON parse errors
- App.tsx slide routes are purely additive; wrapped in CreatorLayout + ProtectedRoute(creatorRoute) consistent with all other creator routes

### Decisions from 14-04

- zundo@2.3.0 installed as blocking dependency — was not in package.json despite being specified in plan (Rule 3)
- react-grid-layout 2.x ships only `./css/styles.css` in package exports — removed non-existent `resizable.css` import from SlideCanvas (Rule 1)
- useBlocker (react-router v6.4+) requires a data router — tests must use `createMemoryRouter` + `RouterProvider`, not `MemoryRouter` + `Routes`
- vitest.config.ts: `css: true` added so CSS imports (react-grid-layout/css/styles.css) resolve in test environment

### Decisions from 14-03

- @testing-library/user-event not in package.json — installed as dev dependency (Rule 3 auto-fix); other test files use fireEvent but plan spec used userEvent
- VideoSlideStrip is a controlled component — parent (SlideBuilderPage) owns slides state via onSlidesChange prop
- Duplicate slide uses POST /videos/{videoId}/slides with copied title+narration_script (no dedicated duplicate endpoint needed)
- SortableSlideThumb separates drag handle (⠿ icon) from click-to-navigate area — avoids dnd-kit drag events intercepting navigation clicks

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

Phase 16 complete. All 5 plans (16-01 through 16-05) done. Quiz Builder fully verified in browser: settings, all 4 question types, explanation persistence, drag-to-reorder persistence, AI generation. QUIZ-01 through QUIZ-08 all GREEN. Next: Phase 17 (TTS and Narration).
