# Requirements: LMS Platform — Milestone v1.0 AI Course Builder

**Defined:** 2026-05-08
**Core Value:** Creators can build and publish high-quality courses without technical knowledge

---

## v1 Requirements

### Infrastructure (INFRA)

- [x] **INFRA-01**: Frontend is built with Vite + React (replaces single-file Babel; proper build step)
- [x] **INFRA-02**: Vite build outputs to `frontend/dist/` with `base: '/lms/'` (compatible with existing Traefik stripprefix + nginx setup)
- [x] **INFRA-03**: `nginx.conf` is committed to the repo (replaces opaque nixpacks Staticfile) with SPA fallback for all routes
- [x] **INFRA-04**: All existing features (auth, admin panel, learner portal, creator portal) continue to work after migration
- [x] **INFRA-05**: React Router operates with `basename=/lms`; all routes functional under path prefix

### Data Models (DATA)

- [x] **DATA-01**: Module table exists with `order_index`, `unlock_rule`, `status`, `description`, linked to Course
- [x] **DATA-02**: Video table exists with `type` (upload/embed/slides), `description`, `order_index`, linked to Module
- [x] **DATA-03**: Slide table exists with `order_index`, `status`, `layout`, `narration_script`, linked to Video
- [x] **DATA-04**: Block table exists with `type`, `content` (JSON), `position` (row/col/width/height), linked to Slide
- [x] **DATA-05**: Quiz table exists with `pass_score`, `max_attempts`, `show_feedback` settings, linked to Module
- [x] **DATA-06**: Question table exists with `type`, `prompt`, `options` (JSON), `correct_answer`, `explanation`, linked to Quiz
- [x] **DATA-07**: Resource table exists for uploaded files (URL, mime type, size), linked to Course
- [x] **DATA-08**: Alembic migrations set up; all new tables created via migration (not bare `create_all`)
- [x] **DATA-09**: `Course.content` JSON column retired; existing course data migrated to new relational structure

### Backend API (API)

- [x] **API-01**: Creator can CRUD modules (create, list, update, delete, reorder by `order_index`)
- [x] **API-02**: Creator can CRUD videos (create, list, update, delete, reorder by `order_index`)
- [x] **API-03**: Creator can CRUD slides (create, list, update, delete, reorder by `order_index`)
- [x] **API-04**: Creator can CRUD blocks within a slide (create, list, update, delete)
- [x] **API-05**: Creator can CRUD quizzes and questions (including bulk reorder for questions)
- [x] **API-06**: Creator can upload files and images (stored, URL returned)
- [x] **API-07**: All new endpoints protected by `require_creator` auth guard

### Course Identity & Structure (COURSE)

- [x] **COURSE-01**: Creator can create a course via Modal 1A (title, description, audience level, AI tone preset, up to 5 learning objectives)
- [x] **COURSE-02**: Creator can generate a course description via AI from topic (streaming)
- [x] **COURSE-03**: Creator can generate learning objectives via AI from course title/description (streaming)
- [x] **COURSE-04**: Creator sees Course Structure wizard (Modal 1B) with module/video/quiz count inputs and live skeleton tree preview
- [x] **COURSE-05**: Creator can confirm structure and have empty modules/videos scaffolded automatically

### Course Builder & Modules (BUILD)

- [ ] **BUILD-01**: Creator sees Course Builder as home base with left-rail tree (modules, videos, quizzes) and module card list
- [ ] **BUILD-02**: Creator can navigate to Module Detail, Video Detail, Quiz Builder from Course Builder
- [ ] **BUILD-03**: Creator sees module/video/quiz status pills (draft/published) in Course Builder
- [ ] **BUILD-04**: Creator can edit module details (title, description, learning outcome, duration estimate, unlock rule)
- [ ] **BUILD-05**: Creator can generate module description via AI from prompt or uploaded document (streaming)
- [ ] **BUILD-06**: Creator sees Module Overview with unified drag-drop reorder list (modules, videos, quizzes) and insert-between capability

### Slide Builder & Editor (SLIDE)

- [ ] **SLIDE-01**: Creator can access Slide Builder for a video and see a thumbnail strip of slides
- [ ] **SLIDE-02**: Creator can add, reorder, duplicate, and delete slides from the thumbnail strip
- [ ] **SLIDE-03**: Creator can trigger bulk narration audio generation for all slides with populated scripts
- [ ] **SLIDE-04**: Creator can open Slide Editor for any slide
- [ ] **SLIDE-05**: Creator can drag content blocks (text, heading, image, video embed, code, quote, list, callout, divider) onto a 12-column snap grid canvas
- [ ] **SLIDE-06**: Creator can resize and reposition blocks on the canvas
- [ ] **SLIDE-07**: Creator can undo and redo canvas changes (minimum 20-step history)
- [ ] **SLIDE-08**: Slide content autosaves on change; pending save flushes before navigation
- [ ] **SLIDE-09**: Creator can select a layout preset (title+content, two-column, full-bleed image, etc.)
- [ ] **SLIDE-10**: Creator can write or edit a narration script for a slide in the Narration tab
- [ ] **SLIDE-11**: Creator can generate a narration script via AI from slide content blocks (streaming)
- [ ] **SLIDE-12**: Creator can generate a slide outline via AI wizard (4-step: source → config → generation → commit)

### AI Generation (AI)

- [ ] **AI-01**: All AI generation uses SSE streaming (POST endpoint; `fetch` + `ReadableStream` on client — not `EventSource`)
- [ ] **AI-02**: A single reusable AI generation drawer (`SideDrawer` + `StreamingTextOutput`) is used across all generation surfaces
- [ ] **AI-03**: Creator can generate a slide outline from a prompt or uploaded document (document ingestion pipeline)
- [ ] **AI-04**: Document ingestion supports PDF and DOCX upload → Claude parses → returns module/slide structure
- [ ] **AI-05**: SSE generator checks `request.is_disconnected()` on every yield to prevent orphaned tokens
- [ ] **AI-06**: Creator sees AI suggestions rail in Course Builder (proactive completeness nudges: missing descriptions, empty modules, etc.)
- [ ] **AI-07**: AI tone preset from Modal 1A is passed as context to all AI generation calls for that course

### TTS / Narration (TTS)

- [ ] **TTS-01**: Creator can generate narration audio for a slide from its narration script (ElevenLabs)
- [ ] **TTS-02**: Creator can bulk generate narration audio for all slides in a video with populated scripts
- [ ] **TTS-03**: TTS service uses a semaphore to rate-limit concurrent requests and prevent 429s on bulk generation
- [ ] **TTS-04**: Generated narration audio is cached; bulk re-generate only reprocesses slides with changed scripts
- [ ] **TTS-05**: Creator can select from available ElevenLabs voice options

### Quiz Builder (QUIZ)

- [ ] **QUIZ-01**: Creator can create a quiz linked to a module with pass score, max attempts, and feedback settings
- [ ] **QUIZ-02**: Creator can add MCQ single-answer questions
- [ ] **QUIZ-03**: Creator can add MCQ multi-answer questions
- [ ] **QUIZ-04**: Creator can add true/false questions
- [ ] **QUIZ-05**: Creator can add short answer questions
- [ ] **QUIZ-06**: Creator can add explanation text to each question (shown to learner after answering)
- [ ] **QUIZ-07**: Creator can reorder questions via drag-and-drop (atomic `order_index` update, no drift)
- [ ] **QUIZ-08**: Creator can generate a batch of quiz questions via AI from module content (streaming)

### Preview Mode (PREVIEW)

- [ ] **PREVIEW-01**: Creator can preview the full course in learner-view mode (shows draft watermark)
- [ ] **PREVIEW-02**: Preview renders all block types; narration scripts visible; quiz in answerable form
- [ ] **PREVIEW-03**: Creator can exit preview and return to where they were in the builder

### Publish Flow & Versioning (PUBLISH)

- [ ] **PUBLISH-01**: Creator can initiate publish flow from Course Builder
- [ ] **PUBLISH-02**: Creator sees pre-flight validation checklist with pass/warn/fail per rule before publishing
- [ ] **PUBLISH-03**: Pre-flight rules include: thumbnail uploaded, at least one module with content, each quiz has ≥3 questions
- [ ] **PUBLISH-04**: Each failed pre-flight rule deep-links to the exact screen needed to fix it
- [ ] **PUBLISH-05**: Creator can publish a course (draft → published state transition)
- [ ] **PUBLISH-06**: Creator can update a published course; system creates a version snapshot before replacing
- [ ] **PUBLISH-07**: Learners enrolled on a prior version retain their progress; new enrolees get the latest version
- [ ] **PUBLISH-08**: Creator can archive a published course (published → archived)

---

## v1.1 Requirements

Deferred from v1 — no blocking dependency on these for first cohort.

### Quiz Builder Extensions

- **QUIZ-09**: Creator can add drag-and-match questions
- **QUIZ-10**: Creator can add fill-in-the-blank questions

### Module Unlock Scheduling

- **BUILD-07**: Creator can set a module to unlock on a specific number of days after enrolment (scheduled_days unlock rule variant)

### Publish Scheduling

- **PUBLISH-09**: Creator can schedule a course to publish at a future date/time

### Analytics

- **ANLYT-01**: Each quiz question can be linked to a course learning objective for objective-level analytics

---

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| SCORM / xAPI export | 1990s spec, large standalone effort, not needed for target buyers — explicitly out of scope per PROJECT.md |
| Real-time collaborative editing | Requires OT/CRDTs + WebSockets; disproportionate complexity for rare use case — explicitly out of scope per PROJECT.md |
| AI image generation inside slide builder | Separate image gen API, moderation, and storage; Unsplash/URL/upload covers the use case — explicitly out of scope per PROJECT.md |
| Voice cloning for TTS | Legal risk (consent, misuse), higher complexity and cost; curated voice library from ElevenLabs is sufficient — explicitly out of scope per PROJECT.md |
| Talking-head video recording | Requires browser media APIs + cloud recording pipeline — a separate product surface; uploaded video type covers the use case — explicitly out of scope per PROJECT.md |
| Gamification (badges, points, leaderboards) | Trivialises professional training; certificate on completion is the right unit for this LMS |
| Multi-language / translation workflow | Separate feature area; English-first |
| Per-slide analytics heatmaps | Needs a separate analytics milestone; module-level completion rates are sufficient for v1 |
| PowerPoint / SCORM import | Spec notes "reserve UI placement" — defer to v2 |
| Math (LaTeX) / interactive hotspot blocks | Spec section 11 — niche use cases, deferred |

---

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| INFRA-01 | Phase 9 | Complete |
| INFRA-02 | Phase 9 | Complete |
| INFRA-03 | Phase 9 | Complete |
| INFRA-04 | Phase 9 | Complete |
| INFRA-05 | Phase 9 | Complete |
| DATA-01 | Phase 10 | Complete |
| DATA-02 | Phase 10 | Complete |
| DATA-03 | Phase 10 | Complete |
| DATA-04 | Phase 10 | Complete |
| DATA-05 | Phase 10 | Complete |
| DATA-06 | Phase 10 | Complete |
| DATA-07 | Phase 10 | Complete |
| DATA-08 | Phase 10 | Complete |
| DATA-09 | Phase 10 | Complete |
| API-01 | Phase 11 | Complete |
| API-02 | Phase 11 | Complete |
| API-03 | Phase 11 | Complete |
| API-04 | Phase 11 | Complete |
| API-05 | Phase 11 | Complete |
| API-06 | Phase 11 | Complete |
| API-07 | Phase 11 | Complete |
| COURSE-01 | Phase 12 | Complete |
| COURSE-02 | Phase 12 | Complete |
| COURSE-03 | Phase 12 | Complete |
| COURSE-04 | Phase 12 | Complete |
| COURSE-05 | Phase 12 | Complete |
| BUILD-01 | Phase 13 | Pending |
| BUILD-02 | Phase 13 | Pending |
| BUILD-03 | Phase 13 | Pending |
| BUILD-04 | Phase 13 | Pending |
| BUILD-05 | Phase 13 | Pending |
| BUILD-06 | Phase 13 | Pending |
| SLIDE-01 | Phase 14 | Pending |
| SLIDE-02 | Phase 14 | Pending |
| SLIDE-03 | Phase 14 | Pending |
| SLIDE-04 | Phase 14 | Pending |
| SLIDE-05 | Phase 14 | Pending |
| SLIDE-06 | Phase 14 | Pending |
| SLIDE-07 | Phase 14 | Pending |
| SLIDE-08 | Phase 14 | Pending |
| SLIDE-09 | Phase 14 | Pending |
| SLIDE-10 | Phase 14 | Pending |
| SLIDE-11 | Phase 14 | Pending |
| SLIDE-12 | Phase 14 | Pending |
| AI-01 | Phase 15 | Pending |
| AI-02 | Phase 15 | Pending |
| AI-03 | Phase 15 | Pending |
| AI-04 | Phase 15 | Pending |
| AI-05 | Phase 15 | Pending |
| AI-06 | Phase 15 | Pending |
| AI-07 | Phase 15 | Pending |
| QUIZ-01 | Phase 16 | Pending |
| QUIZ-02 | Phase 16 | Pending |
| QUIZ-03 | Phase 16 | Pending |
| QUIZ-04 | Phase 16 | Pending |
| QUIZ-05 | Phase 16 | Pending |
| QUIZ-06 | Phase 16 | Pending |
| QUIZ-07 | Phase 16 | Pending |
| QUIZ-08 | Phase 16 | Pending |
| TTS-01 | Phase 17 | Pending |
| TTS-02 | Phase 17 | Pending |
| TTS-03 | Phase 17 | Pending |
| TTS-04 | Phase 17 | Pending |
| TTS-05 | Phase 17 | Pending |
| PREVIEW-01 | Phase 18 | Pending |
| PREVIEW-02 | Phase 18 | Pending |
| PREVIEW-03 | Phase 18 | Pending |
| PUBLISH-01 | Phase 18 | Pending |
| PUBLISH-02 | Phase 18 | Pending |
| PUBLISH-03 | Phase 18 | Pending |
| PUBLISH-04 | Phase 18 | Pending |
| PUBLISH-05 | Phase 18 | Pending |
| PUBLISH-06 | Phase 18 | Pending |
| PUBLISH-07 | Phase 18 | Pending |
| PUBLISH-08 | Phase 18 | Pending |

**Coverage:**
- v1 requirements: 75 total
- Mapped to phases: 75
- Unmapped: 0 ✓

---
*Requirements defined: 2026-05-08*
*Last updated: 2026-05-08 — traceability populated by roadmapper (phases 9–18)*
