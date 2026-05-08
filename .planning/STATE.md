# State

## Current Position

Phase: 9 (Vite Migration) — In progress
Plan: 09-03 complete; next: 09-04
Status: Plans 09-01, 09-03 complete — 7 common UI components extracted, build passes, 4 tests passing
Last activity: 2026-05-08 — Completed 09-03-PLAN.md (Common UI Components)

## Project Reference

See: .planning/PROJECT.md (updated 2026-05-08)

**Core value:** Creators can build and publish high-quality courses without technical knowledge
**Current focus:** Milestone v1.0 — AI Course Builder (Phases 9–18)

## Performance Metrics

- Phases complete: 0/10 (v1.0)
- Plans complete: 1/TBD (09-01 done)
- Requirements mapped: 75/75

| Phase | Plan | Duration | Tasks | Files |
|-------|------|----------|-------|-------|
| 09    | 01   | ~4 min   | 2/2   | 19    |
| 09    | 03   | ~6 min   | 2/2   | 7     |

## Accumulated Context

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

Next action: Continue with 09-02 and/or 09-04 (page components).
