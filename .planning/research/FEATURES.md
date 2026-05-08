# Feature Research

**Domain:** AI-assisted course authoring platform (LMS creator-side)
**Researched:** 2026-05-08
**Confidence:** HIGH (spec-aligned) / MEDIUM (competitor pattern research)

---

## Context

This research covers the new AI Course Builder milestone being added to an existing LMS at `buildbench.uk/lms`. The existing platform already has JWT auth, role-based access, basic course CRUD, AI generation from topic/document, admin panel, creator portal, and learner portal. This research focuses exclusively on what the AI course authoring features need to look like — what users absolutely expect, what differentiates, and what to avoid.

The full feature spec lives in `LMS platform/AI_COURSE_BUILDER_SPEC.md`. This document categorises those features and adds market context.

---

## Feature Landscape

### Table Stakes (Users Expect These)

Features creators assume exist in any course authoring tool. Missing these makes the product feel unfinished or unusable.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Course identity form (title, description, objectives, audience level) | Every course platform starts here; creators expect a clean intake form | LOW | Already partially exists; Modal 1A in spec extends it with AI tone preset and better validation |
| Module/lesson hierarchy | All major platforms (Teachable, Thinkific, Articulate) organise content in modules containing lessons/videos | LOW | Spec models Course > Module > Video > Slide; already in data model |
| Rich text editing for descriptions | Plain textarea is not acceptable for course content; creators need formatting | MEDIUM | RichTextEditor component needed; markdown-out approach is sensible |
| Drag-and-drop content reordering | Creators expect to reorder modules, videos, and slides without re-entering data | MEDIUM | Required at three levels: module list, video list, slide strip; use dnd-kit or similar |
| Autosave | Losing work mid-edit is a showstopper; all modern tools autosave continuously | MEDIUM | "Save by default" is a spec design principle; every field change triggers save |
| Draft/published status separation | Creators need to work on a course without it going live | LOW | State machine in spec: draft → published → has_unpublished_changes → archived |
| Preview mode (as learner) | Without preview, creators cannot verify their work looks right | MEDIUM | Spec section 4.11; renders current draft in learner UI with watermark |
| Publish flow with validation | Creators need a checklist of what's broken before they commit to publish | MEDIUM | Spec section 4.12; pre-flight checklist with pass/warn/fail per rule |
| Course thumbnail | Every course catalogue shows a thumbnail; missing image feels unfinished | LOW | Required before publish (rule C001); image upload with min 1200x675 |
| Quiz with multiple question types | At minimum MCQ and true/false are expected; every authoring tool has these | MEDIUM | Spec supports 6 types; trim to MCQ single, MCQ multi, true/false, short answer for v1 if needed |
| Question feedback/explanation | Learners expect to see why their answer was right or wrong | LOW | Explanation field per question in spec; shown after answer per show_feedback setting |
| Course structure overview (tree or outline) | Creators need to see the full course shape at a glance | LOW | Left-rail TreeView in Course Builder (spec 4.4); also Module Overview (spec 4.10) |
| Undo/redo in slide editor | Drag-and-drop canvas without undo is unusable; this is expected from any editor | HIGH | Canvas state management; spec explicitly calls out Undo/Redo in slide editor top bar |
| Content block types: text, heading, image, video embed | These four are the baseline; any fewer feels like a prototype | MEDIUM | Spec block library includes all four plus code, quote, list, callout, divider |

### Differentiators (Competitive Advantage)

Features that go beyond what creators expect. The spec is explicitly designed around these — they are the reason this platform exists rather than sending creators to Teachable.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| AI slide outline generation | Creator provides a description or document, AI produces a full slide deck outline with titles, summaries, and layout suggestions — creator reviews and accepts | HIGH | Spec section 4.6; 4-step wizard (source → config → generation → commit); requires streaming output |
| AI narration script generation per slide | AI reads the slide's content blocks and drafts a voiceover script matched to the visible content — no copy-paste required | MEDIUM | Spec section 4.8 Narration tab; "Generate from slide content" button; uses fast model |
| AI TTS voiceover generation | One-click "Generate narration" at the Slide Builder level converts all narration scripts to audio via TTS — eliminates recording studio | HIGH | Spec section 4.7; TTS provider TBD (ElevenLabs recommended for quality, OpenAI TTS for cost); audio stored per slide |
| AI quiz question generation from module content | AI reads all video descriptions and slide content in the module and drafts a question set — creator reviews each question rather than writing from scratch | HIGH | Spec section 4.9; two variants: from module content (standard model) and from learning objective (fast model) |
| Document ingestion to course structure | Creator uploads a PDF or DOCX, AI parses and produces a module/slide structure aligned to the course tone — turns existing materials into courses | HIGH | Spec section 5 (document ingestion pipeline); pdfminer + docx parser + Claude; most impactful for corporate training buyers |
| Course structure wizard with live preview | Modal 1B lets creator set module count, videos per module, quiz count, and see the full skeleton tree before committing — prevents blank-page anxiety | MEDIUM | Spec section 4.3; live tree preview pane is the differentiator; most tools just dump you in an empty builder |
| AI suggestions rail | Right rail on Course Builder surfaces proactive suggestions ("Module 3 has no description yet, generate one?") — creator always has a next action | MEDIUM | Spec section 4.4; requires a background completeness scan of full course state |
| Snap-to-grid slide canvas with layout presets | 12-column grid, preset layouts (title+content, two-column, full-bleed image etc.) makes professional-looking slides achievable without design skill | HIGH | Spec section 4.8 CanvasGrid; hardest component to build; consider Fabric.js or react-konva for canvas management |
| Inline AI generation at every text field | Every description field has an AI assist drawer (from prompt or from document) — creators are never stuck on a blank field | MEDIUM | Spec sections 4.5, 4.6; dual-tab drawer pattern used consistently across Module Detail and Video Detail |
| Version history on publish | Published course retains prior version; learners on v(n-1) keep progress, new enrolees get vN — no disruption on updates | MEDIUM | Spec section 4.12 "Publish update"; requires course version column and learner progress scoped to version |
| Learning objective linkage to quiz questions | Each quiz question can be linked to a course learning objective, enabling objective-level analytics later | LOW | Spec Question.linked_objective_id; low build cost, high future analytics value |
| Module unlock rules | Immediate, after_previous, or scheduled (days after enrolment) unlock — supports drip-feed and structured learning paths | MEDIUM | Spec Module.unlock_rule; most consumer tools lack this; it is expected in corporate LMS |

### Anti-Features (Commonly Requested, Often Problematic)

Features that seem valuable but should be explicitly deferred or avoided. These create scope creep, complexity, or poor UX if added prematurely.

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Real-time collaborative editing | Creators imagine working simultaneously on a course like Google Docs | Requires operational transforms (OT) or CRDTs, websockets, conflict resolution — massive complexity for a rare use case on this platform | Single-editor model with clear ownership; use duplicate + import to share structure later |
| SCORM/xAPI export | Enterprise buyers often have old LMS infrastructure that requires SCORM packages | SCORM is a 1990s spec; adding it requires an entirely separate packaging pipeline, and the target buyer here is builders not enterprise buyers with legacy LMS | Build native analytics instead; explicitly out of scope per PROJECT.md |
| AI image generation inside slide builder | Creators want imagery without leaving the builder | Complicates the build significantly (separate image gen API, moderation, storage), adds cost per-generation, and distracts from content | Free image search (Unsplash API) or URL/upload; explicitly deferred per PROJECT.md |
| Voice cloning for narration | Creators want to clone their own voice for TTS | Legal risk (consent, misuse), higher implementation complexity, cost; ElevenLabs voice cloning requires separate API tier | Offer a curated voice library from TTS provider; explicitly deferred per PROJECT.md |
| Talking-head video type | Creators want webcam recording integrated into the builder | Requires browser media APIs, cloud recording, processing pipeline — a separate product surface; talking-head lessons need a recording UX that is not a slide editor | Uploaded video type covers this use case if creator has existing recordings; defer per PROJECT.md |
| Gamification (badges, leaderboards, points) | Learner engagement feature often requested | Significant schema additions, separate display logic, risk of trivialising professional training content | Certificate on completion is the right gamification unit for professional LMS; already in spec |
| AI-locked content (non-editable AI output) | Tempting to "protect" AI generation quality | Violates the core design principle "Editable everywhere"; creators who can't modify AI output will distrust the platform | Every AI output drops into an editable field; accept/regenerate/edit pattern per spec |
| Mandatory AI generation | Forcing AI use for all fields to showcase the feature | Some creators have their content ready; mandatory AI is friction, not assistance | AI is always opt-in; every field is editable without touching AI |
| Per-slide analytics heatmaps | Knowing exactly where learners drop off per slide sounds valuable | Requires detailed event tracking, aggregation pipeline, and visualisation — a separate analytics milestone | Module-level completion rates are sufficient for v1; slide-level events can be added later |
| Multi-language content (translation) | Global reach is appealing | Doubles the content management surface; requires translation workflow, locale-aware rendering; entirely separate feature area | English-first; translation deferred per PROJECT.md |

---

## Feature Dependencies

```
[Course Identity (Modal 1A)]
    └──required before──> [Course Structure (Modal 1B)]
                              └──required before──> [Course Builder scaffold]
                                                        └──required before──> [Module Detail]
                                                        └──required before──> [Module Overview]

[Module Detail]
    └──required before──> [Video Detail]
                              └──required before──> [Slide Builder]
                                                        └──required before──> [Slide Editor (canvas)]

[Slide Editor]
    └──required before──> [AI narration script generation]
                              └──required before──> [AI TTS voiceover generation]

[Video Detail AI slide outline generation]
    └──populates──> [Slide Builder] with draft slides
                        └──required before──> [Slide Editor can open anything useful]

[Module Detail]
    └──required before──> [Quiz Builder]

[Quiz Builder]
    └──uses──> [AI question generation from module content]
                   └──depends on──> [slides having content blocks populated]

[Draft state machine]
    └──required before──> [Publish Flow]
                              └──required before──> [Version history on publish update]

[Document ingestion pipeline (backend)]
    └──enables──> [Module Detail: from document tab]
    └──enables──> [Video Detail: from document tab]
    └──enables──> [Course creation from document] (existing feature, already built)

[Autosave]
    └──required before──> [Undo/Redo] (undo must not conflict with autosave)

[AI tone preset (Modal 1A)]
    └──feeds into──> all AI generation operations across the whole course

[Learning objectives (Modal 1A)]
    └──feeds into──> [Quiz Builder: generate from objective]
    └──feeds into──> [Question: linked_objective_id]
    └──enables future──> [Objective-level analytics]
```

### Dependency Notes

- **Course Identity must be captured before anything else:** AI tone preset and learning objectives set in Modal 1A propagate into every downstream AI generation call. Building the course without them means the AI has no context.
- **Slide content must exist before AI narration can be useful:** "Generate from slide content" reads the blocks on the canvas. If slides are empty, the generated script will be generic. Slide content population therefore gates narration quality, not just narration availability.
- **TTS audio generation requires narration scripts:** Bulk "Generate narration" on the Slide Builder processes all slides with populated scripts. Slides without scripts are skipped. This is expected behaviour, not a bug.
- **Document ingestion pipeline is shared infrastructure:** The same backend pipeline (extract → chunk → generate) underpins module description from document, video description from document, and slide outline from document. Build it once as a reusable service.
- **Publish flow requires all validation rules to be implemented first:** The pre-flight checklist is only useful if the status fields (slide.status, quiz.status, etc.) are auto-calculated correctly throughout the authoring flow.
- **Version history on publish update is not the same as autosave:** Autosave is continuous draft persistence. Version history is a snapshot created at the moment of publish. These are independent systems and should not be conflated.

---

## MVP Definition

### Launch With (v1)

This is everything in the spec's acceptance criteria (spec section 10). All ten criteria must pass for v1 to ship.

- [ ] Course Identity wizard (Modal 1A) with AI description and objectives generation
- [ ] Course Structure wizard (Modal 1B) with live skeleton preview
- [ ] Course Builder scaffold (left rail tree, module card list, status pills)
- [ ] Module Detail with rich text and AI description generation (prompt + document)
- [ ] Video Detail with video type selection and AI slide outline generation wizard
- [ ] Slide Builder (thumbnail strip, add/reorder/delete, bulk narration generation)
- [ ] Slide Editor (drag-drop canvas, all block types in spec except Math and Hotspot, narration tab, layout tab)
- [ ] Quiz Builder with MCQ single, MCQ multi, true/false, short answer (drag_match and fill_blank can defer to v1.1)
- [ ] AI quiz question generation from module content
- [ ] Module Overview (unified reorder list with insert between items)
- [ ] Preview mode (learner-view render of draft state)
- [ ] Publish flow with pre-flight checklist and version management

### Add After Validation (v1.1)

Features with real user value but not blockers for the first cohort of creators.

- [ ] AI TTS voiceover audio generation — high value but requires TTS provider decision and cost model; can launch with narration scripts only and add audio after
- [ ] AI suggestions right rail — proactive completeness nudges; not critical for first creator sessions, add once core flow works
- [ ] Drag-match and fill-blank question types — MCQ + true/false + short answer covers 90% of quiz use cases
- [ ] Scheduled publish (date/time) — immediate publish covers v1
- [ ] Module unlock rules (scheduled_days variant) — immediate and after_previous cover the core LMS pattern; date-based scheduling is a power feature

### Future Consideration (v2+)

- [ ] SCORM/xAPI export — explicitly out of scope; large standalone effort
- [ ] Real-time co-editing — out of scope; architectural complexity disproportionate to v1 user base
- [ ] AI image generation — deferred per PROJECT.md; Unsplash integration or URL/upload sufficient
- [ ] Voice cloning — deferred per PROJECT.md; legal and cost risk
- [ ] Talking-head video type — deferred per PROJECT.md; requires recording UX
- [ ] Math (LaTeX) blocks and interactive hotspots — spec section 11; niche use cases
- [ ] Multi-language / translation workflow — separate feature area
- [ ] Per-slide analytics — needs analytics milestone first
- [ ] Course import from PowerPoint/SCORM — spec section 4.1 notes this as "reserve UI placement"; defer to v2

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Course Identity + Structure wizard (Modals 1A/1B) | HIGH | LOW | P1 |
| Module Detail with AI description | HIGH | MEDIUM | P1 |
| Video Detail with AI slide outline generation | HIGH | HIGH | P1 |
| Slide Editor (canvas, blocks, narration) | HIGH | HIGH | P1 |
| Slide Builder (thumbnail strip, ordering) | HIGH | MEDIUM | P1 |
| Quiz Builder with AI question generation | HIGH | HIGH | P1 |
| Module Overview (unified reorder/insert) | HIGH | MEDIUM | P1 |
| Autosave throughout | HIGH | MEDIUM | P1 |
| Preview mode | HIGH | MEDIUM | P1 |
| Publish flow with validation checklist | HIGH | MEDIUM | P1 |
| Draft/published state machine | HIGH | LOW | P1 |
| AI TTS voiceover generation | HIGH | HIGH | P2 |
| AI suggestions right rail | MEDIUM | MEDIUM | P2 |
| Version history on publish update | MEDIUM | MEDIUM | P2 |
| Drag-match / fill-blank question types | MEDIUM | MEDIUM | P2 |
| Module unlock scheduling | MEDIUM | LOW | P2 |
| Scheduled publish | LOW | LOW | P3 |
| Learning objective → quiz question linkage analytics | LOW | LOW | P3 |
| PowerPoint import | LOW | HIGH | P3 |

---

## Competitor Feature Analysis

Researched against Teachable, Thinkific, Articulate Rise 360, and Mindsmith (AI-native).

| Feature | Teachable | Thinkific | Articulate Rise 360 | Our Approach |
|---------|-----------|-----------|---------------------|--------------|
| AI course outline generation | Yes, gated behind $189/mo Growth plan | Yes, included in core plans | Limited | AI-first, not gated; tone preset is novel |
| Slide/block-based editing | No (video + text only) | No (video + text only) | Yes, block-based | Full drag-drop canvas with snap-to-grid |
| AI narration script | No | No | No | Per-slide generation from content blocks |
| AI TTS voiceover | No | No | No (Storyline 360 has limited TTS) | Integrated per-video bulk generation |
| Document to course | Basic text extraction | No | No | Full PDF/DOCX → module/slide structure |
| Quiz AI generation | No | No | No | From module content or from objective |
| Preview mode | Yes | Yes | Yes | Yes, with draft watermark |
| Version history | No (basic) | No | No | Full version on publish, learner progress preserved |
| Module unlock rules | No | Limited | No | Immediate / after_previous / scheduled_days |
| SCORM export | No | Yes (Plus plans) | Yes | Deliberately excluded v1 |
| Real-time co-editing | No | No | No | Deliberately excluded v1 |

The spec positions this platform well ahead of Teachable/Thinkific on authoring depth, and competitive with (and in some respects beyond) Articulate Rise 360 on the AI assistance layer.

---

## User Flow Notes Per Feature Group

These are not in the template but are essential context for the roadmap — they describe where user flows are linear vs where they branch.

**Course creation flow (linear, one-time per course):**
Modal 1A → Modal 1B → Course Builder. Creator returns to Course Builder as home base between all deeper edits. This flow must feel lightweight; two modals is the right pattern.

**Module editing flow (iterative, per module):**
Course Builder → Module Detail → edit identity → done. Or: Module Detail → Video Detail → Slide Builder → Slide Editor → back to Slide Builder → back to Module Detail. Breadcrumb navigation is essential; creators get deep in the hierarchy.

**AI generation flow (consistent pattern across all screens):**
Open drawer → choose source (prompt or document) → configure → generate (streaming) → review output → accept / edit then accept / regenerate / discard. This pattern is used in at least 6 places and must be implemented as a reusable component (SideDrawer + StreamingTextOutput).

**Quiz building flow (non-linear, question by question):**
Open Quiz Builder → set settings → add questions one by one or AI-generate batch → review each AI question → accept/edit/reject → set correct answers → done. The batch AI generation then individual review is the high-value path.

**Publish flow (linear gate, one action):**
Click Publish → see pre-flight checklist → fix any blocking issues (each links to the correct screen) → return to checklist → publish. Must not be dismissible if there are blocking failures.

---

## Sources

- [AI Course Creator vs. Traditional Platform (ddiy.co)](https://ddiy.co/ai-course-creator-vs-traditional-platform/) — market landscape, competitor feature sets [MEDIUM confidence]
- [Best AI Course Creator comparison 2026 (ddiy.co)](https://ddiy.co/best-ai-course-creator/) — feature matrix across platforms [MEDIUM confidence]
- [Teachable vs. Thinkific detailed comparison (learningrevolution.net)](https://www.learningrevolution.net/teachable-vs-thinkific/) — pricing and feature gates [MEDIUM confidence]
- [Top 15 AI-Powered LMS in 2026 (thinkific.com)](https://www.thinkific.com/blog/ai-lms/) — what's now standard in AI-LMS [MEDIUM confidence]
- [ElevenLabs for online learning (profilelearning.com)](https://profilelearning.com/from-narration-to-conversation-how-elevenlabs-elevates-ai-speech-for-online-learning/) — TTS integration patterns in LMS [MEDIUM confidence]
- [eLearning Authoring Tools comparison (mindsmith.ai)](https://www.mindsmith.ai/blog/top-10-elearning-authoring-tools-for-2025) — Articulate Rise 360, Mindsmith, drag-drop UX patterns [MEDIUM confidence]
- [Document Ingestion AI Processing Guide (extend.ai)](https://www.extend.ai/resources/document-ingestion-ai-processing-guide) — chunking and extraction best practices [MEDIUM confidence]
- [Course Authoring Best Practices 2025 (eleapsoftware.com)](https://www.eleapsoftware.com/glossary/course-authoring-guide-2025-tools-and-best-practices/) — common pitfalls including content overload [MEDIUM confidence]
- `LMS platform/AI_COURSE_BUILDER_SPEC.md` — primary source; all spec-aligned findings are HIGH confidence
- `LMS Platform/.planning/PROJECT.md` — project constraints and out-of-scope decisions [HIGH confidence]

---

*Feature research for: AI course authoring platform (creator-side)*
*Researched: 2026-05-08*
