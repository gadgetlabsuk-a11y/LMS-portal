# Roadmap: LMS Platform

## Milestones

- ✅ **v0.1 LMS Foundation** — Phases 1–8 (shipped 2026-05-08)
- ✅ **v1.0 AI Course Builder** — Phases 9–18 (shipped 2026-05-11)
- 📋 **v1.1** — Next milestone (planned)

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

<details>
<summary>✅ v1.0 AI Course Builder (Phases 9–18) — SHIPPED 2026-05-11</summary>

- [x] **Phase 9: Vite Migration** — Replace single-file Babel frontend with Vite + React build (completed 2026-05-08)
- [x] **Phase 10: Data Models** — Normalise course data from JSON blob to relational tables via Alembic (completed 2026-05-09)
- [x] **Phase 11: Backend CRUD API** — Add all creator API endpoints (modules, videos, slides, blocks, quizzes, uploads) (completed 2026-05-09)
- [x] **Phase 12: Course Identity & Structure** — Course creation Modal 1A (identity + AI) and Modal 1B (structure wizard) (completed 2026-05-09)
- [x] **Phase 13: Course Builder & Module Detail** — Course Builder with left-rail tree, Module Detail with rich text and drag-drop (completed 2026-05-09)
- [x] **Phase 14: Slide Builder & Slide Editor** — Slide authoring: thumbnail strip, snap-grid canvas, block library, undo/redo, autosave (completed 2026-05-09)
- [x] **Phase 15: AI Generation Infrastructure** — SSE streaming, reusable SideDrawer, document ingestion, AI suggestions rail (completed 2026-05-10)
- [x] **Phase 16: Quiz Builder** — Quiz creation with 4 question types, drag-to-reorder, AI question generation (completed 2026-05-10)
- [x] **Phase 17: TTS & Narration** — ElevenLabs audio generation (per-slide + bulk) with rate limiting and hash caching (completed 2026-05-10)
- [x] **Phase 18: Preview & Publish** — Learner-view preview, pre-flight checklist, course versioning, archive (completed 2026-05-11)

Full details: `.planning/milestones/v1.0-ROADMAP.md`

</details>

---

### 📋 v1.1 (Planned)

*Next milestone — start with `/gsd:new-milestone`*

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1–8 | v0.1 | — | Complete | 2026-05-08 |
| 9. Vite Migration | v1.0 | 7/7 | Complete | 2026-05-08 |
| 10. Data Models | v1.0 | 4/4 | Complete | 2026-05-09 |
| 11. Backend CRUD API | v1.0 | 4/4 | Complete | 2026-05-09 |
| 12. Course Identity & Structure | v1.0 | 5/5 | Complete | 2026-05-09 |
| 13. Course Builder & Module Detail | v1.0 | 5/5 | Complete | 2026-05-09 |
| 14. Slide Builder & Slide Editor | v1.0 | 8/8 | Complete | 2026-05-09 |
| 15. AI Generation Infrastructure | v1.0 | 6/6 | Complete | 2026-05-10 |
| 16. Quiz Builder | v1.0 | 5/5 | Complete | 2026-05-10 |
| 17. TTS & Narration | v1.0 | 6/6 | Complete | 2026-05-10 |
| 18. Preview & Publish | v1.0 | 5/5 | Complete | 2026-05-11 |
