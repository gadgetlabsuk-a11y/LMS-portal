# Retrospective

Living retrospective — updated after each milestone.

---

## Milestone: v1.0 — AI Course Builder

**Shipped:** 2026-05-11
**Phases:** 10 (9–18) | **Plans:** 55 | **Commits:** 246

### What Was Built

- Vite + React + TypeScript migration from 3420-line single-file Babel app
- Relational schema (5 Alembic migrations) replacing JSON blobs for all course content
- Full creator authoring: Course Builder, Module Detail, Slide Builder with snap-grid canvas and block library
- SSE streaming AI generation infrastructure with reusable SideDrawer component
- ElevenLabs TTS: per-slide audio and bulk generation with rate limiting and hash caching
- Quiz Builder: 4 question types, drag-to-reorder (dnd-kit), AI question generation
- Preview & Publish: pre-flight checklist, CourseVersion snapshot model, learner enrolment pinning, archive

### What Worked

- **Wave-based parallel execution** — Plans like 17-03 (backend bulk endpoint) and 17-04 (frontend audio player) ran concurrently with zero conflicts because they touched different files. Significant time savings across multiple phases.
- **Plan checker caught regressions before execution** — In Phase 17, the checker caught that `SlideBuilderPage.test.tsx` had an assertion that `bulk-narration-btn` was disabled. This would have broken the test suite before a single line of implementation was written. Prevention is far cheaper than gap closure.
- **TDD wave 0 stubs** — Requiring pytest.fail() stubs before implementation meant every phase started with a clear, runnable RED state. No ambiguity about what "done" meant.
- **bufferRef + parse-on-completion for SSE** — Accumulating all SSE tokens before JSON.parse prevented the mid-stream parse errors that plagued early AI generation attempts. This pattern should be applied universally.
- **Research phase caught pitfalls early** — The Phase 17 researcher flagged that `asyncio.Semaphore(3)` must be module-level (not per-request), and that the legacy `eleven_monolingual_v1` model was deprecated. Both would have caused runtime failures if discovered during execution.

### What Was Inefficient

- **Plan 15-06 gap closure (SideDrawer orphaned)** — SideDrawer was built in Phase 14 but never wired into any production surface. The verifier caught this, but it required a full gap closure cycle. The planner should have included the wiring as part of the original plan rather than treating component creation as "done" before integration.
- **conftest.py fixture isolation (Phase 17 gap)** — The `setup_test_db` autouse fixture called `create_all` without first calling `drop_all`. When pytest randomized test order, this caused `table users already exists` errors. The fix was one line, but the gap closure required two plan checker revision cycles to nail down the correct `db` fixture pattern. The isolation pattern should be documented as a project convention.
- **Plan checker iteration overhead** — Phase 18 plans required 2 revision cycles (PREVIEW-02 quiz interactivity, wave assignment for plan 05). Both were legitimate catches, but the planner consistently underestimated the depth of integration needed for frontend components. More upfront research on existing component reuse would reduce iterations.

### Patterns Established

- **SSE streaming pattern:** `StreamingResponse` + `EventSourceResponse` on backend; `useSSEStream` hook with `bufferRef` accumulation + parse-on-completion on frontend
- **SideDrawer z-index:** `z-[55]` (overlay) + `z-[60]` (panel) to appear above Modal (`z-50`); Fragment wrapper to render outside Modal DOM hierarchy
- **TTS module-level semaphore:** `_bulk_semaphore = asyncio.Semaphore(3)` at module level in `tts_service.py` — never inside a function or endpoint
- **Hash caching pattern:** `hashlib.sha256(script.encode()).hexdigest()` vs stored `narration_script_hash` column — skip if equal
- **dnd-kit sortable pattern:** `PointerSensor` with `activationConstraint: { distance: 8 }` prevents accidental drag on form inputs; `arrayMove` + POST reorder on `onDragEnd`
- **conftest.py isolation:** `drop_all` before `create_all` in `setup_test_db`; `db` fixture wraps test in connection + SAVEPOINT + rollback with `app.dependency_overrides[get_db]` bound to same connection
- **CourseVersion snapshot:** JSON blob (not relational clone) for course versioning; `Enrollment.course_version` pins learner to version at enrolment time

### Key Lessons

1. **Wire components as part of the plan that builds them.** If a plan creates a component, the plan must also add the entry point that uses it. "Component built" ≠ "requirement met".
2. **pytest fixture isolation is a first-class concern.** Every phase test file should use `drop_all` + `create_all` + SAVEPOINT pattern from day one. Add to project CLAUDE.md.
3. **The plan checker's value is proportional to the quality of must_haves.** Weak must_haves ("component exists") produce weak verification. Strong must_haves ("endpoint returns 400 on missing script") catch integration failures.
4. **Research the exact API before writing the plan.** Phase 17's `eleven_flash_v2_5` model and Rachel/Josh voice IDs were confirmed in research — the executor didn't have to guess. This pattern should be standard for any third-party API integration.
5. **SSE route order matters in FastAPI.** POST AI routes must be declared before GET wildcard routes (`GET /{id}`) to avoid shadowing. Document this in CLAUDE.md.

### Cost Observations

- Model mix: primarily `sonnet` for execution; `sonnet` for research, planning, and verification
- Sessions: ~4 extended sessions across 4 days
- Notable: Wave-based parallel execution (phases 17-03/17-04, 18-03 waves) meaningfully reduced wall-clock time compared to strictly sequential execution

---

## Cross-Milestone Trends

| Metric | v0.1 | v1.0 |
|--------|------|------|
| Phases | 8 (manual) | 10 |
| Plans | — | 55 |
| LOC | ~3,420 (single file) | ~21,600 |
| Timeline | — | 4 days |
| Gap closure cycles | — | 2 (Phases 15, 17) |
| Plan checker revisions | — | ~6 across all phases |

**Trend:** Gap closure overhead is ~10% of total execution time. The two gaps (SideDrawer orphaned, conftest fixture isolation) were both integration gaps — component built but not wired, or test infrastructure not isolated. Investing in integration checks during planning would reduce this.
