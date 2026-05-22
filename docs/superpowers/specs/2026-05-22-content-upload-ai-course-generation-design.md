# Generate Course from Uploaded Content — Design Spec

**Date:** 2026-05-22
**Status:** Approved (design); pending implementation plan
**Author:** Stuart + Claude

## Summary

Add a creator-portal feature that lets a creator **upload one or more documents
(`.pptx`, `.docx`, `.pdf`), set a target shape (number of modules, videos per
module, slides per video), and have AI generate a full relational course from
that content** — Modules → Videos → Slides → content Blocks — with a
review-and-confirm gate before anything is persisted.

This produces *relational* content (the current Module/Video/Slide/Block model),
not the retired `Course.content` JSON blob. A legacy single-file
`POST /api/courses/generate-from-document` endpoint exists but is UI-less and
emits the retired shape; it is removed/redirected by this work.

## Goals

- Multi-file upload merged into a single source corpus.
- Creator-controlled structure: # modules, # videos per module, # slides per video, plus tone & difficulty.
- A reviewable, editable outline before any course is created (the safety gate).
- End state: a fully-populated **Draft** course the creator refines in the normal builder.
- Reuse existing infrastructure: `DocumentService` (extraction), `ClaudeService`
  (Sonnet 4.6), `useSSEStream`, slide/block model, brand styling.

## Non-Goals (v1 / YAGNI)

- Extracting **images/diagrams** from files into `image` blocks (text-only generation; images added manually).
- **Background-job / queue** infrastructure (we use a cancellable, client-driven sequential fill).
- **Quiz** generation from content (quizzes have their own existing generator; possible later add-on).
- **OCR** of scanned/image-only PDFs (relies on text-extractable files; surfaced as a limitation when a file yields no text).
- **Re-generating / diffing** an existing course from new sources.
- **Non-document sources** (URLs, video transcripts).

## Chosen Approach — "Outline-first, then fill content per-video"

Two AI phases, chosen over a single mega-call (brittle: model output limits + the
site's ~100s Cloudflare request timeout) and over a server-side background job
(no job infra today; SQLite has no volume; review would come after full generation).

1. **Phase 1 — Outline (the review gate).** Merge uploaded files into a corpus and
   ask Claude for an outline only: modules → videos → slide titles + a one-line
   brief each. Fast, small, fits well under the timeout.
2. **Review & edit.** Creator edits/removes/reorders before committing.
3. **Phase 2a — Persist.** On confirm, create the Draft Course + source-document
   rows + Module/Video/Slide stubs in one transaction.
4. **Phase 2b — Fill content per-video.** For each video, generate each slide's
   content `Block`s + narration grounded in the corpus, streamed with a progress
   bar, run sequentially and cancellable. Each call is bounded to one video so it
   never approaches the timeout. May be skipped ("skip content for now").

This also **redeems the creator's instinct** about the slide-level "AI Outline"
button: the existing `SlideOutlineWizard` slide generator gains optional
content-grounding from the course's stored source corpus, so AI generation is
content-driven at both the whole-course and single-video levels.

## User Flow

Entry point: a **"Generate from content"** choice in the **"+ New course"**
affordance on the creator course list (alongside "Blank course"). Opens a
multi-step wizard:

1. **Upload** — drag/drop multiple `.pptx/.docx/.pdf` files (with limits).
2. **Shape** — # modules, # videos per module, # slides per video (capped); tone; difficulty.
3. **Generate outline** — "Generating outline…" determinate state while Phase 1 runs.
4. **Review & edit** — editable tree of modules → videos → slides (rename/remove/reorder).
5. **Create** — Phase 2a persists the Draft course + source text; returns the structure.
6. **Fill content** — Phase 2b runs video-by-video with a progress bar; cancellable; or skip.

End: route to the course builder for the new Draft.

## Architecture

### Data model — one new table

`course_source_documents`:

| column | type | notes |
|---|---|---|
| `id` | int PK | |
| `course_id` | int FK → courses.id, `ON DELETE CASCADE` | |
| `filename` | str | original upload name |
| `content_type` | str | MIME |
| `char_count` | int | extracted length |
| `extracted_text` | Text | per-file extracted text |
| `created_at` | datetime | |

The grounding **corpus** = concatenation of `extracted_text` across a course's
rows. Purpose: provenance ("generated from these files") and the source for
Phase 2b (and the slide-level grounding upgrade). Requires **one Alembic migration**.

No other schema changes. Generated slides are normal `Slide` stubs
(`status='draft'`) whose `narration_script` is seeded from the outline brief;
`Block` rows are created during Phase 2b.

### Endpoints (all creator-only; ownership enforced)

1. **`POST /api/courses/ai/outline-from-content`** — Phase 1.
   - `multipart/form-data`: `files[]`, `modules` (int), `videos_per_module` (int),
     `slides_per_video` (int), `tone` (str), `difficulty` (str), optional `title` hint.
   - Extract & merge text → cap corpus to ~60,000 chars (see Limits) → `ClaudeService.generate_course_outline(...)`.
   - **Returned as a validated JSON response** (not a raw token stream) behind a
     determinate "Generating outline…" state. Pydantic-validated; **one automatic
     retry** on malformed model output. (More robust than the current wizard's
     client-side `JSON.parse` of a token stream.)
   - Response shape:
     ```json
     {
       "title": "...",
       "description": "...",
       "modules": [
         {"title": "...", "description": "...",
          "videos": [
            {"title": "...", "description": "...",
             "slides": [{"title": "...", "brief": "..."}]}
          ]}
       ]
     }
     ```
   - Persists nothing.

2. **`POST /api/courses/from-outline`** — Phase 2a.
   - `multipart/form-data`: the (possibly edited) approved outline (JSON string field)
     + the original `files[]` re-sent from the wizard's memory. Re-extraction is
     cheap and keeps the server **stateless** (no session cache for the corpus).
   - One transaction: create Draft `Course`, `CourseSourceDocument` rows, and
     `Module`/`Video`/`Slide` stubs honoring the structure; seed `Slide.narration_script` from `brief`.
   - Response: `{ "course_id": int, "videos": [{ "video_id": int, "slide_ids": [int] }] }`.

3. **`POST /api/videos/{video_id}/ai/generate-content`** — Phase 2b (streamed).
   - Loads the course's stored corpus + the video's slide stubs; for each slide,
     `ClaudeService.generate_slide_blocks(corpus, module/video/slide titles, brief)` →
     persists `Block` rows + `Slide.narration_script` → **streams per-slide progress (SSE)**.
   - Bounded to one video (≤ slides_per_video slides) so it stays within the timeout.
   - Per-video isolated: failure here flags the video "content pending — retry"
     without affecting other videos or the persisted structure.

### `ClaudeService` additions (Sonnet 4.6, inline prompts like existing methods)

- `generate_course_outline(corpus, n_modules, videos_per_module, slides_per_video, tone, difficulty)`
  → outline JSON. Instructed to use **only** the supplied source material, produce
  **exactly** the requested counts, titles + 1-line description/brief, strict JSON.
- `generate_slide_blocks(corpus, module_title, video_title, slide_title, brief)`
  → `{ blocks: [{type, content}], narration_script }`, grounded in corpus.
  Uses only text-bearing block types: `heading`, `text`, `quote`, `code`
  (the editor also supports `image`/`video_embed`, which need assets and stay manual).
- Shared **JSON validation/repair helper**: strip code fences, parse, validate
  against a Pydantic schema; one retry with a corrective instruction on failure.

### Frontend

New wizard `GenerateFromContentWizard` (modal; zustand store mirroring
`slideEditorStore`; Stadler styling; reuses `useSSEStream`, streaming/Button components):

- `ContentUploadStep` — multi-file drag/drop, file list, inline validation.
- `StructureSettingsStep` — count inputs (with caps) + tone & difficulty selects.
- `OutlineReviewEditor` — editable tree (rename/remove/reorder), layout cues from `CourseTreeRail`.
- `GenerationProgress` — iterates returned videos **sequentially**, calls
  `generate-content` per video via `useSSEStream`, advances a cancellable progress bar.

Store state: `files: File[]`, settings, `outline`, `course_id`, per-video progress.

`services/api.ts`: add two multipart POSTs (`outline-from-content`, `from-outline`)
and the SSE `generate-content` (reusing the established streaming reader + `Authorization` header).

Entry point: a "Generate from content" option in "+ New course" on the creator
course list; on finish or "skip content for now", route to the course builder.

## Error Handling & Limits

- **Upload:** allowed types `.pptx/.docx/.pdf`; per-file ≤ 10 MB (existing cap);
  max 10 files; total corpus capped (see Corpus cap).
  Unsupported/oversized rejected inline.
- **Unreadable file:** skip with a warning and continue if other files yielded
  text; if nothing extractable, block with a clear message.
- **Count caps:** ≤ 8 modules, ≤ 6 videos/module, ≤ 8 slides/video (tunable
  constants) — keeps generation within model + Cloudflare limits.
- **Corpus cap:** merged source text truncated to **~60,000 characters**
  (≈15k tokens) before being sent to the model, allocated proportionally across
  files; over-cap is truncated with a user-visible notice.
- **Outline failure / malformed JSON:** server validates + retries once; on failure
  the wizard shows an error and a **Retry that preserves uploaded files & settings**.
- **Persist (2a):** single transaction, all-or-nothing — no half-built course.
- **Fill (2b):** each video independent; a failed video flagged "content pending —
  retry"; others persist. Cancel mid-fill leaves a valid Draft with whatever completed.
- **Cost & auth:** creator-only + ownership checks; usage recorded via existing
  `ApiUsage`; a small "this uses AI credits" note in the wizard.

## Testing (TDD; `ClaudeService` mocked — no real API calls; backend runs targeted single files given iCloud slowness)

**Backend (pytest, existing fixtures):**
- `DocumentService` multi-file extraction (pptx/docx/pdf), corrupt/empty handling, corpus concatenation + cap/truncation.
- `outline-from-content`: valid JSON honors counts; malformed→retry path; count caps; file/type validation; creator-only.
- `from-outline`: persists the correct number of modules/videos/slides + `CourseSourceDocument` rows; narration seeded from brief; rollback on failure; ownership.
- `videos/{id}/ai/generate-content`: creates `Block`s + narration per slide; per-video isolation on failure; SSE progress; ownership.
- JSON validation/repair helper unit tests.

**Frontend (vitest + RTL, mock api/SSE):**
- Wizard step navigation; upload validation (bad types/over-count rejected); settings caps.
- `OutlineReviewEditor` edits reflected in the create payload.
- Progress advances per video; cancel path; "skip content" path.
- Error → Retry preserves uploads/settings.

## Migration / Deployment Notes

- One Alembic migration for `course_source_documents`.
- Backend deploy to Coolify is manual and **wipes SQLite** (no volume) — batch this
  with other backend work; recreate the seeded admin afterwards.
- Removing/redirecting the legacy `generate-from-document` endpoint has no frontend consumer.

## Open Questions

None at design time. (Block-image generation, quiz-from-content, and re-generation
are deliberate v1 non-goals.)
