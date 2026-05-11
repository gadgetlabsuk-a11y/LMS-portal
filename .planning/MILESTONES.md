# Milestones

## v1.0 AI Course Builder (Shipped: 2026-05-11)

**Phases:** 9–18 (10 phases) · **Plans:** 55 · **LOC:** ~21,600 (Python + TypeScript) · **Timeline:** 4 days

**Key accomplishments:**
- Migrated single-file 3420-line Babel frontend to full Vite + React + TypeScript build with role-based layouts (Admin/Creator/Learner)
- Normalised course data from JSON blobs to relational schema (Course/Module/Video/Slide/Block/Quiz/Question) via Alembic migrations
- Built complete creator authoring platform: Course Builder with live tree rail, Module Detail with rich text and drag-drop reorder
- Delivered full Slide Builder with 12-column snap-grid canvas, block library, undo/redo, autosave, and AI slide outline wizard
- Shipped SSE streaming AI generation infrastructure: Claude-powered content generation via reusable SideDrawer with bufferRef parse-on-completion pattern
- Integrated ElevenLabs TTS: per-slide audio + bulk generation with `asyncio.Semaphore(3)` rate limiting and script-hash caching
- Built Quiz Builder with 4 question types, drag-to-reorder (dnd-kit), and AI question generation
- Delivered Preview & Publish: learner-view preview with draft watermark, pre-flight checklist, course versioning with enrolment pinning, and archive

---

## v0.1 — LMS Foundation

**Shipped:** 2026-05-08
**Phases:** 1–8 (pre-GSD, tracked manually)

**What shipped:**
- FastAPI backend with JWT auth, role-based access (admin/creator/trainee)
- Admin panel: users, courses, audit logs, security, white-label, dev tools
- Basic course management with AI generation (topic + document)
- Course player (iframe-based)
- Learner portal at `/learn` — catalogue, course detail
- Creator portal at `/creator` — dashboard, course list, learner enrollments
- Path-prefix routing at `buildbench.uk/lms` via Traefik
- Deployed on Coolify with nixpacks staticfile provider

**Last phase:** 8 (creator portal)
