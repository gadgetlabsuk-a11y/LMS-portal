# State

## Current Position

Phase: Not started (defining requirements)
Plan: —
Status: Defining requirements for v1.0
Last activity: 2026-05-08 — Milestone v1.0 started

## Project Reference

See: .planning/PROJECT.md (updated 2026-05-08)

**Core value:** Creators can build and publish high-quality courses without technical knowledge
**Current focus:** Milestone v1.0 — AI Course Builder

## Accumulated Context

- Backend is stable and well-tested. No breaking changes expected.
- Frontend migration to Vite + React is the first gate — all new UI work goes in the new structure.
- The AI_COURSE_BUILDER_SPEC.md is the authoritative design document for the creator authoring experience.
- Vite + React build output must serve as static files under the `/lms` path prefix (same as current nginx setup).
- The existing FastAPI backend already has course CRUD endpoints. The new data model (Module, Video, Slide, Block, Quiz) will require new migrations and new API endpoints.
