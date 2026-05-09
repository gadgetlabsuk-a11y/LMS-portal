# Roadmap: LMS Platform

## Milestones

- ✅ **v0.1 LMS Foundation** - Phases 1–8 (shipped 2026-05-08)
- 🚧 **v1.0 AI Course Builder** - Phases 9–18 (in progress)

## Phases

<details>
<summary>✅ v0.1 LMS Foundation (Phases 1–8) — SHIPPED 2026-05-08</summary>

Phases 1–8 were tracked manually before GSD was adopted. What shipped:
- FastAPI backend with JWT auth, role-based access (admin/creator/trainee)
- Admin panel: users, courses, audit logs, security, white-label, dev tools
- Basic course management with AI generation (topic + document)
- Course player (iframe-based)
- Learner portal at `/learn` — catalogue, course detail
- Creator portal at `/creator` — dashboard, course list, learner enrollments
- Path-prefix routing at `buildbench.uk/lms` via Traefik
- Deployed on Coolify with nixpacks staticfile provider

</details>

---

### 🚧 v1.0 AI Course Builder (Phases 9–18)

**Milestone Goal:** Creators can build and publish high-quality AI-assisted courses through a structured authoring flow — from course identity through slide editing, quiz building, and TTS narration — and publish with confidence using pre-flight validation.

- [x] **Phase 9: Vite Migration** — Replace single-file Babel frontend with a proper Vite + React build; verify all existing features work under `/lms` (completed 2026-05-08)
- [x] **Phase 10: Data Models** — Normalise course data from JSON blob to relational tables via Alembic migrations (completed 2026-05-09)
- [x] **Phase 11: Backend CRUD API** — Add all new creator API endpoints (modules, videos, slides, blocks, quizzes, uploads) (completed 2026-05-09)
- [x] **Phase 12: Course Identity & Structure** — Course creation Modal 1A (identity + AI assistance) and Modal 1B (structure wizard with live skeleton) (completed 2026-05-09)
- [x] **Phase 13: Course Builder & Module Detail** — Home-base Course Builder with left-rail tree, module card list, Module Detail with rich text and drag-drop reorder (completed 2026-05-09)
- [ ] **Phase 14: Slide Builder & Slide Editor** — Full slide authoring: thumbnail strip, 12-column snap-grid canvas, block library, undo/redo, autosave, AI slide outline wizard
- [ ] **Phase 15: AI Generation Infrastructure** — SSE streaming infrastructure, reusable AI drawer, document ingestion pipeline, AI suggestions rail
- [ ] **Phase 16: Quiz Builder** — Quiz creation with MCQ/true-false/short-answer questions, drag-to-reorder, AI question generation
- [ ] **Phase 17: TTS & Narration** — ElevenLabs narration audio generation (per-slide and bulk) with rate limiting and script-hash caching
- [ ] **Phase 18: Preview & Publish** — Full-course preview in learner view, pre-flight publish checklist, version history, archive

## Phase Details

### Phase 9: Vite Migration
**Goal**: The frontend runs as a proper Vite + React build deployed to Coolify, with all v0.1 features intact
**Depends on**: Nothing (continuing from v0.1 baseline)
**Requirements**: INFRA-01, INFRA-02, INFRA-03, INFRA-04, INFRA-05
**Success Criteria** (what must be TRUE):
  1. A tester can visit `buildbench.uk/lms`, log in, and use the admin panel, learner portal, and creator portal without any regression from v0.1
  2. Deep-linking to any route (e.g. `/lms/admin`, `/lms/creator`) works after a hard browser refresh
  3. The build pipeline produces a `frontend/dist/` directory; Coolify deploys it via nixpacks staticfile with the committed `nginx.conf`
  4. No Babel standalone script tag exists in the deployed HTML; assets reference `/lms/` path prefix correctly
**Plans**: 7 plans

Plans:
- [ ] 09-01-PLAN.md — Vite scaffold: package.json, vite.config.ts, tsconfig, nginx.conf, main.tsx, App.tsx stubs, vitest setup
- [ ] 09-02-PLAN.md — Core services and contexts: api.ts, AuthContext, ToastContext
- [ ] 09-03-PLAN.md — Common components: Modal, Button, Card, Badge, Input, Select, Textarea
- [ ] 09-04-PLAN.md — Layouts and auth guards: AdminLayout, LearnerLayout, CreatorLayout, ProtectedRoute, SmartRedirect, LoginPage
- [ ] 09-05-PLAN.md — Admin pages: AdminDashboard, UserManagementPage, CourseManagementPage, SecurityPage, DevToolsPage, WhiteLabelPage
- [ ] 09-06-PLAN.md — Creator and learner pages: CreatorDashboard, CreatorLearners, LearnerCatalogue, CourseDetail, ModuleAccordion, CourseViewerPage
- [ ] 09-07-PLAN.md — Wire App.tsx routes + Coolify staging smoke test checkpoint

### Phase 10: Data Models
**Goal**: All new relational tables exist in the production database, `Course.content` JSON is retired, and schema changes run automatically on every Coolify deploy
**Depends on**: Phase 9
**Requirements**: DATA-01, DATA-02, DATA-03, DATA-04, DATA-05, DATA-06, DATA-07, DATA-08, DATA-09
**Success Criteria** (what must be TRUE):
  1. Alembic `alembic upgrade head` runs on deploy without error; all 8+ new tables are present in the production database
  2. The `Course.content` JSON column no longer exists; existing course data has been migrated to the new relational structure without data loss
  3. A developer can confirm the Module, Video, Slide, Block, Quiz, Question, and Resource tables exist with correct columns via a database inspector or `alembic current`
  4. Rolling back the migration via `alembic downgrade` completes cleanly
**Plans**: 4 plans

Plans:
- [ ] 10-01-PLAN.md — Alembic bootstrap: install, alembic init, env.py with dynamic DB URL, failing test stubs for DATA-01 through DATA-09
- [ ] 10-02-PLAN.md — New SQLAlchemy models: Module, Video, Slide, Block, Quiz, Question, Resource, AiPromptLog + updated Course model
- [ ] 10-03-PLAN.md — Four Alembic migration scripts: extend courses, create 8 tables, data migration from content JSON, drop content column
- [ ] 10-04-PLAN.md — Coolify start command update + production migration smoke test checkpoint

### Phase 11: Backend CRUD API
**Goal**: All creator API endpoints for the new data model are live, auth-guarded, and testable via `/docs`
**Depends on**: Phase 10
**Requirements**: API-01, API-02, API-03, API-04, API-05, API-06, API-07
**Success Criteria** (what must be TRUE):
  1. A creator can create, read, update, delete, and reorder modules via the API; a non-creator token receives a 403
  2. A creator can create, read, update, delete, and reorder videos and slides via the API
  3. A creator can create and manage blocks within a slide, and quizzes with questions, via the API
  4. A creator can upload a file and receive back a stored URL via the upload endpoint
  5. All new endpoints are visible and exercisable in the FastAPI `/docs` UI
**Plans**: 4 plans

Plans:
- [ ] 11-01-PLAN.md — Module CRUD + reorder router, tests, register in main.py
- [ ] 11-02-PLAN.md — Video + Slide CRUD + reorder routers, tests, register in main.py
- [ ] 11-03-PLAN.md — Block + Quiz/Question CRUD + question reorder routers, tests, register in main.py
- [ ] 11-04-PLAN.md — Generic file upload endpoint, tests, register in main.py

### Phase 12: Course Identity & Structure
**Goal**: Creators can create a course with a full identity (title, description, objectives, AI tone) and scaffold its module/video/quiz structure before any content authoring begins
**Depends on**: Phase 11
**Requirements**: COURSE-01, COURSE-02, COURSE-03, COURSE-04, COURSE-05
**Success Criteria** (what must be TRUE):
  1. A creator can open Modal 1A, fill in title, description, audience level, tone preset, and up to 5 learning objectives, then save the course
  2. A creator can click "Generate with AI" for description or objectives and see streamed text appear in the field in real time
  3. A creator can open Modal 1B, input module/video/quiz counts, and see a live skeleton tree preview update as they type
  4. A creator can confirm the structure and navigate to Course Builder with the empty modules and videos already scaffolded in the tree
**Plans**: 5 plans

Plans:
- [ ] 12-01-PLAN.md — Wave 0: failing test stubs (COURSE-01 through COURSE-05) + sse-starlette in requirements.txt
- [ ] 12-02-PLAN.md — Backend: extend CourseCreate schema, add ClaudeService.stream_text(), two SSE endpoints
- [ ] 12-03-PLAN.md — Frontend: SkeletonTreePreview component (COURSE-04), test GREEN
- [ ] 12-04-PLAN.md — Frontend: CourseIdentityModal (1A), CourseStructureModal (1B), CreatorCourseListPage, App.tsx wiring
- [ ] 12-05-PLAN.md — Human verify: full Modal 1A → 1B → builder stub flow in browser

### Phase 13: Course Builder & Module Detail
**Goal**: Creators have a home-base Course Builder they can navigate from, and can edit any module's details — including AI-assisted description generation — with full drag-drop reorder of the content tree
**Depends on**: Phase 12
**Requirements**: BUILD-01, BUILD-02, BUILD-03, BUILD-04, BUILD-05, BUILD-06
**Success Criteria** (what must be TRUE):
  1. A creator sees the Course Builder with a left-rail tree listing all modules, videos, and quizzes; status pills (draft/published) are visible
  2. A creator can click a module, video, or quiz in the tree and navigate to the correct detail screen
  3. A creator can open Module Detail and edit title, description, learning outcome, duration estimate, and unlock rule; changes save
  4. A creator can drag modules and videos to reorder them in the Module Overview list; the new order persists after a page reload
  5. A creator can generate a module description via AI from a text prompt or uploaded document and see it stream in
**Plans**: 5 plans

Plans:
- [ ] 13-01-PLAN.md — Wave 0: install dnd-kit + failing test stubs (BUILD-01 through BUILD-06)
- [ ] 13-02-PLAN.md — Backend: SSE endpoint POST /api/modules/:id/ai/generate-description (BUILD-05)
- [ ] 13-03-PLAN.md — Frontend: CourseBuilderPage + CourseTreeRail + ModuleOverviewList with dnd-kit (BUILD-01, BUILD-02, BUILD-03, BUILD-06)
- [ ] 13-04-PLAN.md — Frontend: ModuleDetailPage form + AI streaming + App.tsx routes (BUILD-02, BUILD-04, BUILD-05)
- [ ] 13-05-PLAN.md — Human verify: full browser walkthrough of all 5 success criteria

### Phase 14: Slide Builder & Slide Editor
**Goal**: Creators can build slides visually using a 12-column snap-grid canvas with a full block library, undo/redo, autosave, narration scripting, and an AI-powered slide outline wizard
**Depends on**: Phase 13
**Requirements**: SLIDE-01, SLIDE-02, SLIDE-03, SLIDE-04, SLIDE-05, SLIDE-06, SLIDE-07, SLIDE-08, SLIDE-09, SLIDE-10, SLIDE-11, SLIDE-12
**Success Criteria** (what must be TRUE):
  1. A creator can open Slide Builder for a video and see a thumbnail strip; they can add, reorder, duplicate, and delete slides from the strip
  2. A creator can drag any block type (text, heading, image, video embed, code, quote, list, callout, divider) onto the canvas and it snaps to the 12-column grid
  3. A creator can resize and reposition blocks on the canvas, undo and redo changes (at least 20 steps), and see a "Saved" indicator after changes flush
  4. A creator can select a layout preset and see the canvas update to match that layout
  5. A creator can open the Narration tab, write a script, trigger AI narration script generation from slide content, and see the generated text stream in
  6. A creator can run the 4-step AI slide outline wizard (source → config → generation → commit) and have the resulting slides added to the strip
**Plans**: 5 plans

Plans:
- [ ] 13-01-PLAN.md — Wave 0: install dnd-kit + failing test stubs (BUILD-01 through BUILD-06)
- [ ] 13-02-PLAN.md — Backend: SSE endpoint POST /api/modules/:id/ai/generate-description (BUILD-05)
- [ ] 13-03-PLAN.md — Frontend: CourseBuilderPage + CourseTreeRail + ModuleOverviewList with dnd-kit (BUILD-01, BUILD-02, BUILD-03, BUILD-06)
- [ ] 13-04-PLAN.md — Frontend: ModuleDetailPage form + AI streaming + App.tsx routes (BUILD-02, BUILD-04, BUILD-05)
- [ ] 13-05-PLAN.md — Human verify: full browser walkthrough of all 5 success criteria

### Phase 15: AI Generation Infrastructure
**Goal**: All AI generation across the platform uses a single SSE streaming infrastructure with a reusable drawer component, document ingestion works for PDF and DOCX, and the AI suggestions rail is live in Course Builder
**Depends on**: Phase 14
**Requirements**: AI-01, AI-02, AI-03, AI-04, AI-05, AI-06, AI-07
**Success Criteria** (what must be TRUE):
  1. Every AI generation surface (course description, objectives, module description, narration script, slide outline, quiz questions) uses the same `SideDrawer` + `StreamingTextOutput` component — no ad-hoc streaming implementations exist
  2. A creator can upload a PDF or DOCX document in the slide outline wizard and receive a structured module/slide outline parsed from its contents
  3. The AI suggestions rail is visible in Course Builder and shows proactive nudges for missing descriptions, empty modules, and other completeness gaps
  4. The AI tone preset set in Modal 1A is visibly reflected in generation output (e.g. formal tone produces different phrasing than casual)
  5. Disconnecting the browser mid-stream stops token generation on the server (no orphaned Claude API calls)
**Plans**: 5 plans

Plans:
- [ ] 13-01-PLAN.md — Wave 0: install dnd-kit + failing test stubs (BUILD-01 through BUILD-06)
- [ ] 13-02-PLAN.md — Backend: SSE endpoint POST /api/modules/:id/ai/generate-description (BUILD-05)
- [ ] 13-03-PLAN.md — Frontend: CourseBuilderPage + CourseTreeRail + ModuleOverviewList with dnd-kit (BUILD-01, BUILD-02, BUILD-03, BUILD-06)
- [ ] 13-04-PLAN.md — Frontend: ModuleDetailPage form + AI streaming + App.tsx routes (BUILD-02, BUILD-04, BUILD-05)
- [ ] 13-05-PLAN.md — Human verify: full browser walkthrough of all 5 success criteria

### Phase 16: Quiz Builder
**Goal**: Creators can build quizzes with four question types, reorder questions by drag-and-drop, and generate a batch of questions via AI from module content
**Depends on**: Phase 15
**Requirements**: QUIZ-01, QUIZ-02, QUIZ-03, QUIZ-04, QUIZ-05, QUIZ-06, QUIZ-07, QUIZ-08
**Success Criteria** (what must be TRUE):
  1. A creator can create a quiz linked to a module and configure pass score, max attempts, and feedback settings
  2. A creator can add MCQ single-answer, MCQ multi-answer, true/false, and short-answer questions with correct answers and explanation text
  3. A creator can drag questions to reorder them; the new order persists after a page reload with no `order_index` drift
  4. A creator can trigger AI question generation from module content and see a batch of questions streamed in, then confirm them to the quiz
**Plans**: 5 plans

Plans:
- [ ] 13-01-PLAN.md — Wave 0: install dnd-kit + failing test stubs (BUILD-01 through BUILD-06)
- [ ] 13-02-PLAN.md — Backend: SSE endpoint POST /api/modules/:id/ai/generate-description (BUILD-05)
- [ ] 13-03-PLAN.md — Frontend: CourseBuilderPage + CourseTreeRail + ModuleOverviewList with dnd-kit (BUILD-01, BUILD-02, BUILD-03, BUILD-06)
- [ ] 13-04-PLAN.md — Frontend: ModuleDetailPage form + AI streaming + App.tsx routes (BUILD-02, BUILD-04, BUILD-05)
- [ ] 13-05-PLAN.md — Human verify: full browser walkthrough of all 5 success criteria

### Phase 17: TTS & Narration
**Goal**: Creators can generate ElevenLabs narration audio for individual slides or in bulk for an entire video, with rate limiting preventing API storms and caching preventing redundant regeneration
**Depends on**: Phase 16
**Requirements**: TTS-01, TTS-02, TTS-03, TTS-04, TTS-05
**Success Criteria** (what must be TRUE):
  1. A creator can click "Generate audio" on a single slide with a narration script and hear the resulting audio in the player
  2. A creator can trigger bulk audio generation for all slides in a video; slides with no script are skipped; progress is visible
  3. Running bulk generation twice does not re-call ElevenLabs for slides whose narration script has not changed since the last generation
  4. A creator can select from at least two ElevenLabs voice options before generating
**Plans**: 5 plans

Plans:
- [ ] 13-01-PLAN.md — Wave 0: install dnd-kit + failing test stubs (BUILD-01 through BUILD-06)
- [ ] 13-02-PLAN.md — Backend: SSE endpoint POST /api/modules/:id/ai/generate-description (BUILD-05)
- [ ] 13-03-PLAN.md — Frontend: CourseBuilderPage + CourseTreeRail + ModuleOverviewList with dnd-kit (BUILD-01, BUILD-02, BUILD-03, BUILD-06)
- [ ] 13-04-PLAN.md — Frontend: ModuleDetailPage form + AI streaming + App.tsx routes (BUILD-02, BUILD-04, BUILD-05)
- [ ] 13-05-PLAN.md — Human verify: full browser walkthrough of all 5 success criteria

### Phase 18: Preview & Publish
**Goal**: Creators can preview the full course as a learner, then publish with confidence using a pre-flight checklist — with version history ensuring enrolled learners are never disrupted
**Depends on**: Phase 17
**Requirements**: PREVIEW-01, PREVIEW-02, PREVIEW-03, PUBLISH-01, PUBLISH-02, PUBLISH-03, PUBLISH-04, PUBLISH-05, PUBLISH-06, PUBLISH-07, PUBLISH-08
**Success Criteria** (what must be TRUE):
  1. A creator can enter Preview Mode from Course Builder and see the full course rendered in learner view with a draft watermark; all block types render correctly and quizzes are answerable
  2. A creator can exit preview and land back exactly where they were in the builder
  3. A creator can initiate the publish flow and see a pre-flight checklist with pass/warn/fail results; each failed item deep-links to the exact screen needed to fix it
  4. A creator can publish a course (draft → published) and the course is visible to learners
  5. A creator can update a published course; a version snapshot is created; learners already enrolled retain their progress on the prior version while new enrolees see the updated version
  6. A creator can archive a published course; it is no longer visible in the public catalogue
**Plans**: 5 plans

Plans:
- [ ] 13-01-PLAN.md — Wave 0: install dnd-kit + failing test stubs (BUILD-01 through BUILD-06)
- [ ] 13-02-PLAN.md — Backend: SSE endpoint POST /api/modules/:id/ai/generate-description (BUILD-05)
- [ ] 13-03-PLAN.md — Frontend: CourseBuilderPage + CourseTreeRail + ModuleOverviewList with dnd-kit (BUILD-01, BUILD-02, BUILD-03, BUILD-06)
- [ ] 13-04-PLAN.md — Frontend: ModuleDetailPage form + AI streaming + App.tsx routes (BUILD-02, BUILD-04, BUILD-05)
- [ ] 13-05-PLAN.md — Human verify: full browser walkthrough of all 5 success criteria

---

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 9. Vite Migration | 7/7 | Complete | 2026-05-08 | - |
| 10. Data Models | 4/4 | Complete | 2026-05-09 | - |
| 11. Backend CRUD API | 4/4 | Complete    | 2026-05-09 | - |
| 12. Course Identity & Structure | 5/5 | Complete    | 2026-05-09 | - |
| 13. Course Builder & Module Detail | 5/5 | Complete    | 2026-05-09 | - |
| 14. Slide Builder & Slide Editor | v1.0 | 0/TBD | Not started | - |
| 15. AI Generation Infrastructure | v1.0 | 0/TBD | Not started | - |
| 16. Quiz Builder | v1.0 | 0/TBD | Not started | - |
| 17. TTS & Narration | v1.0 | 0/TBD | Not started | - |
| 18. Preview & Publish | v1.0 | 0/TBD | Not started | - |
