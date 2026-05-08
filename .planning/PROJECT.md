# LMS Platform

## What This Is

A multi-tenant LMS (Learning Management System) hosted at `buildbench.uk/lms`. The platform serves three user roles: admins (manage everything), creators (build and publish courses), and trainees (take courses). The backend is FastAPI + SQLAlchemy; the current frontend is a single-file React + Babel app.

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

### Active

- [ ] Vite + React migration (replace single-file index.html with a proper build)
- [ ] AI-assisted course authoring platform per AI_COURSE_BUILDER_SPEC.md

### Out of Scope

- SCORM/xAPI export — complexity, deferred
- Real-time co-editing — complexity, deferred
- Talking-head video type — deferred (spec section 11)
- Mobile app — web-first
- AI image generation inside slide builder — deferred
- Voice cloning — deferred

## Context

- **Codebase:** FastAPI backend (`backend/`), single-file frontend (`frontend/index.html`, now 3420 lines), nginx served via nixpacks staticfile provider on Coolify
- **Current frontend:** All React components inline in one file with Babel standalone transform. Works but cannot scale to a slide editor and quiz builder.
- **AI integration:** Backend uses `claude_service.py` for Claude-powered course generation. Currently supports topic-based and document-based generation.
- **Spec:** Full creator authoring spec at `LMS platform/AI_COURSE_BUILDER_SPEC.md` — covers Course Identity, Course Structure wizard, Course Builder scaffold, Module Detail, Video Detail, Slide Builder, Slide Editor, Quiz Builder, Preview Mode, and Publish Flow.
- **Key open questions from spec:** TTS provider (ElevenLabs/OpenAI/Azure), AI model tier config, slide layout library, quiz question types for v1, version retention policy.

## Constraints

- **Tech stack:** FastAPI + SQLAlchemy (backend, keep); migrate frontend to Vite + React
- **Deployment:** Coolify + Traefik on `buildbench.uk/lms`. Frontend must build to static files served by nginx.
- **Path prefix:** All frontend routes must work under `/lms` prefix (handled by Traefik stripprefix, no change needed)
- **Single repo:** Frontend and backend coexist in the same repo

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Path prefix `/lms` via Traefik stripprefix | Avoids collision with tenant subdomains | ✓ Good |
| Single-file React + Babel for v0.1 | Fast to ship, no build step needed | ⚠️ Revisit — file grew to 3420 lines, cannot support slide editor |
| Migrate to Vite + React for v1.0 | Single file unsustainable for course builder complexity | — Pending |
| nixpacks staticfile provider (no custom nixpacks.toml) | Provider already generates correct nginx.conf | ✓ Good |
| Creator portal separate from admin at `/creator` | Clean separation, creators don't see admin features | ✓ Good |

---
*Last updated: 2026-05-08 after v0.1 completion (creator portal shipped)*
