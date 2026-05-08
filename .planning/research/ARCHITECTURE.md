# Architecture Research

**Domain:** AI-assisted LMS course builder (FastAPI + Vite/React)
**Researched:** 2026-05-08
**Confidence:** HIGH — based on direct inspection of existing codebase

---

## Current Architecture (v0.1 baseline)

```
Coolify / Traefik
    │  (path-prefix /lms, stripprefix before hitting container)
    ▼
nginx (nixpacks staticfile provider)
    │  serves frontend/dist/* as static files
    │  try_files $uri $uri/ /index.html  (SPA deep-link routing)
    │
    ├── /* (static assets)  ──▶  frontend/dist/
    │
    └── /api/* (proxied to FastAPI on port 8000)
              │
        FastAPI (main.py)
              │
        ┌─────┴──────────────────────────┐
        │  Existing Routers              │
        │  /api/auth        auth.py      │
        │  /api/users       users.py     │
        │  /api/courses     courses.py   │
        │  /api/admin       admin.py     │
        │  /api/creator     creator.py   │
        │  /api/learn       learn.py     │
        │  /api/security    security.py  │
        │  /api/whitelabel  whitelabel.py│
        └─────┬──────────────────────────┘
              │
        Services layer
        claude_service.py  (Claude API, non-streaming)
        document_service.py (PDF/DOCX text extraction)
        tts_service.py      (ElevenLabs, existing)
        slide_service.py    (PPTX export)
        script_service.py   (DOCX export)
        player_service.py   (HTML player render)
              │
        SQLAlchemy ORM
              │
        SQLite (dev) / PostgreSQL (prod)
        Tables: users, sessions, courses, enrollments,
                audit_logs, error_logs, api_usage,
                feature_flags, whitelabel_config,
                login_attempts, ip_allowlist
```

**Key current constraint:** `Course.content` is a single JSON blob containing the entire course structure. Module/Video/Slide data has no normalised DB representation — everything lives in that blob. The new spec requires proper relational tables for all of these.

---

## Target Architecture (v1.0)

```
Coolify / Traefik
    │  (same /lms stripprefix — no change)
    ▼
nginx (same nixpacks staticfile provider — no change)
    │
    ├── /* static assets    ──▶  frontend/dist/  (Vite build output)
    │
    └── /api/* proxied to FastAPI :8000
              │
        FastAPI (main.py — minimally changed)
              │
        ┌─────┴────────────────────────────────────────┐
        │  Existing Routers (unchanged)                │
        │  /api/auth  /api/users  /api/admin           │
        │  /api/creator  /api/learn  /api/security     │
        │  /api/whitelabel                             │
        ├──────────────────────────────────────────────┤
        │  Modified Routers                            │
        │  /api/courses   (extend, keep existing)      │
        ├──────────────────────────────────────────────┤
        │  NEW Routers                                 │
        │  /api/modules   modules.py                   │
        │  /api/videos    videos.py                    │
        │  /api/slides    slides.py                    │
        │  /api/quizzes   quizzes.py                   │
        │  /api/questions questions.py                 │
        │  /api/resources resources.py                 │
        │  /api/ai        ai.py  (SSE streaming)       │
        │  /api/uploads   uploads.py                   │
        └─────┬────────────────────────────────────────┘
              │
        Services layer
        ┌──────────────────────────────────────────────┐
        │  KEEP (extend as needed)                     │
        │  claude_service.py  → add streaming + ops    │
        │  document_service.py → add URL + txt/md      │
        │  tts_service.py     → attach to Slide model  │
        ├──────────────────────────────────────────────┤
        │  NEW services                                │
        │  ai_service.py   (unified AI ops dispatcher) │
        │  upload_service.py (file storage + URLs)     │
        │  validation_service.py (publish pre-flight)  │
        └─────┬────────────────────────────────────────┘
              │
        SQLAlchemy ORM + Alembic migrations
              │
        Extended schema (see Data Model section)
```

**Frontend: Vite + React**
```
frontend/
├── index.html           (Vite entry, sets base="/lms/")
├── vite.config.ts       (base: "/lms/", outDir: "dist")
├── src/
│   ├── main.tsx         (ReactDOM.createRoot)
│   ├── App.tsx          (React Router v6, basename="/lms")
│   ├── api/             (Axios/fetch wrappers per resource)
│   │   ├── courses.ts
│   │   ├── modules.ts
│   │   ├── slides.ts
│   │   └── ai.ts        (SSE client)
│   ├── components/      (shared/design system)
│   │   ├── ui/          (primitives: Button, Input, Modal)
│   │   └── shared/      (RichTextEditor, DragDropZone, etc.)
│   ├── features/        (screen-level feature modules)
│   │   ├── auth/
│   │   ├── admin/
│   │   ├── learn/
│   │   └── creator/     (ALL new course builder screens)
│   │       ├── CourseBuilder/
│   │       ├── ModuleDetail/
│   │       ├── VideoDetail/
│   │       ├── SlideBuilder/
│   │       ├── SlideEditor/
│   │       ├── QuizBuilder/
│   │       ├── ModuleOverview/
│   │       ├── PreviewMode/
│   │       └── PublishFlow/
│   ├── hooks/           (useAutoSave, useSSE, useDragDrop)
│   └── store/           (Zustand slices per resource)
└── dist/                (Vite build output, nginx serves this)
```

---

## Data Model Changes

### What exists (keep, do not drop)
- `users`, `sessions`, `enrollments`, `audit_logs`, `error_logs`, `api_usage`, `feature_flags`, `whitelabel_config`, `login_attempts`, `ip_allowlist` — no changes needed.
- `courses` table — keep but **extend** with new columns. Do not drop `content` (JSON) until migration is complete. Retire it once all courses are migrated to normalised structure.

### Course table extension (Alembic migration)
Add columns to `courses`:
- `slug` (String, unique, nullable initially)
- `summary` (Text, nullable)
- `thumbnail_url` (String, nullable)
- `audience_level` (Enum: beginner/intermediate/advanced, nullable)
- `learning_objectives` (JSON array, nullable)
- `category` (String, nullable)
- `tags` (JSON array, nullable)
- `estimated_duration_minutes` (Integer, nullable)
- `ai_tone_preset` (String, nullable)
- `ai_custom_prompt` (Text, nullable)
- `navigation_mode` (Enum: sequential/free, default sequential)
- `default_pass_rate` (Integer, default 80)
- `default_quiz_attempts` (Integer, default 3)
- `default_quiz_time_limit_seconds` (Integer, nullable)
- `certificate_enabled` (Boolean, default True)
- `published_at` (DateTime, nullable)
- `version` (Integer, default 1)
- `status` already exists (extend enum to add `has_unpublished_changes`)

### New tables (new Alembic migration)
- `modules` — id, course_id (FK courses), order_index, title, description, learning_objectives (JSON), estimated_duration_minutes, pass_rate_override, unlock_rule, unlock_days_after_enrolment, status
- `videos` — id, module_id (FK modules), order_index, title, description, video_type, estimated_duration_seconds, narration_voice_id, source_video_url, status
- `slides` — id, video_id (FK videos), order_index, layout_id, duration_seconds, narration_script, narration_audio_url, transition, status
- `blocks` — id, slide_id (FK slides), order_index, type, content (JSON), style (JSON), alt_text, grid_position (JSON: x,y,width,height)
- `quizzes` — id, module_id (FK modules, nullable), video_id (FK videos, nullable), order_index, title, description, quiz_type, pass_rate, attempts_allowed, time_limit_seconds, shuffle_questions, show_feedback, on_fail_action, status
- `questions` — id, quiz_id (FK quizzes), order_index, type, prompt, points, explanation, options (JSON), correct_answer (JSON), linked_objective_id, difficulty
- `resources` — id, module_id (FK modules), type, title, url_or_file, visible_to_learner
- `ai_prompt_log` — id, creator_id (FK users), operation, inputs (JSON), output (Text), model_tier, tokens_used, created_at (for rate limiting + debugging)

---

## Component Boundaries and Responsibilities

| Component | Responsibility | Notes |
|-----------|----------------|-------|
| `routers/courses.py` | Course identity CRUD, publish, archive, preview token | Extend existing file |
| `routers/modules.py` | Module CRUD, reorder | New file |
| `routers/videos.py` | Video CRUD | New file |
| `routers/slides.py` | Slide CRUD, bulk reorder | New file |
| `routers/quizzes.py` | Quiz + Question CRUD | New file |
| `routers/ai.py` | Unified AI endpoint, SSE streaming | New file — most complex |
| `routers/uploads.py` | Document, image, video, thumbnail upload | New file |
| `services/ai_service.py` | Dispatches to Claude per operation, handles chunking, streaming | New — wraps claude_service |
| `services/claude_service.py` | Low-level Claude API calls | Extend with `stream_generate()` |
| `services/upload_service.py` | File storage, path management, cleanup | New |
| `services/validation_service.py` | Publish pre-flight checklist evaluation | New |
| `features/creator/*` (React) | All creator authoring screens | New — largest frontend work |
| `components/shared/*` (React) | Design system components per spec section 8 | New |
| `hooks/useAutoSave` | Debounced PATCH on every field change | New |
| `hooks/useSSE` | EventSource wrapper for AI streaming | New |
| `store/courseStore` | Zustand: course + module + video tree state | New |
| `store/editorStore` | Zustand: active slide, selected block, undo stack | New |

---

## Data Flows

### 1. Course Creation (Modal 1A → 1B → Builder)

```
Creator fills Modal 1A
  → POST /api/courses  (creates Course row, status=draft)
  → Returns course_id

Creator fills Modal 1B
  → POST /api/courses/:id/scaffold
      body: { module_count, videos_per_module, quizzes_per_module, ... }
      Server creates Module[], Video[], Quiz[] rows in one transaction
  → Frontend receives full course tree
  → Navigate to CourseBuilder with course_id
```

### 2. AI Generation with SSE Streaming

```
Creator clicks "Generate description"
  → POST /api/ai/generate
      body: { operation: "generate_description", inputs: {...}, course_id }
      Server: ai_service.dispatch(operation, inputs)
              → calls claude_service.stream_generate(prompt)
              → returns StreamingResponse (text/event-stream)
  → Frontend: EventSource on response URL
              → tokens arrive as SSE events
              → StreamingTextOutput component renders incrementally
  → Creator accepts: PATCH /api/courses/:id  { description: "..." }
  → Creator rejects: discard, no PATCH sent
```

### 3. Slide Editor Autosave

```
Creator drags block onto canvas
  → editorStore updates local state immediately (optimistic)
  → useAutoSave hook: debounce 800ms
  → PATCH /api/slides/:id  { blocks: [...] }
  → Server updates Slide.blocks, Slide.status auto-recalculated
  → Save indicator: "Saved" / "Saving..." / "Error"
```

### 4. Document Ingestion Pipeline

```
Creator uploads PDF to AI drawer
  → POST /api/uploads/document  (multipart)
      → upload_service saves to /uploads/docs/temp_{uuid}.pdf
      → document_service.extract_text() → raw text
      → Returns { doc_id, char_count }
  → POST /api/ai/generate
      body: { operation: "generate_module_desc", inputs: { doc_id, course_id }, ... }
      → ai_service loads temp text, chunks if needed, calls Claude stream
      → upload_service.cleanup(doc_id) after stream completes
```

### 5. TTS Narration Generation

```
Creator clicks "Generate narration" on Slide Editor
  → POST /api/slides/:id/generate-narration
      → tts_service.generate(slide.narration_script, voice_id)
      → Saves audio to /uploads/audio/slide_{id}.mp3
      → Updates Slide.narration_audio_url
  → Frontend: audio element src updated, preview plays
```

### 6. Publish Flow

```
Creator clicks "Publish"
  → GET /api/courses/:id/preflight
      → validation_service.check(course_id)
      → Returns { items: [{ rule_id, scope, status, fix_url }] }
  → Frontend renders ChecklistRow components
  → If all blocks pass: POST /api/courses/:id/publish
      → Sets Course.status = "published", Course.published_at, Course.version++
      → If version > 1: prior published content frozen, working copy becomes new version
```

---

## API Endpoints: New vs Modified

### Modified (extend existing)
| Endpoint | Change |
|----------|--------|
| `POST /api/courses` | Add new identity fields to CourseCreate schema |
| `PATCH /api/courses/:id` | Add new fields, handle state machine transitions |
| `GET /api/courses/:id` | Include nested module tree (lazy-loadable) |

### New endpoints
| Endpoint | Purpose |
|----------|---------|
| `POST /api/courses/:id/scaffold` | Build skeleton from 1B inputs (creates all Module/Video/Quiz rows) |
| `POST /api/courses/:id/publish` | State machine: draft→published, published→has_unpublished_changes |
| `POST /api/courses/:id/archive` | Archive a course |
| `GET /api/courses/:id/preflight` | Publish pre-flight validation |
| `POST /api/courses/:id/preview-token` | Issue short-lived token for preview mode |
| `POST /api/modules` | Create module |
| `PATCH /api/modules/:id` | Update module |
| `DELETE /api/modules/:id` | Delete module |
| `POST /api/modules/:id/reorder` | Reorder children (videos + quizzes) |
| `POST /api/modules/:id/videos` | Create video |
| `PATCH /api/videos/:id` | Update video |
| `DELETE /api/videos/:id` | Delete video |
| `POST /api/videos/:id/slides` | Create slide |
| `PATCH /api/slides/:id` | Update slide (blocks, narration, settings) |
| `DELETE /api/slides/:id` | Delete slide |
| `POST /api/slides/reorder` | Bulk reorder slides |
| `POST /api/slides/:id/generate-narration` | TTS for one slide |
| `POST /api/videos/:id/generate-narration-all` | TTS for all slides in video |
| `POST /api/modules/:id/quizzes` | Create quiz |
| `PATCH /api/quizzes/:id` | Update quiz settings |
| `DELETE /api/quizzes/:id` | Delete quiz |
| `POST /api/quizzes/:id/questions` | Add question |
| `PATCH /api/questions/:id` | Update question |
| `DELETE /api/questions/:id` | Delete question |
| `POST /api/ai/generate` | Unified AI: streams via SSE |
| `POST /api/uploads/document` | Upload doc for ingestion |
| `POST /api/uploads/image` | Upload slide image |
| `POST /api/uploads/video` | Upload video file |
| `POST /api/uploads/thumbnail` | Upload course thumbnail |

---

## Architectural Patterns

### Pattern 1: Unified AI Endpoint with SSE

**What:** All AI operations go through one endpoint `POST /api/ai/generate`. The request body carries `operation` (string enum) and `inputs` (dict). The response is `text/event-stream`. The frontend uses a single `useSSE` hook regardless of which AI operation is running.

**Why:** Avoids proliferating 10 different streaming endpoints. Prompt templates, model tier selection, rate limiting, and logging live in one place (`ai_service.py`). The spec section 5 explicitly calls for this pattern.

**SSE event protocol:**
```
event: token
data: {"text": "Here is your "}

event: token
data: {"text": "course description..."}

event: done
data: {"total_tokens": 142, "operation": "generate_description"}

event: error
data: {"message": "Rate limit exceeded"}
```

**FastAPI implementation:** use `StreamingResponse` with `media_type="text/event-stream"` and an `async_generator` that yields formatted SSE lines. Do NOT use `asyncio.sleep(0)` polling — use `async for chunk in anthropic_stream`.

### Pattern 2: Optimistic UI with Debounced Autosave

**What:** Every field change updates Zustand store immediately (no loading state). A debounced hook (800ms) fires the PATCH. If PATCH fails, store rolls back and shows an error.

**Why:** The spec requires "save by default, save on every field change." A round-trip on every keystroke is too slow. Optimistic updates keep the editor feeling instant.

**Zustand store slice pattern:**
```typescript
// editorStore.ts
const useEditorStore = create<EditorState>((set, get) => ({
  slide: null,
  isDirty: false,
  lastSaved: null,
  updateBlock: (blockId, patch) => {
    set(s => ({ slide: applyBlockPatch(s.slide, blockId, patch), isDirty: true }))
  },
  markSaved: () => set({ isDirty: false, lastSaved: new Date() }),
}))
```

### Pattern 3: Feature-Folder React Structure

**What:** Each major screen is a folder under `features/creator/` containing the screen component, its local hooks, and its sub-components. Shared primitives go in `components/`.

**Why:** The single-file anti-pattern is exactly what caused the current 3420-line index.html problem. Feature folders keep screen-specific code co-located without polluting the shared component tree.

**Rule:** A component in `features/creator/SlideEditor/` is never imported by `features/creator/QuizBuilder/`. Cross-feature sharing goes through `components/shared/`.

### Pattern 4: Alembic for All Schema Changes

**What:** Every schema change — including adding columns to `courses`, creating new tables, adding indexes — is an Alembic migration script. No manual `CREATE TABLE` or `ALTER TABLE` in production.

**Why:** Coolify redeploys the container on push. Without Alembic, schema changes require manual SSH intervention or data loss.

**Migration sequence:**
1. `alembic init alembic` (first time setup)
2. One migration: extend `courses` table columns
3. Second migration: create all new tables (modules, videos, slides, blocks, quizzes, questions, resources, ai_prompt_log)
4. Run both on deploy via `alembic upgrade head` in Coolify start command

---

## Recommended Build Order

The order is driven by hard dependencies: the frontend cannot build course builder screens until the backend endpoints exist, and the backend cannot serve normalised data until the DB schema is migrated.

### Phase 1 — Vite Migration (no new features)
**Goal:** Replace single-file frontend with Vite build, identical behaviour to v0.1.

1. Init Vite project in `frontend/src/`, configure `base: "/lms/"` and `outDir: "dist"`.
2. Port existing React components from `index.html` into feature folders.
3. Configure React Router v6 with `basename="/lms"`.
4. Verify Coolify nixpacks staticfile provider still picks up `frontend/dist/`.
5. Verify nginx `try_files` SPA routing still works for deep links.
6. Remove Babel standalone, old index.html (keep as backup until smoke tested in prod).

**Dependency note:** This phase must complete before any new UI work begins. All new creator features land in the new Vite codebase.

### Phase 2 — Backend Schema Migration
**Goal:** Normalised DB schema live in production, existing courses unbroken.

1. Add Alembic to `backend/`, configure to point at same DB URL from `config.py`.
2. Migration 1: extend `courses` table (nullable columns only — safe, no data loss).
3. Migration 2: create new tables (modules, videos, slides, blocks, quizzes, questions, resources, ai_prompt_log).
4. Update Coolify start command: `alembic upgrade head && uvicorn main:app ...`.
5. No frontend changes in this phase — existing UI continues to work.

### Phase 3 — Core CRUD API
**Goal:** All new REST endpoints exist and are testable via OpenAPI docs.

1. New routers: `modules.py`, `videos.py`, `slides.py`, `quizzes.py`, `questions.py`, `resources.py`.
2. New endpoints on `courses.py`: scaffold, publish, archive, preflight, preview-token.
3. New `uploads.py` router (document, image, video, thumbnail).
4. Register new routers in `main.py`.
5. Basic auth guards (require_creator) on all new routes.

**Dependency note:** Phase 3 can begin as soon as Phase 2 is deployed. No frontend dependency.

### Phase 4 — Course Identity UI (Modal 1A + 1B)
**Goal:** Creator can create a course with structured identity fields and generate a skeleton.

1. CourseIdentityModal (Modal 1A) with all fields, slug auto-generation.
2. CourseStructureModal (Modal 1B) with live skeleton preview tree.
3. Calls: `POST /api/courses`, `POST /api/courses/:id/scaffold`.
4. Navigate to CourseBuilder on success.

### Phase 5 — Course Builder + Module Detail
**Goal:** Creator can see and manage the course tree, open module detail.

1. CourseBuilder: left rail tree, module card list, inline editing, drag-to-reorder modules.
2. ModuleDetail: identity fields, video/quiz list, reorder content toggle.
3. Calls: `PATCH /api/courses/:id`, `PATCH /api/modules/:id`, `POST /api/modules/:id/reorder`.

### Phase 6 — AI Integration (SSE)
**Goal:** AI generation works across Course Identity, Module Detail, Video Detail.

1. `ai_service.py`: dispatcher, model tier map, rate limit tracking via `ai_prompt_log`.
2. Extend `claude_service.py` with `stream_generate()` using Anthropic async streaming.
3. `routers/ai.py`: `POST /api/ai/generate` → SSE StreamingResponse.
4. Frontend: `useSSE` hook, `StreamingTextOutput` component, `SideDrawer` with AI tabs.
5. Wire "Generate description" on CourseIdentityModal, ModuleDetail, VideoDetail.

**Dependency note:** AI integration depends on Phase 4+5 (course + module records must exist before AI generate calls can reference them).

### Phase 7 — Slide Builder + Slide Editor
**Goal:** Creator can generate a slide outline, manage the slide deck, and edit individual slides.

1. VideoDetail: type selector, slide outline generation wizard (source → config → generate → commit).
2. SlideBuilder: horizontal thumbnail strip, drag reorder, bulk actions.
3. SlideEditor: canvas grid, block library (drag-to-place), right panel tabs, block resize/move.
4. Narration tab: `POST /api/slides/:id/generate-narration`, audio preview.
5. Autosave hook: debounced PATCH on block changes.

**This is the most complex phase.** `CanvasGrid` with 12-column snap, drag-to-place blocks, and undo/redo represents the bulk of frontend complexity. Expect this phase to take 2-3x the effort of earlier phases.

### Phase 8 — Quiz Builder
**Goal:** Creator can build quiz question sets with AI assistance.

1. QuizBuilder: settings header, question list, add question with type selector.
2. Question editor modal: per-type answer schema (MCQ options, fill blank, etc.).
3. AI generate questions from module content.
4. Wire quiz into ModuleOverview unified content list.

### Phase 9 — Preview Mode + Publish Flow
**Goal:** Creator can preview course as learner and publish.

1. PreviewMode: renders learner-facing UI with draft data + watermark.
2. PublishFlow: `GET /api/courses/:id/preflight` → ChecklistRow components.
3. `POST /api/courses/:id/publish` with version bump logic.
4. Post-publish confirmation screen.

---

## Deployment Constraints (Coolify / nginx)

These constraints are fixed by the existing infrastructure and must not be violated by new code.

| Constraint | Detail | Impact |
|------------|--------|--------|
| Traefik strips `/lms` prefix | All requests arrive at the container without `/lms` | Vite `base: "/lms/"` handles asset paths; React Router `basename="/lms"` handles routes |
| nginx serves `frontend/dist/` as static files | nixpacks staticfile provider reads `frontend/Staticfile` | Vite `outDir` must be `frontend/dist/`. Do not change this path. |
| `try_files $uri $uri/ /index.html` in nginx | SPA deep-link routing works (patched in recent commits) | React Router must handle all non-API routes client-side |
| FastAPI at port 8000 | nginx proxies `/api/*` to FastAPI | All new endpoints must be under `/api/` prefix |
| No WebSocket support confirmed | Traefik config unknown — SSE is safer | Use SSE (text/event-stream) for streaming, not WebSocket |
| Single container | Frontend static files served by nginx; FastAPI is separate process | Coolify Procfile or supervisor runs both; check existing start.sh |
| `/uploads/` directory | FastAPI mounts `StaticFiles(directory="uploads")` at `/uploads` | Upload service must write to `backend/uploads/` subdirectories |

---

## Anti-Patterns

### Anti-Pattern 1: Storing course structure in the JSON blob

**What people do:** Continue using `Course.content` JSON to store modules, slides, and blocks.
**Why it's wrong:** Cannot do relational queries (e.g. "all slides without narration"), cannot enforce foreign key integrity, cannot do Alembic migrations on nested structure, makes AI context assembly expensive (must deserialise entire blob).
**Do this instead:** Normalise to proper tables per Phase 2. The `content` column should be retired once all courses use the new structure. Keep it nullable for backward compatibility during transition.

### Anti-Pattern 2: Blocking sync route handlers for AI generation

**What people do:** `def generate(...)` (sync) calling `claude_service.generate_course(...)` with `asyncio.run()` inside.
**Why it's wrong:** FastAPI dispatches sync handlers via `run_in_executor` which uses the thread pool. Claude API calls block threads for 5-30 seconds. With the current 20-worker pool, 20 concurrent generation requests exhaust the pool entirely.
**Do this instead:** All AI endpoints must be `async def`. The SSE streaming pattern (Phase 6) eliminates this by definition, since `StreamingResponse` requires an async generator.

### Anti-Pattern 3: Embedding the /lms prefix in API call URLs

**What people do:** `fetch("/lms/api/courses")` — hardcoding the path prefix in frontend code.
**Why it's wrong:** Traefik strips `/lms` before requests reach FastAPI. The correct backend URL is `/api/courses`. The `/lms` prefix is only for frontend assets and SPA routes.
**Do this instead:** All API calls use `/api/...`. Create a single `api/client.ts` with a configured axios instance. Never reference `/lms` in API call paths.

### Anti-Pattern 4: Spinning up ClaudeService per request

**What people do:** `claude_service = ClaudeService()` inside every route handler (current pattern in courses.py).
**Why it's wrong:** Fine for now, but instantiation overhead adds up. More importantly, per-request instances make rate limiting and token counting across requests impossible.
**Do this instead:** Make `ai_service.py` a module-level singleton (or use FastAPI dependency injection). Rate limit tracking in `ai_prompt_log` requires a shared context.

---

## Integration Points: New vs Existing

| Integration | Type | Notes |
|-------------|------|-------|
| `claude_service.py` → `ai_service.py` | Extend | `ai_service` wraps `claude_service`. Add `stream_generate(prompt) -> AsyncGenerator` to `claude_service`. |
| `tts_service.py` | Reuse | Existing ElevenLabs integration. Wire to `POST /api/slides/:id/generate-narration` instead of to `course.content` blob. |
| `document_service.py` | Extend | Add support for plain `.txt` and `.md` files (currently only PDF/DOCX/PPTX). Add URL fetch+readability path. |
| `courses.py` router | Modify | Add scaffold, publish, preflight, preview-token endpoints. Keep all existing endpoints. |
| `creator.py` router | Extend | Existing stats/learners endpoints unchanged. May add course tree endpoint for dashboard. |
| Auth middleware (`require_creator`) | Reuse | All new creator endpoints use same guard. No changes to auth. |
| Uploads directory | Extend | Existing `/uploads/videos/` subdirectory pattern. Add `/uploads/docs/`, `/uploads/images/`, `/uploads/audio/`, `/uploads/thumbnails/`. |
| Alembic | New | No Alembic setup currently exists. First-time setup required. Configure `env.py` to import `Base` from `models`. |

---

## Scaling Considerations

This is a single-tenant LMS (one organisation). Scale targets are modest.

| Scale | Architecture Notes |
|-------|-------------------|
| Current (1-50 concurrent creators) | Monolith is correct. 20-thread pool is adequate. SQLite acceptable for dev, PostgreSQL for prod. |
| 50-500 concurrent creators | SSE streaming may saturate thread pool. Move AI endpoint to async worker (Celery + Redis or FastAPI BackgroundTasks). |
| 500+ | Split AI service to separate FastAPI instance. Add CDN for uploaded assets. Consider S3 for file storage. |

**First bottleneck will be AI streaming.** Each SSE connection holds open an HTTP connection for 5-30 seconds. At 50 concurrent generation requests, nginx keep-alive and FastAPI thread pool need tuning. This is unlikely to be a problem at current scale, but Phase 6 should include a simple concurrency test.

---

*Architecture research for: LMS Platform — Vite+React migration + AI Course Builder*
*Researched: 2026-05-08*
