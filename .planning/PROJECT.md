# LMS Platform

## What This Is

An AI-powered LMS (Learning Management System) at `buildbench.uk/lms`. Creators build and publish high-quality courses using an AI-assisted authoring platform — from course identity through slide editing, quiz building, TTS narration, and pre-flight publish validation. Trainees discover and complete courses in a clean learner portal. Admins manage the platform via a full admin panel.

Backend: FastAPI + SQLAlchemy. Frontend: Vite + React + TypeScript.

## Core Value

Creators can build and publish high-quality courses without technical knowledge, and trainees can find and complete those courses easily.

## Requirements

### Validated

- ✓ JWT authentication with role-based access (admin / creator / trainee) — v0.1
- ✓ Admin panel: user management, audit logs, security, white-label settings — v0.1
- ✓ Basic course management (create/edit/delete, AI generation from topic or document) — v0.1
- ✓ Learner portal at `/learn` — course catalogue, course detail, course player — v0.1
- ✓ Creator portal at `/creator` — dashboard, course management, learner enrollments — v0.1
- ✓ Path-prefix routing at `buildbench.uk/lms/*` via Traefik — v0.1
- ✓ Deployed on Coolify with nixpacks staticfile provider for frontend — v0.1
- ✓ Vite + React migration (full build replacing single-file Babel frontend) — v1.0
- ✓ Relational data model (Course/Module/Video/Slide/Block/Quiz/Question via Alembic) — v1.0
- ✓ Full creator authoring: Course Builder, Module Detail, Slide Builder, Slide Editor — v1.0
- ✓ AI generation infrastructure: SSE streaming, SideDrawer, Claude-powered content — v1.0
- ✓ Quiz Builder: 4 question types, drag-to-reorder, AI question generation — v1.0
- ✓ ElevenLabs TTS narration: per-slide + bulk generation with caching — v1.0
- ✓ Preview & Publish: pre-flight checklist, course versioning, learner enrolment pinning, archive — v1.0

### Active

- [ ] Learner progress tracking (resume course, mark modules complete, quiz scoring)
- [ ] Enrolment management (creator-triggered enrolments, self-enrol links)
- [ ] Course completion certificates
- [ ] Creator analytics (completion rates, quiz scores, learner progress views)

### Out of Scope

- SCORM/xAPI export — complexity, deferred
- Real-time co-editing — complexity, deferred
- Talking-head video type — deferred (spec section 11)
- Mobile app — web-first
- AI image generation inside slide builder — deferred
- Voice cloning — deferred
- Offline mode — real-time is core value

## Context

- **Codebase:** ~21,600 LOC — FastAPI backend (`backend/`), Vite + React + TypeScript frontend (`frontend/`)
- **Tech stack:** FastAPI, SQLAlchemy 2.0, Alembic, Pydantic; React 18, Vite 6, TypeScript, Tailwind, Zustand, dnd-kit, TipTap
- **AI integration:** `claude_service.py` (Anthropic Claude) for course generation + quiz generation. ElevenLabs for TTS narration. SSE streaming via FastAPI `StreamingResponse`.
- **Deployment:** Coolify + Traefik on `buildbench.uk/lms`. Frontend builds to static files served by nginx. Backend on Uvicorn.
- **Database:** SQLite in dev, configurable via `DB_URL`. 5 Alembic migrations (001–005).
- **v1.0 shipped:** Full creator authoring platform — 10 phases, 55 plans, 246 commits over 4 days.

## Constraints

- **Tech stack:** FastAPI + SQLAlchemy (backend, keep); Vite + React (frontend, keep)
- **Deployment:** Coolify + Traefik on `buildbench.uk/lms`. Frontend must build to static files served by nginx.
- **Path prefix:** All frontend routes must work under `/lms` prefix (handled by Traefik stripprefix)
- **Single repo:** Frontend and backend coexist in the same repo

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Path prefix `/lms` via Traefik stripprefix | Avoids collision with tenant subdomains | ✓ Good |
| Single-file React + Babel for v0.1 | Fast to ship, no build step needed | ⚠️ Hit ceiling at 3420 lines — migrated in v1.0 |
| Migrate to Vite + React for v1.0 | Single file unsustainable for course builder complexity | ✓ Good — clean separation by feature |
| nixpacks staticfile provider | Provider generates correct nginx.conf automatically | ✓ Good |
| Creator portal separate from admin at `/creator` | Clean separation, creators don't see admin features | ✓ Good |
| Relational schema vs JSON blob for course content | JSON blob couldn't support slide editor, quiz builder, or granular updates | ✓ Good — enabled all v1.0 features |
| SSE streaming for AI generation | Real-time feedback for long-running Claude calls; `bufferRef` parse-on-completion pattern avoids mid-stream JSON parse errors | ✓ Good |
| `asyncio.Semaphore(3)` module-level for TTS bulk | Prevents ElevenLabs API storms; module-level avoids per-request recreation | ✓ Good |
| Script-hash caching for TTS | `SHA-256(narration_script)` vs `slide.narration_script_hash` — skips unchanged slides | ✓ Good |
| CourseVersion snapshot (JSON blob) for versioning | Relational clone of all child rows is unnecessary complexity | ✓ Good |
| Learner enrolment version pinning | `Enrollment.course_version` pins learner to version at time of enrolment | ✓ Good |
| SideDrawer z-index above Modal (z-[55]/z-[60] vs z-50) | Allows AI drawers to appear over modals without re-architecting modal stack | ✓ Good |
| Fragment pattern for SideDrawers outside Modal wrapper | Correct z-index stacking without DOM restructuring | ✓ Good |

---
*Last updated: 2026-05-11 after v1.0 milestone — AI Course Builder shipped*
