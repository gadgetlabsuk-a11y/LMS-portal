# Project Research Summary

**Project:** LMS Platform — Vite+React Migration + AI Course Builder (v1.0)
**Domain:** AI-assisted e-learning authoring platform (creator-side)
**Researched:** 2026-05-08
**Confidence:** HIGH

---

## Executive Summary

This project adds a full AI-powered course authoring suite to an existing FastAPI/SQLite LMS. The existing platform has working JWT auth, basic course CRUD, a Claude-backed AI service, and a single-file React frontend (3420-line index.html with Babel standalone). The v1.0 milestone replaces that frontend with a proper Vite+React build and introduces a deeply integrated AI authoring experience: structured course creation wizards, a drag-drop slide canvas with layout presets, AI-generated slide outlines and narration scripts, TTS voiceover generation, AI quiz question generation, and a multi-step publish flow with validation. This is not a greenfield build — every architectural decision must preserve the working baseline.

The recommended approach is a 9-phase build ordered by hard dependencies: infrastructure first (Vite migration, database schema normalisation, core REST API), then UI scaffolding (course identity and structure wizards, course builder and module detail), then AI integration via SSE streaming, then the two most complex surfaces (slide canvas editor, quiz builder), and finally preview and publish. The stack is well-defined with high confidence: Vite 6 + React 18 + TypeScript, shadcn/ui + Tailwind, dnd-kit for list reordering, react-grid-layout for the slide canvas, TipTap v3 for rich text, Zustand + TanStack Query for state, and sse-starlette for backend streaming. The TTS provider (OpenAI TTS vs ElevenLabs) is the only unresolved stack decision and depends on whether an OpenAI API key already exists.

The key risks are all known and preventable. The most dangerous is the Vite/nginx subpath configuration — this repo already has five nginx-related emergency commits, confirming the path-prefix complexity is real. The second is the existing `Course.content` JSON blob: new relational tables must fully replace it in one migration, not coexist alongside it. The third is the slide canvas autosave race condition, where drag operations fire state changes faster than debounced saves can consume them, causing silent data loss on navigation. All three have clear prevention strategies and must be addressed in their respective phases before any dependent work begins.

---

## Key Findings

### Recommended Stack

The frontend build requires a clean Vite 6 project in `frontend/` with `base: '/lms/'` (for asset URL prefixing) and React Router v6 `basename="/lms"` (for route matching). These are distinct and differently formatted — a known source of deployment failures. The component library should be shadcn/ui (Tailwind-native, copy-into-repo model) rather than Mantine, which conflicts with the existing Tailwind setup. Drag-and-drop has two separate tools: dnd-kit for list reordering (modules, slides, quiz questions) and react-grid-layout for the slide canvas grid (snap-to-grid, resize handles, collision detection). These must not be mixed — react-grid-layout manages its own drag system.

The backend additions are minimal and conservative: extend existing routers rather than replace them, add sse-starlette for SSE streaming (fully compatible with FastAPI 0.104), upgrade document ingestion to PyMuPDF (6x faster than the spec's suggested pdfminer.six), and introduce Alembic for all schema migrations. The existing `claude_service.py` and `tts_service.py` are extended, not replaced.

**Core technologies:**
- Vite 6 + React 18.3 + TypeScript 5: build system and UI framework — already proven, correct version pinning matters
- shadcn/ui + Tailwind 3.4: component library — Tailwind-native, avoids CSS-in-JS conflicts
- dnd-kit/sortable: list drag-drop — 2.8M weekly downloads, replaces deprecated react-beautiful-dnd
- react-grid-layout 1.4: slide canvas grid — purpose-built snap-grid with resize handles, not a dnd-kit use case
- TipTap v3: rich text editor — ProseMirror-backed, active v3, avoids legacy Quill
- Zustand 5 + TanStack Query 5: state — Zustand for UI/editor state, TanStack Query for server state (keep separate)
- sse-starlette 2.x: backend SSE — EventSourceResponse for FastAPI, handles disconnect cleanly
- PyMuPDF (fitz) 1.26: PDF extraction — replaces current raw UTF-8 decode that produces garbage on complex PDFs
- Alembic: schema migrations — required; Coolify redeploys the container on every push

**Unresolved:** TTS provider. OpenAI TTS ($15/1M chars, lower friction if OpenAI key exists) vs ElevenLabs (better narration quality, separate billing). Design `NarrationService` as a swappable abstraction regardless.

### Expected Features

**Must have (table stakes) — all in v1:**
- Course identity form with AI description/objective generation (Modal 1A)
- Module/lesson hierarchy with drag-to-reorder at three levels
- Rich text editing for all description fields
- Autosave on every field change with explicit save indicators
- Draft/published state machine with clear status visibility
- Preview mode rendering draft as learner sees it
- Publish flow with pre-flight validation checklist
- Course thumbnail required before publish
- Quiz builder: MCQ single/multi, true/false, short answer
- Slide canvas with text, heading, image, video embed, code, quote block types
- Undo/redo in slide editor (spec explicitly requires this)

**Should have (competitive differentiators) — all in v1:**
- AI slide outline generation wizard (4-step: source → config → generate → commit)
- AI narration script generation per slide from visible content blocks
- AI TTS voiceover generation (bulk per video)
- AI quiz question generation from module content
- Document ingestion pipeline (PDF/DOCX to module/slide structure)
- Course structure wizard with live skeleton preview (Modal 1B)
- Snap-to-grid slide canvas with layout presets
- Version history on publish (learner progress preserved across updates)

**Defer to v1.1:**
- AI suggestions right rail (proactive completeness nudges)
- Drag-match and fill-blank question types
- Module unlock scheduling (scheduled_days variant)

**Defer to v2+:**
- SCORM/xAPI export, real-time co-editing, AI image generation, voice cloning, talking-head video type, multi-language, per-slide analytics, PowerPoint import

### Architecture Approach

The target architecture is an evolutionary extension of the existing monolith. New routers (modules.py, videos.py, slides.py, quizzes.py, questions.py, ai.py, uploads.py) are added alongside existing ones. The single most important architectural change is replacing the `Course.content` JSON blob with proper relational tables via Alembic migrations. A new `ai_service.py` acts as a unified dispatcher for all AI operations, wrapping `claude_service.py` with streaming support. All AI generation goes through one endpoint (`POST /api/ai/generate`) returning `text/event-stream`.

**Major components:**
1. Alembic migration pipeline — extends `courses` table, creates 8 new tables; runs on every Coolify deploy
2. `ai_service.py` + `routers/ai.py` — unified SSE streaming; prompt templates, model tier, rate limiting in one place
3. `features/creator/` (React) — 9 screen-level feature folders (CourseBuilder, ModuleDetail, VideoDetail, SlideBuilder, SlideEditor, QuizBuilder, ModuleOverview, PreviewMode, PublishFlow)
4. `hooks/useAutoSave` — debounced PATCH with flush-on-unmount; must handle drag canvas high-event-rate
5. `store/editorStore` (Zustand) — active slide, selected block, undo stack; separate from courseStore
6. `validation_service.py` — publish pre-flight logic; must be complete before publish flow is built

### Critical Pitfalls

1. **Vite base/React Router basename misconfigured** — `base: '/lms/'` in vite.config.ts (trailing slash required), `basename="/lms"` in BrowserRouter (no trailing slash). Verify in Coolify staging before any other frontend work. 5 nginx emergency commits in this repo confirm this hazard is established.

2. **Course.content JSON coexisting with relational tables** — migrate all existing course data to relational tables in one Alembic script and retire the column. Two-code-path handling is not acceptable.

3. **order_index drift under concurrent reorder** — reorder is a single transaction updating all siblings atomically. Never update individual order_index values via PATCH. Debounce the reorder API call.

4. **SSE generator runs after client disconnect** — check `await request.is_disconnected()` at every yield. Omitting this burns Claude API tokens silently.

5. **Slide canvas autosave race condition** — flush pending saves on route change in useEffect cleanup. Write block positions to server only on onDragEnd, not during drag.

6. **TTS bulk generation storms** — use asyncio.Semaphore(3). Cache by narration_script_hash. `eleven_monolingual_v1` in current tts_service.py is deprecated; use `eleven_turbo_v2_5`.

7. **PDF extraction producing garbage** — replace raw UTF-8 byte decode in document_service.py with PyMuPDF. Test with a real scanned PDF before connecting to AI generation.

---

## Implications for Roadmap

### Phase 1: Vite Migration
**Rationale:** Every subsequent frontend phase lands in the new Vite codebase. Must complete and verify in Coolify staging first. The /lms subpath and nginx SPA fallback are confirmed hazards in this specific repo.
**Delivers:** Identical behaviour to v0.1 frontend, built with Vite, deployed via nixpacks staticfile.
**Avoids:** Pitfalls 1 (base/basename mismatch), 2 (nginx SPA fallback), 3 (auth regression during migration).

### Phase 2: Database Schema Migration
**Rationale:** Relational schema must be live in production before any new API endpoints are written. Course.content JSON must be retired in one clean migration.
**Delivers:** 8 new relational tables, extended courses table, Alembic configured and running on Coolify deploys.
**Avoids:** Pitfalls 4 (Course.content divergence), 5 (order_index corruption), 10 (learner progress versioning).

### Phase 3: Core CRUD API
**Rationale:** Frontend cannot build creator screens until backend endpoints exist and are testable. Can begin immediately after Phase 2.
**Delivers:** All new routers with auth guards, testable via /docs.
**Research flag:** Standard REST CRUD — skip deep research.

### Phase 4: Course Identity UI (Modals 1A + 1B)
**Rationale:** Course Identity captures AI tone preset and learning objectives that propagate into every downstream AI call. Nothing meaningful can be generated without this context.
**Delivers:** CourseIdentityModal, CourseStructureModal with live skeleton preview, navigation to CourseBuilder.
**Addresses:** Table stakes course identity form + live skeleton preview differentiator.

### Phase 5: Course Builder + Module Detail
**Rationale:** CourseBuilder is the home base creators return to between all deeper edits. Module Detail must exist before Video Detail or Quiz Builder.
**Delivers:** Left-rail tree, module card list with drag-to-reorder, Module Detail with rich text.
**Uses:** dnd-kit/sortable for module reordering, TipTap for rich text.

### Phase 6: AI Integration (SSE Streaming)
**Rationale:** Requires course and module records to exist. All later AI features (slide outline, quiz generation) reuse the same infrastructure built here.
**Delivers:** ai_service.py dispatcher, stream_generate() on claude_service.py, POST /api/ai/generate SSE endpoint, useSSE hook, StreamingTextOutput component, SideDrawer pattern.
**Avoids:** Pitfall 6 (SSE orphaned generators — disconnect detection must be in initial implementation).
**Research flag:** SSE + Anthropic SDK streaming interaction is moderately complex — recommend research-phase.

### Phase 7: Slide Builder + Slide Editor
**Rationale:** Highest-complexity phase. The 12-column snap-grid canvas, block drag-to-place, undo/redo, and autosave flush pattern all converge here. Must follow Phase 6 (slide outline generation is the primary way slides get populated).
**Delivers:** VideoDetail with slide outline wizard, SlideBuilder thumbnail strip, SlideEditor canvas with full block library, narration tab, autosave with flush-on-navigate.
**Uses:** react-grid-layout for canvas (not dnd-kit), dnd-kit for slide strip, Zustand editorStore for undo stack.
**Avoids:** Pitfall 9 (autosave race — flush on unmount from day one).
**Research flag:** react-grid-layout API depth + undo/redo state design — recommend research-phase. This is the highest-risk phase.

### Phase 8: Quiz Builder
**Rationale:** AI question generation reads slide blocks — Phase 7 must complete for useful output. Reuses Phase 6 AI infrastructure entirely.
**Delivers:** QuizBuilder with MCQ/true-false/short-answer, AI question generation from module content.
**Research flag:** Standard patterns — skip deep research.

### Phase 9: TTS + Preview Mode + Publish Flow
**Rationale:** TTS requires narration scripts (Phase 7). Preview and publish require all content types. This is the final gate before v1 ships.
**Delivers:** TTS generation with semaphore rate limiting and script-hash caching, PreviewMode with draft watermark, PublishFlow with pre-flight checklist, version bump logic.
**Avoids:** Pitfall 7 (TTS storm — semaphore and caching must be in initial implementation).
**Research flag:** TTS provider decision must be made before this phase. Confirm ElevenLabs model name (`eleven_turbo_v2_5`) before use.

### Phase Ordering Rationale

- Phases 1-3 are infrastructure-only; Phase 2 and 3 can partially overlap once Phase 1 deploys to staging.
- Phase 4 precedes Phase 5 because course identity fields (tone preset, objectives) are consumed by all subsequent AI generation.
- Phase 6 (AI) follows Phases 4-5 because the AI drawer needs course/module records to attach results to.
- Phase 7 (Slide Editor) is isolated as its own phase because its complexity warrants focused delivery before Phase 8 attempts to consume slide content.
- Phase 9 is last because TTS, preview, and publish all depend on content from all prior phases being complete.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 6 (AI/SSE):** Anthropic SDK streaming integration, request.is_disconnected() pattern, rate limiting via ai_prompt_log — moderately complex integration with project-specific constraints.
- **Phase 7 (Slide Editor):** react-grid-layout API depth, undo/redo state design with Zustand, autosave flush pattern — highest-risk phase in the project.

Phases with standard patterns (skip research-phase):
- **Phases 1, 3, 4, 5, 8:** Well-documented patterns with high-confidence library choices.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All package versions confirmed via npm/PyPI. TTS provider is the only open decision. |
| Features | HIGH | Spec-aligned findings are definitive. Competitor analysis is MEDIUM (third-party sources). |
| Architecture | HIGH | Based on direct codebase inspection. Existing patterns clearly identified. |
| Pitfalls | HIGH | 7 of 10 pitfalls grounded in existing code inspection or git history, not speculation. |

**Overall confidence: HIGH**

### Gaps to Address

- **TTS provider (OpenAI vs ElevenLabs):** Resolve before Phase 9. Confirm whether an OpenAI API key already exists — this is the deciding factor. Build `NarrationService` as a swappable abstraction regardless.
- **Traefik stripprefix exact behaviour:** STACK.md and PITFALLS.md have a minor tension on whether `base: '/lms/'` or `base: '/'` is correct. Resolve by checking the Traefik config in Coolify before the first Vite deploy.
- **SQLite vs PostgreSQL for v1 production:** Concurrent writes (AI streaming + autosave + TTS) will cause write lock contention. If more than one creator will author simultaneously at launch, migrate to PostgreSQL before Phase 6.
- **ElevenLabs model deprecation:** Current tts_service.py uses `eleven_monolingual_v1` (deprecated). Update to `eleven_turbo_v2_5` before any TTS work regardless of provider decision.

---

## Sources

### Primary (HIGH confidence)
- `LMS platform/AI_COURSE_BUILDER_SPEC.md` — full feature spec, all acceptance criteria
- `LMS Platform/.planning/PROJECT.md` — project constraints and out-of-scope decisions
- Existing codebase (`backend/services/`, `frontend/index.html`, git history) — pitfall findings
- [Vite Shared Options — base config](https://vite.dev/config/shared-options) — base behaviour confirmed
- [sse-starlette PyPI](https://pypi.org/project/sse-starlette/) — v2.x, FastAPI 0.104 compatibility
- [Zustand npm](https://www.npmjs.com/package/zustand) — v5.0.13
- [@tiptap/react npm](https://www.npmjs.com/package/@tiptap/react) — v3.22.5, React 18 compatible
- [@dnd-kit/sortable npm](https://www.npmjs.com/package/@dnd-kit/sortable) — v10.0.0
- [OpenAI TTS pricing](https://openai.com/api/pricing/) — $15/1M chars confirmed

### Secondary (MEDIUM confidence)
- [dnd-kit vs pragmatic DnD comparison 2026](https://www.pkgpulse.com/blog/dnd-kit-vs-react-beautiful-dnd-vs-pragmatic-drag-drop-2026) — library selection
- [shadcn/ui vs Mantine comparison 2025](https://makersden.io/blog/react-ui-libs-2025-comparing-shadcn-radix-mantine-mui-chakra) — component library decision
- [TanStack Query vs SWR 2025](https://refine.dev/blog/react-query-vs-tanstack-query-vs-swr-2025/) — state management
- [ElevenLabs vs OpenAI TTS comparison](https://vapi.ai/blog/elevenlabs-vs-openai) — quality claims (third-party benchmark)
- [PyMuPDF vs pdfminer benchmark](https://github.com/py-pdf/benchmarks) — 6x speed claim
- [Coolify nixpacks SPA issues](https://github.com/coollabsio/coolify/discussions/5763) — nginx SPA fallback pitfall
- [FastAPI SSE disconnect](https://github.com/fastapi/fastapi/discussions/7572) — orphaned generator pitfall
- [ElevenLabs models](https://elevenlabs.io/docs/overview/models) — eleven_monolingual_v1 deprecation confirmed

---
*Research completed: 2026-05-08*
*Ready for roadmap: yes*
