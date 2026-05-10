# Phase 16: Quiz Builder — Research

**Researched:** 2026-05-10
**Domain:** Quiz CRUD UI, question type forms, dnd-kit sortable, SSE AI generation, SideDrawer integration
**Confidence:** HIGH — all findings drawn directly from the existing codebase (Phase 11–15 code)

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| QUIZ-01 | Creator can create a quiz linked to a module with pass score, max attempts, and feedback settings | Backend CRUD fully exists in `quizzes.py`; frontend page and route are the only missing pieces |
| QUIZ-02 | Creator can add MCQ single-answer questions | Question model has `type`, `prompt`, `options` (JSON), `correct_answer` (JSON) — supports MCQ single via type string `"mcq_single"` |
| QUIZ-03 | Creator can add MCQ multi-answer questions | Same columns as QUIZ-02; `correct_answer` is JSON so it can store an array of indices for multi-answer |
| QUIZ-04 | Creator can add true/false questions | Same model; type `"true_false"`; options always `["True", "False"]`; correct_answer is `"True"` or `"False"` |
| QUIZ-05 | Creator can add short answer questions | type `"short_answer"`; no options needed; correct_answer is a string pattern or null (manual grading) |
| QUIZ-06 | Creator can add explanation text per question | `explanation` column (Text, nullable) already exists on Question model |
| QUIZ-07 | Creator can reorder questions via drag-and-drop with no order_index drift | `POST /api/quizzes/{quiz_id}/questions/reorder` already exists; dnd-kit sortable pattern proven in VideoSlideStrip |
| QUIZ-08 | Creator can generate a batch of questions via AI from module content (streaming) | New SSE endpoint needed in `quizzes.py`; useSSEStream + SideDrawer pattern proven in Phase 15 |
</phase_requirements>

---

## Summary

Phase 16 is primarily a frontend build phase. The entire backend layer (Quiz CRUD, Question CRUD, question reorder endpoint) was delivered in Phase 11 (`backend/routers/quizzes.py`) and requires only one new addition: an SSE endpoint for AI question generation (QUIZ-08). The data model is fully live — `Quiz` and `Question` tables with all required columns exist in `backend/models/models.py`.

On the frontend, a `QuizBuilderPage` must be built and wired at `/creator/courses/:id/quizzes/:quizId`. The page handles quiz settings (QUIZ-01), a question list with type-specific forms (QUIZ-02 through QUIZ-06), dnd-kit drag-to-reorder (QUIZ-07), and an AI generation SideDrawer (QUIZ-08). All patterns needed — dnd-kit sortable, useSSEStream, SideDrawer + StreamingTextOutput — are battle-tested across Phases 13–15.

The AI question generation surface follows the SideDrawer mandate from AI-02 (Phase 15). The AI response streams JSON representing a batch of questions; the client accumulates all tokens into a buffer ref (same pattern as SlideOutlineWizard), parses on completion, shows a preview, and lets the creator confirm before writing to the API.

**Primary recommendation:** No new library installs required. Reuse dnd-kit (already installed), useSSEStream (already exists), SideDrawer + StreamingTextOutput (already exist). Backend only needs one new SSE endpoint. Frontend needs QuizBuilderPage, question type sub-components, drag list, and AI drawer.

---

## Standard Stack

### Core (all already installed — no new installs for this phase)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| @dnd-kit/core + @dnd-kit/sortable | installed Phase 13 | Question drag-to-reorder | Same pattern as VideoSlideStrip and SortableModuleRow |
| useSSEStream | frontend/src/hooks/useSSEStream.ts | AI streaming | Single SSE hook for the whole platform (AI-01) |
| SideDrawer | frontend/src/components/ai/SideDrawer.tsx | AI generation drawer | AI-02 mandate: all AI surfaces use SideDrawer |
| StreamingTextOutput | frontend/src/components/ai/StreamingTextOutput.tsx | Streamed text display inside drawer | Paired with SideDrawer on all generation surfaces |
| sse-starlette 2.x | backend requirements.txt | Backend SSE response | Platform standard for SSE endpoints |
| ClaudeService._stream_text() | backend/services/claude_service.py | Streams AI tokens | Platform standard; all SSE endpoints call this |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| React local state (useState) | React 18.3 | Quiz + question state | No Zustand needed — quiz builder is simpler than slide editor; no undo/redo |
| @/components/common/* | project | Button, Input, Textarea, Select | Standard UI components with spread `...props` for data-testid pass-through |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Local state for quiz builder | Zustand store | Zustand adds no value here — there's no undo/redo, no cross-page state sharing. Local state is simpler and consistent with ModuleDetailPage approach. |
| SideDrawer for AI generation | Inline streaming panel | AI-02 requires SideDrawer on all generation surfaces. Only SlideOutlineWizard has a documented exception, and that's because it's a multi-step wizard structure. |

**Installation:** None required. All dependencies installed in previous phases.

---

## Architecture Patterns

### Recommended Project Structure

```
frontend/src/pages/creator/
├── QuizBuilderPage.tsx          # New — route target for /creator/courses/:id/quizzes/:quizId
├── __tests__/
│   └── QuizBuilderPage.test.tsx # New — Wave 0 RED stub

frontend/src/components/quiz/
├── QuestionForm.tsx             # New — type-switching form for all 4 question types
├── SortableQuestionRow.tsx      # New — dnd-kit sortable wrapper around QuestionForm
├── __tests__/
│   └── QuestionForm.test.tsx    # New — Wave 0 RED stub

backend/routers/
└── quizzes.py                   # Exists — add new SSE endpoint for QUIZ-08

backend/tests/
└── test_quiz_phase16.py         # New — Wave 0 RED stubs, then SSE test
```

### Pattern 1: dnd-kit Sortable Question List

**What:** `DndContext` + `SortableContext` wrapping `SortableQuestionRow` items; `arrayMove` on `onDragEnd`; optimistic update then `POST /api/quizzes/{quizId}/questions/reorder`.
**When to use:** QUIZ-07 — reorder questions in the QuizBuilderPage question list.
**Example (directly from VideoSlideStrip.tsx):**

```typescript
// Source: frontend/src/components/slide/VideoSlideStrip.tsx — exact pattern to replicate
const handleDragEnd = async (event: DragEndEvent) => {
  const { active, over } = event
  if (!over || active.id === over.id) return
  const oldIndex = questions.findIndex((q) => q.id === active.id)
  const newIndex = questions.findIndex((q) => q.id === over.id)
  const newOrder = arrayMove(questions, oldIndex, newIndex)
  setQuestions(newOrder)                        // optimistic update
  await api.post(`/quizzes/${quizId}/questions/reorder`, {
    question_ids: newOrder.map((q) => q.id),
  })
}
```

Key detail: use `id` directly (integers) as sortable items — not `question-${q.id}` string keys. VideoSlideStrip uses raw integer IDs; ModuleOverviewList uses prefixed strings because it has mixed module/video types in the same context. Questions are homogenous so raw integer IDs are fine.

### Pattern 2: Type-Switching Question Form

**What:** A single `QuestionForm` component that renders different input fields based on `question.type`. The four types map to different UI shapes:

```typescript
// Type shapes for the 4 question types
type QuestionType = 'mcq_single' | 'mcq_multi' | 'true_false' | 'short_answer'

// MCQ single: prompt + 2-5 options (strings) + one correct index
// MCQ multi: prompt + 2-5 options (strings) + array of correct indices
// True/False: prompt only; options fixed as ["True", "False"]; correct_answer "True"|"False"
// Short answer: prompt only; correct_answer is a string or null
```

**When to use:** Any time a question is added or edited.
**Note:** Store options as `string[]` in the Question's `options` JSON column. Store `correct_answer` as JSON — an integer index for mcq_single, an integer array for mcq_multi, a string for true_false and short_answer.

### Pattern 3: SSE AI Question Generation (QUIZ-08)

**What:** Backend SSE endpoint streams JSON question batch; frontend SideDrawer accumulates tokens into `bufferRef`, parses on completion, shows preview batch, creator confirms each.
**When to use:** AI Generate Questions button in QuizBuilderPage.

Backend endpoint — mirrors `POST /api/slides/{slide_id}/ai/generate-outline` pattern from slides.py:

```python
# Source: backend/routers/slides.py SSE pattern + quizzes.py structure
@router.post("/api/quizzes/{quiz_id}/ai/generate-questions")
async def generate_questions(
    quiz_id: int,
    body: AiQuestionRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_creator),
):
    quiz = _get_quiz_or_404(quiz_id, db, current_user)
    # Fetch module content for context
    module = quiz.module
    prompt = (
        f"Generate {body.count} quiz questions for a module titled '{module.title}'. "
        f"Module description: {module.description or 'none'}. "
        f"Return ONLY a JSON array of question objects with keys: "
        f"type (mcq_single|mcq_multi|true_false|short_answer), prompt, options (array or null), "
        f"correct_answer (int|int[]|string), explanation. "
        f"Tone: {body.tone_preset}."
    )

    async def event_generator():
        async for token in claude_service._stream_text(prompt):
            if await request.is_disconnected():
                break
            yield {"data": token}

    return EventSourceResponse(event_generator())
```

CRITICAL: Declare this route BEFORE `GET /api/quizzes/{quiz_id}` in the router. FastAPI path-order collision prevention — same rule as slides.py (STATE.md decision from 14-02).

Frontend — accumulate into bufferRef, parse only on stream completion (same as SlideOutlineWizard):

```typescript
// Source: frontend/src/components/slide/SlideOutlineWizard.tsx — bufferRef pattern
const bufferRef = useRef('')
const { startStream, isStreaming } = useSSEStream()

const handleGenerate = async () => {
  bufferRef.current = ''
  await startStream({
    url: `/api/quizzes/${quizId}/ai/generate-questions`,
    body: { count: 5, tone_preset: tonePreset },
    onToken: (t) => { bufferRef.current += t },
  })
  const parsed: GeneratedQuestion[] = JSON.parse(bufferRef.current)
  setPendingQuestions(parsed)
}
```

### Pattern 4: SideDrawer Integration (AI-02 compliance)

**What:** QuizBuilderPage has an "AI Generate" button that opens a SideDrawer containing a form (question count, tone) and the AI results review UI.
**When to use:** QUIZ-08 — all AI surfaces must use SideDrawer per AI-02 mandate.

```typescript
// Source: frontend/src/pages/creator/ModuleDetailPage.tsx — SideDrawer pattern
const [aiDrawerOpen, setAiDrawerOpen] = useState(false)

// In render:
<>
  <Button onClick={() => setAiDrawerOpen(true)}>Generate Questions with AI</Button>
  <SideDrawer
    isOpen={aiDrawerOpen}
    onClose={() => setAiDrawerOpen(false)}
    title="AI Question Generator"
  >
    {/* question count selector, tone selector, generate button, pending questions preview */}
  </SideDrawer>
</>
```

Note on SideDrawer z-index: z-[55] overlay / z-[60] panel. These values are already in SideDrawer.tsx. No change needed unless QuizBuilderPage opens inside a Modal (it doesn't — it's a full page).

### Pattern 5: Quiz Settings Form (QUIZ-01)

**What:** The QuizBuilderPage top section shows quiz metadata — title, pass_rate, attempts_allowed, show_feedback — with a save button that calls `PUT /api/quizzes/{quizId}`.

Column name mapping (confirmed from models.py and quizzes.py):
- `pass_rate` (integer, default 80) — the "pass score" requirement in QUIZ-01
- `attempts_allowed` (integer, default 3) — "max attempts" in QUIZ-01
- `show_feedback` (string: "immediate" | "on_completion" | "never") — "feedback settings" in QUIZ-01

### Anti-Patterns to Avoid

- **Zustand for quiz builder state:** No undo/redo, no cross-page state. Local `useState` is correct.
- **Nested DndContext for question reorder:** There's only one list, so a single DndContext is sufficient. Don't use the prefixed-ID pattern from ModuleOverviewList (that was needed for mixed types).
- **Partial JSON parse during streaming:** Always accumulate full response in `bufferRef.current`, parse only after `startStream` resolves. Streaming partial JSON will throw.
- **Declaring SSE route after the quiz GET route:** FastAPI uses declaration order for path matching. `POST /api/quizzes/{quiz_id}/ai/generate-questions` must appear before `GET /api/quizzes/{quiz_id}` in quizzes.py.
- **Separate DndContext per question:** Questions are a single flat list — one DndContext, one SortableContext is correct.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Drag-to-reorder question list | Custom drag handlers with mousedown/mousemove | `@dnd-kit/sortable` + `useSortable` | Keyboard accessibility, pointer/touch support, scroll container handling — all free |
| SSE streaming from client | Custom fetch loop | `useSSEStream` hook | AbortController, error handling, state management already solved |
| AI generation drawer | Inline streaming panel | `SideDrawer` + `StreamingTextOutput` | AI-02 compliance; z-index handling pre-solved |
| Atomic reorder | Multiple individual PUT calls | `POST /quizzes/{id}/questions/reorder` | Already implemented; single transaction prevents order_index drift |
| JSON parsing of streamed AI output | Line-by-line incremental JSON parsing | Buffer-then-parse pattern | Partial JSON throws; buffer everything in `bufferRef.current`, parse after stream completes |

**Key insight:** Every building block needed for Phase 16 exists in the codebase. The implementation task is wiring known patterns in a new context, not building new capabilities.

---

## Common Pitfalls

### Pitfall 1: SSE Route Declaration Order in quizzes.py

**What goes wrong:** `POST /api/quizzes/{quiz_id}/ai/generate-questions` is declared after `GET /api/quizzes/{quiz_id}`, causing FastAPI to match the GET route first.
**Why it happens:** FastAPI uses first-match-wins for path patterns. `{quiz_id}` is greedy.
**How to avoid:** Declare the SSE endpoint immediately after the `QuestionReorderRequest` schema, before the quiz GET endpoint. This is the same rule applied in slides.py (STATE.md decision 14-02).
**Warning signs:** 422 Unprocessable Entity on POST to the AI endpoint — FastAPI is trying to parse "ai" as an integer quiz_id.

### Pitfall 2: order_index Drift on Reorder

**What goes wrong:** Rapid drag-reorder calls overlap; the second call returns before the first, leaving order_indices inconsistent.
**Why it happens:** Non-atomic per-row updates allow interleaving.
**How to avoid:** Always use `POST /api/quizzes/{quiz_id}/questions/reorder` which is already implemented with a single `db.commit()` after the loop. Never call individual `PUT /api/questions/{id}` to update order_index. This is STATE.md pitfall #3.
**Warning signs:** Questions jump back to old positions after page reload.

### Pitfall 3: Partial JSON Parse of Streamed AI Response

**What goes wrong:** `onToken` callback calls `JSON.parse(token)` or parses the accumulating buffer mid-stream, throwing on every token until the final one.
**Why it happens:** Claude streams valid JSON in fragments; each fragment is not itself valid JSON.
**How to avoid:** Use `bufferRef.current += t` in `onToken`, then `JSON.parse(bufferRef.current)` only after `await startStream(...)` resolves. Exact pattern from SlideOutlineWizard.tsx.
**Warning signs:** Console errors showing `SyntaxError: Unexpected token` during generation.

### Pitfall 4: Wave 0 Frontend RED State

**What goes wrong:** Wave 0 frontend test imports an existing file — vitest passes at collection (GREEN), not RED.
**Why it happens:** The test stub needs to import a file that doesn't exist yet to get the correct RED failure.
**How to avoid:** Import the non-existent page/component directly: `import { QuizBuilderPage } from '../QuizBuilderPage'`. This gives `Cannot find module` at vitest collection — correct RED state per STATE.md 14-01 decision.

### Pitfall 5: Wave 0 Backend RED State

**What goes wrong:** Backend test stub uses `assert False` (produces ERROR not FAILED) or imports are correct (test somehow passes).
**Why it happens:** `assert False` raises `AssertionError` which pytest shows as ERROR, not FAILED.
**How to avoid:** Use `pytest.fail("QUIZ-08: not implemented")` directly in test function body — produces FAILED status. Established pattern from STATE.md decisions for Phases 12, 13, 14.

### Pitfall 6: Correct_Answer JSON Shape per Question Type

**What goes wrong:** Saving mcq_multi with `correct_answer: 0` (integer) instead of `correct_answer: [0, 2]` (array), or saving true_false with `correct_answer: 0` instead of `"True"`.
**Why it happens:** The column is `JSON` type — any value is accepted at the DB level.
**How to avoid:** Enforce shape in QuestionForm component logic per type. At form submit time: mcq_single → integer index; mcq_multi → integer array; true_false → string "True" or "False"; short_answer → string or null.

---

## Code Examples

### Backend SSE Endpoint Skeleton

```python
# Source: backend/routers/slides.py lines 174-200 (generate_narration pattern)
# Place BEFORE GET /api/quizzes/{quiz_id} in quizzes.py

class AiQuestionRequest(BaseModel):
    count: Optional[int] = 5
    tone_preset: Optional[str] = "professional"

@router.post("/api/quizzes/{quiz_id}/ai/generate-questions")
async def generate_questions(
    quiz_id: int,
    body: AiQuestionRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_creator),
):
    """Stream AI-generated quiz questions from module content. QUIZ-08."""
    quiz = _get_quiz_or_404(quiz_id, db, current_user)
    module = quiz.module
    prompt = (
        f"Generate {body.count} quiz questions for a module titled '{module.title}'. "
        f"Description: {module.description or 'no description'}. "
        f"Return ONLY a valid JSON array. Each element: "
        f"{{type: 'mcq_single'|'mcq_multi'|'true_false'|'short_answer', "
        f"prompt: string, options: string[]|null, correct_answer: int|int[]|string|null, "
        f"explanation: string}}. Tone: {body.tone_preset}."
    )

    async def event_generator():
        async for token in claude_service._stream_text(prompt):
            if await request.is_disconnected():
                break
            yield {"data": token}

    return EventSourceResponse(event_generator())
```

### Frontend App.tsx Route Addition

```typescript
// Source: frontend/src/App.tsx — matches existing creator route pattern
<Route
  path="/creator/courses/:id/quizzes/:quizId"
  element={
    <CreatorLayout>
      <ProtectedRoute creatorRoute>
        <QuizBuilderPage />
      </ProtectedRoute>
    </CreatorLayout>
  }
/>
```

### CourseTreeRail Navigation to Quiz

The `CourseTreeRail` already lists quizzes in the tree (it receives `quizzes` prop). Currently quizzes in the tree are non-navigable stubs. Phase 16 should add navigation:

```typescript
// In CourseTreeRail.tsx — add onClick to quiz tree items
navigate(`/creator/courses/${courseId}/quizzes/${quiz.id}`)
```

### dnd-kit Sensors for Question List

```typescript
// Source: frontend/src/components/slide/VideoSlideStrip.tsx lines 103-105
const sensors = useSensors(useSensor(PointerSensor), useSensor(KeyboardSensor))
// Note: VideoSlideStrip uses plain sensors without activationConstraint.
// For question rows (which have form inputs), add distance constraint to
// prevent accidental drags when clicking into input fields:
const sensors = useSensors(
  useSensor(PointerSensor, { activationConstraint: { distance: 8 } }),
  useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }),
)
// This mirrors the ModuleOverviewList pattern (STATE.md 13-03).
```

### Backend Test SSE Pattern

```python
# Source: backend/tests/test_slides_phase14.py lines 47-65
@pytest.fixture(autouse=True)
def reset_sse_state():
    from sse_starlette.sse import AppStatus
    AppStatus.should_exit_event = None
    yield

def test_generate_questions_streams_tokens(creator_token, creator_quiz):
    mock_tokens = ["[", '{"type":"mcq_single","prompt":"Q?"}', "]"]

    async def mock_stream(prompt):
        for token in mock_tokens:
            yield token

    with patch("routers.quizzes.claude_service._stream_text", side_effect=mock_stream):
        res = client.post(
            f"/api/quizzes/{creator_quiz['id']}/ai/generate-questions",
            json={"count": 1, "tone_preset": "professional"},
            headers={"Authorization": f"Bearer {creator_token}"},
        )
    assert res.status_code == 200
    assert "data:" in res.text
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Ad-hoc inline streaming | useSSEStream + SideDrawer | Phase 15 | All AI surfaces now standardised; quiz AI must follow same pattern |
| Quizzes listed but not navigable in tree | Phase 16 adds QuizBuilderPage route | Phase 16 | CourseTreeRail quiz items need onClick wiring to new route |
| Quiz rows shown as non-draggable in ModuleOverviewList | Phase 16 — quiz row in ModuleOverviewList can remain non-draggable at module level; questions are draggable within QuizBuilderPage | Phase 16 | No change to ModuleOverviewList needed for reordering; only internal question order uses drag |

**Key column naming note:** STATE.md decision from 11-03 confirms: `pass_rate` and `attempts_allowed` are the actual column names (not `pass_score`/`max_attempts` as REQUIREMENTS.md uses colloquially). This is confirmed in models.py line 377-378 and quizzes.py schemas.

---

## Open Questions

1. **Quiz access from CourseBuilderPage tree**
   - What we know: `CourseTreeRail` already renders quiz items from the `quizzes` prop. It currently has no navigation on click.
   - What's unclear: Does CourseTreeRail need a `navigate` call added to quiz items, or should the quiz be accessed from ModuleDetailPage?
   - Recommendation: Add `navigate` to quiz items in CourseTreeRail — same pattern as module/video items. Route is `/creator/courses/:id/quizzes/:quizId`.

2. **creator_quiz fixture for tests**
   - What we know: conftest.py has `creator_course` but no `creator_quiz` fixture.
   - What's unclear: Whether to add `creator_quiz` to conftest.py or keep it file-local in `test_quiz_phase16.py`.
   - Recommendation: Keep file-local in `test_quiz_phase16.py` (same pattern as `creator_slide` fixture in `test_slides_phase14.py`).

3. **Question form auto-save vs explicit save**
   - What we know: The slide editor has autosave on change. The module detail page uses an explicit "Save" button.
   - What's unclear: Should individual question edits autosave, or should the creator click Save per question?
   - Recommendation: Explicit Save per question (like ModuleDetailPage) — simpler state management, less API chatter, and question forms are discrete submit actions.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (backend), vitest (frontend) |
| Backend config | No pytest.ini — run from `backend/` with venv activated |
| Frontend config | `frontend/vitest.config.ts` — jsdom environment, globals: true |
| Backend quick run | `cd backend && source venv/bin/activate && python -m pytest tests/test_quiz_phase16.py -x` |
| Frontend quick run | `cd frontend && npx vitest run src/pages/creator/__tests__/QuizBuilderPage.test.tsx` |
| Full backend suite | `cd backend && source venv/bin/activate && python -m pytest tests/ -x` |
| Full frontend suite | `cd frontend && npx vitest run` |

### Phase Requirements to Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| QUIZ-01 | Creator creates quiz with pass_rate/attempts_allowed/show_feedback | integration (backend) | `pytest tests/test_quiz_phase16.py::test_create_quiz_settings -x` | Wave 0 |
| QUIZ-01 | QuizBuilderPage renders settings form | unit (frontend) | `vitest run src/pages/creator/__tests__/QuizBuilderPage.test.tsx` | Wave 0 |
| QUIZ-02 | Add MCQ single question with correct answer | integration (backend) + unit (frontend) | `pytest tests/test_quiz_phase16.py::test_create_mcq_single_question -x` | Wave 0 |
| QUIZ-03 | Add MCQ multi question with correct answer array | integration (backend) + unit (frontend) | `pytest tests/test_quiz_phase16.py::test_create_mcq_multi_question -x` | Wave 0 |
| QUIZ-04 | Add true/false question | integration (backend) + unit (frontend) | `pytest tests/test_quiz_phase16.py::test_create_true_false_question -x` | Wave 0 |
| QUIZ-05 | Add short answer question | integration (backend) + unit (frontend) | `pytest tests/test_quiz_phase16.py::test_create_short_answer_question -x` | Wave 0 |
| QUIZ-06 | Explanation text saved and returned | integration (backend) | `pytest tests/test_quiz_phase16.py::test_question_explanation -x` | Wave 0 |
| QUIZ-07 | Question reorder persists, no order_index drift | integration (backend) + unit (frontend) | `pytest tests/test_quiz_phase16.py::test_reorder_questions -x` | Wave 0 |
| QUIZ-08 | AI generation endpoint streams tokens | integration (backend) | `pytest tests/test_quiz_phase16.py::test_generate_questions_streams_tokens -x` | Wave 0 |
| QUIZ-08 | SideDrawer renders in QuizBuilderPage | unit (frontend) | `vitest run src/pages/creator/__tests__/QuizBuilderPage.test.tsx` | Wave 0 |

### Sampling Rate

- **Per task commit:** Run the phase-specific test file only (`test_quiz_phase16.py` or `QuizBuilderPage.test.tsx`)
- **Per wave merge:** Full suite (`pytest tests/` + `vitest run`)
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `backend/tests/test_quiz_phase16.py` — covers QUIZ-01 through QUIZ-08 (Wave 0: `pytest.fail()` stubs)
- [ ] `frontend/src/pages/creator/QuizBuilderPage.tsx` — imports from this file are the Wave 0 RED trigger
- [ ] `frontend/src/pages/creator/__tests__/QuizBuilderPage.test.tsx` — imports non-existent `QuizBuilderPage` for RED state
- [ ] `frontend/src/components/quiz/QuestionForm.tsx` — needed for question type UI
- [ ] `frontend/src/components/quiz/__tests__/QuestionForm.test.tsx` — Wave 0 RED stub importing non-existent QuestionForm

No new packages needed — framework install step is skipped.

---

## Sources

### Primary (HIGH confidence)

- `backend/routers/quizzes.py` — complete Quiz+Question CRUD + reorder endpoint, confirmed column names
- `backend/models/models.py` — Quiz and Question table schemas, confirmed column names (`pass_rate`, `attempts_allowed`, `show_feedback`, `correct_answer` as JSON, `explanation` as Text)
- `frontend/src/components/slide/VideoSlideStrip.tsx` — dnd-kit sortable pattern for flat lists
- `frontend/src/components/builder/ModuleOverviewList.tsx` — dnd-kit with activationConstraint for lists with clickable children
- `frontend/src/hooks/useSSEStream.ts` — SSE streaming hook interface
- `frontend/src/components/ai/SideDrawer.tsx` — SideDrawer props interface and z-index values
- `frontend/src/components/slide/SlideOutlineWizard.tsx` — bufferRef JSON accumulation pattern
- `backend/routers/slides.py` — SSE endpoint pattern + route declaration order rule
- `backend/services/claude_service.py` — `_stream_text()` method signature
- `backend/tests/test_slides_phase14.py` — `reset_sse_state` fixture + SSE mock pattern
- `backend/tests/conftest.py` — `creator_token`, `creator_course`, `creator_user` fixture availability
- `.planning/STATE.md` — confirmed pitfall #3 (order_index drift), decision 14-02 (route order), decision 11-03 (pass_rate/attempts_allowed naming), decisions 15-01 (Wave 0 patterns)

### Secondary (MEDIUM confidence)

- `frontend/src/App.tsx` — confirmed route pattern for new creator page
- `frontend/src/pages/creator/ModuleDetailPage.tsx` — SideDrawer + useSSEStream integration pattern

---

## Metadata

**Confidence breakdown:**
- Backend API layer: HIGH — fully implemented in Phase 11; only one new SSE endpoint needed
- Data model: HIGH — confirmed column names and types from models.py
- dnd-kit pattern: HIGH — directly replicable from VideoSlideStrip
- SSE/AI generation: HIGH — direct reuse of Phase 15 patterns
- Frontend page structure: HIGH — ModuleDetailPage provides the template
- Question type data shapes: HIGH — JSON column supports all four types; shapes defined from REQUIREMENTS.md + model

**Research date:** 2026-05-10
**Valid until:** 2026-06-10 (stable codebase; no fast-moving dependencies)
