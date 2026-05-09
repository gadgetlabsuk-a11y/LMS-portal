# Phase 12: Course Identity & Structure - Research

**Researched:** 2026-05-09
**Domain:** React modals, SSE streaming, FastAPI course identity API, structure scaffolding
**Confidence:** HIGH

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| COURSE-01 | Creator can create a course via Modal 1A (title, description, audience level, AI tone preset, up to 5 learning objectives) | Existing POST /api/courses must be extended with new Phase 10 columns; all Modal components are already in common/ |
| COURSE-02 | Creator can generate a course description via AI from topic (streaming) | No SSE pattern exists yet in this codebase; must build first SSE endpoint in courses.py using FastAPI StreamingResponse + sse-starlette; client uses fetch + ReadableStream |
| COURSE-03 | Creator can generate learning objectives via AI from course title/description (streaming) | Same SSE pattern as COURSE-02; second endpoint for objectives generation |
| COURSE-04 | Creator sees Course Structure wizard (Modal 1B) with module/video/quiz count inputs and live skeleton tree preview | Pure client-side: number inputs drive a computed tree, no API call until confirmation |
| COURSE-05 | Creator can confirm structure and have empty modules/videos scaffolded automatically | Sequential POST /api/modules + POST /api/videos calls from frontend using existing Phase 11 endpoints |
</phase_requirements>

---

## Summary

Phase 12 is the first creator-facing UI phase. It introduces two modals (Modal 1A: course identity; Modal 1B: structure wizard) on the `/creator/courses` page, which currently uses the admin `CourseManagementPage`. The existing course creation flow only saves `title` and `description`; Phase 12 must extend it to save the full set of Phase 10 identity columns (`audience_level`, `learning_objectives`, `ai_tone_preset`, `ai_custom_prompt`). All seven common components (Modal, Button, Card, Badge, Input, Select, Textarea) already exist and are import-ready.

SSE streaming does not yet exist in this codebase. The `ClaudeService` in `backend/services/claude_service.py` currently calls Claude synchronously with `httpx` and `max_tokens=8192` in one shot. Phase 12 must introduce the first streaming endpoint(s) (POST `/api/courses/ai/generate-description` and POST `/api/courses/ai/generate-objectives`) using `sse-starlette`, FastAPI's `StreamingResponse`, and Anthropic's streaming API. The client-side pattern is `fetch` + `ReadableStream` (not `EventSource`) as specified in AI-01. `sse-starlette` is not yet in `requirements.txt` and must be added.

The Modal 1B skeleton preview is entirely client-side: number inputs for module count and videos-per-module compute a synthetic tree array which renders immediately on every keystroke. No API call happens until the creator confirms. Scaffolding then calls the existing Phase 11 `POST /api/modules` and `POST /api/videos` endpoints sequentially.

**Primary recommendation:** Build the SSE streaming infrastructure here (COURSE-02/03) as a direct pattern — not a generic drawer. Phase 15 will refactor it into a reusable `SideDrawer + StreamingTextOutput`. Building it simply now avoids premature abstraction while giving Phase 15 a concrete reference to extract from.

---

## Standard Stack

### Core (already installed)
| Library | Version | Purpose | Status |
|---------|---------|---------|--------|
| React | 18.3.1 | Component rendering | Installed |
| TypeScript | 5.6.2 | Type safety | Installed |
| Tailwind CSS | 3.4.16 | Styling | Installed |
| React Router DOM | 6.28.0 | Navigation, `useNavigate` | Installed |
| FastAPI | 0.104.1 | Backend API | Installed |
| httpx | 0.25.2 | Async HTTP for Claude calls | Installed |

### Must Add
| Library | Version | Purpose | Why Needed |
|---------|---------|---------|------------|
| sse-starlette | 2.x | FastAPI SSE (text/event-stream responses) | Required for COURSE-02/03 streaming; not in requirements.txt |

**Zustand 5 and TanStack Query 5 are NOT installed.** Per the stack decisions in STATE.md, they are planned but not yet added. Phase 12 should defer both — local `useState` is sufficient for two modals. Phase 13 (Course Builder) is the right place to introduce server state caching with TanStack Query.

### Installation
```bash
# Backend only
pip install sse-starlette
# Add to backend/requirements.txt: sse-starlette==2.1.3
```

---

## Architecture Patterns

### Existing Course Creation Flow (what currently exists)

`POST /api/courses` accepts only `{ title, description, status }` via `CourseCreate` Pydantic model. The `CourseManagementPage` simple modal saves exactly those two fields. All Phase 10 columns (`audience_level`, `learning_objectives`, `ai_tone_preset`, `ai_custom_prompt`, `summary`) exist on the DB model but are never written by any existing endpoint.

**Modal 1A must extend the existing `POST /api/courses` payload** — the cleanest approach is to expand `CourseCreate` in `courses.py` to accept the new fields (all optional so nothing breaks).

### Recommended File Structure for Phase 12
```
frontend/src/
├── pages/creator/
│   └── CreatorCourseListPage.tsx     # replaces CourseManagementPage for /creator/courses
├── components/course/
│   ├── CourseIdentityModal.tsx        # Modal 1A
│   ├── CourseStructureModal.tsx       # Modal 1B
│   └── SkeletonTreePreview.tsx        # live preview sub-component for Modal 1B

backend/routers/
└── courses.py                         # extend CourseCreate + add 2 SSE endpoints
```

Note: `/creator/courses` currently renders `CourseManagementPage` (same as admin). The cleanest path is to create a `CreatorCourseListPage` that wraps the existing list display and triggers the new modals — avoids modifying the shared admin component.

### Pattern 1: Extending CourseCreate (COURSE-01)

The `CourseCreate` Pydantic model in `courses.py` currently has `title`, `description`, `status`. Add the Phase 10 identity fields as optional:

```python
# Source: backend/routers/courses.py — extend CourseCreate
class CourseCreate(BaseModel):
    title: str
    description: Optional[str] = None
    status: CourseStatus = CourseStatus.DRAFT
    # Phase 12 additions
    audience_level: Optional[str] = None
    learning_objectives: Optional[list] = None  # JSON array of strings, max 5
    ai_tone_preset: Optional[str] = None
    ai_custom_prompt: Optional[str] = None
    summary: Optional[str] = None
```

The `create_course` handler then maps these to the `Course` model columns.

### Pattern 2: SSE Streaming Endpoint (COURSE-02/03)

No SSE exists in the codebase today. The `ClaudeService` must grow a new `stream_text()` method that uses httpx streaming mode and yields text deltas. The router endpoint uses `sse-starlette`'s `EventSourceResponse`.

```python
# Source: sse-starlette docs + Anthropic streaming API docs
from sse_starlette.sse import EventSourceResponse
import asyncio

@router.post("/ai/generate-description")
async def generate_description_stream(
    request: Request,
    body: AiDescriptionRequest,
    current_user: User = Depends(require_creator),
):
    async def event_generator():
        async for token in claude_service.stream_description(body.topic, body.tone_preset):
            if await request.is_disconnected():
                break
            yield {"data": token}
    return EventSourceResponse(event_generator())
```

**Critical:** `await request.is_disconnected()` must be called on every `yield` (Known Pitfall #4 from STATE.md). This prevents orphaned Claude API tokens.

### Pattern 3: Client-side SSE Consumption (fetch + ReadableStream)

The client must use `fetch` with `ReadableStream`, NOT `EventSource`. `EventSource` does not support POST or auth headers.

```typescript
// Source: MDN ReadableStream + project convention (AI-01)
const streamGenerate = async (
  endpoint: string,
  body: object,
  onToken: (token: string) => void,
  signal: AbortSignal
) => {
  const res = await fetch(`${API_BASE}/api${endpoint}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${localStorage.getItem('token')}`,
    },
    body: JSON.stringify(body),
    signal,
  })
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  const reader = res.body!.getReader()
  const decoder = new TextDecoder()
  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    const text = decoder.decode(value)
    // SSE lines: "data: token\n\n"
    const lines = text.split('\n')
    for (const line of lines) {
      if (line.startsWith('data: ')) {
        onToken(line.slice(6))
      }
    }
  }
}
```

`AbortController` + `signal` allows cancellation when the modal closes mid-stream.

### Pattern 4: Modal 1B Skeleton Tree Preview (COURSE-04)

The preview is purely derived from number inputs — no API call:

```typescript
// client-side computation from controlled inputs
interface StructureInputs {
  moduleCount: number
  videosPerModule: number
  quizPerModule: boolean  // or a count
}

const buildSkeletonTree = (inputs: StructureInputs): SkeletonNode[] => {
  return Array.from({ length: inputs.moduleCount }, (_, mi) => ({
    type: 'module' as const,
    label: `Module ${mi + 1}`,
    children: [
      ...Array.from({ length: inputs.videosPerModule }, (_, vi) => ({
        type: 'video' as const,
        label: `Video ${vi + 1}`,
      })),
      ...(inputs.quizPerModule ? [{ type: 'quiz' as const, label: 'Quiz' }] : []),
    ],
  }))
}
```

The tree re-renders on every `onChange` with no debounce needed — computation is O(modules * videos), trivially fast.

### Pattern 5: Structure Scaffolding (COURSE-05)

After creator confirms Modal 1B, the frontend calls the Phase 11 endpoints sequentially:

```typescript
const scaffoldStructure = async (courseId: number, inputs: StructureInputs) => {
  for (let mi = 0; mi < inputs.moduleCount; mi++) {
    const modRes = await api.post(`/courses/${courseId}/modules`, {
      title: `Module ${mi + 1}`,
      status: 'draft',
    })
    if (!modRes.ok) throw new Error('Module creation failed')
    const module = await modRes.json()

    for (let vi = 0; vi < inputs.videosPerModule; vi++) {
      await api.post(`/modules/${module.id}/videos`, {
        title: `Video ${vi + 1}`,
        status: 'draft',
      })
    }
    if (inputs.quizPerModule) {
      await api.post(`/modules/${module.id}/quizzes`, {
        title: `Quiz ${mi + 1}`,
        pass_rate: 80,
        attempts_allowed: 3,
      })
    }
  }
}
```

After scaffolding completes, navigate to `/creator/courses/:id/builder` (Course Builder, Phase 13).

### Anti-Patterns to Avoid

- **Using EventSource for SSE:** EventSource is GET-only, cannot send JSON body or auth headers. Always use `fetch + ReadableStream` for POST-based SSE.
- **Storing SSE accumulation in the server:** The stream endpoint should be stateless — yield tokens, do not cache or store generated text. The client is responsible for accumulating and writing to the field on confirmation.
- **Calling scaffolding in parallel (Promise.all) across modules:** Module `order_index` is set server-side as `(count of existing modules)`. Sequential calls guarantee correct order. Parallel calls may produce `order_index` drift.
- **Modifying CourseManagementPage directly:** That component is shared with `/admin/courses`. Create a new `CreatorCourseListPage` to avoid breaking the admin view.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| SSE text/event-stream response | Custom generator with raw `\n\n` framing | `sse-starlette` `EventSourceResponse` | Handles reconnect headers, keep-alive, and correct framing automatically |
| ReadableStream decoding | Byte-level buffer management | `TextDecoder` + chunk split on `\n` | TextDecoder handles multi-byte UTF-8 correctly across chunk boundaries |
| Learning objectives UI | Custom drag-reorder list | Simple `useState` array with add/remove buttons (max 5) | Drag-reorder (dnd-kit) is Phase 13+ overkill; simple index-based CRUD suffices for 5 items |

---

## Common Pitfalls

### Pitfall 1: SSE Orphaned Token Generation
**What goes wrong:** Browser closes the tab or creator closes the modal mid-stream. The FastAPI generator keeps running and consuming Claude API tokens.
**Why it happens:** FastAPI generators do not automatically detect client disconnection without an explicit check.
**How to avoid:** Call `await request.is_disconnected()` on every `yield` inside the generator. This is confirmed in STATE.md Known Pitfall #4.
**Warning signs:** Claude API costs higher than expected; streams that run to completion even after modal close.

### Pitfall 2: learning_objectives JSON Shape Mismatch
**What goes wrong:** Frontend sends objectives as `["obj1", "obj2"]` but backend or DB stores as `{"items": [...]}` or vice versa.
**Why it happens:** The `Course.learning_objectives` column is `JSON` (no schema enforcement). The `Module.learning_objectives` column is also `JSON list`. Both should be `list[str]` but nothing enforces it.
**How to avoid:** Define explicitly in the `CourseCreate` Pydantic schema as `Optional[List[str]]` with `max_length=5` validation. On the frontend, always pass `string[]`.

### Pitfall 3: Route Conflict — /api/courses/ai/generate-description vs /api/courses/{course_id}
**What goes wrong:** FastAPI route matching matches `/api/courses/ai/generate-description` as `course_id = "ai"` and hits the `GET /{course_id}` handler.
**Why it happens:** FastAPI matches routes in declaration order. String path segments match `{course_id: int}` only if they can be coerced to int, but `str` typed `{course_id}` would match "ai".
**How to avoid:** Declare the specific `/ai/...` routes BEFORE the `/{course_id}` routes in `courses.py`. Since `course_id` is typed `int`, FastAPI will correctly reject "ai" and fall through — but ordering still matters for clarity. Verify via `/docs`.
**Warning signs:** 422 Unprocessable Entity or 404 on the AI endpoint in production.

### Pitfall 4: Modal 1B quiz scaffolding — Quiz model field names
**What goes wrong:** Scaffolding POST to `/api/modules/{id}/quizzes` with wrong field names (`pass_score` instead of `pass_rate`, `max_attempts` instead of `attempts_allowed`).
**Why it happens:** STATE.md Decisions from 11-03: "pass_rate and attempts_allowed naming confirmed throughout (not pass_score/max_attempts)".
**How to avoid:** Use `pass_rate` and `attempts_allowed` in all quiz creation payloads.

### Pitfall 5: Sequential scaffolding UX
**What goes wrong:** Creator clicks "Confirm Structure" for 5 modules x 3 videos = 15 API calls. With no loading state, creator double-clicks.
**How to avoid:** Disable the confirm button immediately on first click, show a spinner. Re-enable only if the sequence fails.

---

## Code Examples

### Modal 1A — Learning Objectives (up to 5, add/remove)
```typescript
// Pattern: controlled array, max 5
const [objectives, setObjectives] = useState<string[]>([''])

const addObjective = () => {
  if (objectives.length < 5) setObjectives([...objectives, ''])
}
const removeObjective = (i: number) => {
  setObjectives(objectives.filter((_, idx) => idx !== i))
}
const updateObjective = (i: number, val: string) => {
  setObjectives(objectives.map((o, idx) => idx === i ? val : o))
}

// On save, filter empty strings before sending:
const payload = { ...formData, learning_objectives: objectives.filter(Boolean) }
```

### Backend SSE Endpoint (sse-starlette pattern)
```python
# Source: sse-starlette docs
from sse_starlette.sse import EventSourceResponse

@router.post("/ai/generate-description")
async def generate_description_stream(
    request: Request,
    body: AiDescriptionRequest,
    current_user: User = Depends(require_creator),
):
    async def generator():
        async for token in claude_service.stream_text(body.topic, body.tone_preset):
            if await request.is_disconnected():
                break
            yield {"data": token}
    return EventSourceResponse(generator())
```

### ClaudeService streaming method
```python
# Uses httpx streaming mode with Anthropic's stream=True parameter
async def stream_text(self, prompt: str, tone: Optional[str] = None):
    headers = {
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
        "x-api-key": self.api_key,
    }
    payload = {
        "model": self.model,
        "max_tokens": 1024,
        "stream": True,
        "messages": [{"role": "user", "content": prompt}],
    }
    async with httpx.AsyncClient() as client:
        async with client.stream("POST", CLAUDE_API_URL, json=payload, headers=headers, timeout=60.0) as response:
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data = json.loads(line[6:])
                    if data.get("type") == "content_block_delta":
                        yield data["delta"].get("text", "")
```

---

## State of the Art

| Old Approach | Current Approach | Impact |
|--------------|------------------|--------|
| `EventSource` for SSE | `fetch + ReadableStream` (POST-based) | Enables auth headers + JSON body; EventSource is GET-only |
| `httpx` one-shot JSON | `httpx.stream()` async generator | Token-by-token delivery; lower time-to-first-byte |
| Monolith inline `<script>` modal | React `Modal` component (already exists in common/) | Drop-in; no new modal infrastructure needed |

**No deprecated approaches to avoid here** — SSE pattern is being established fresh in Phase 12.

---

## Open Questions

1. **Should the AI generation "write" the field directly, or require the creator to confirm first?**
   - What we know: Phase 15 will introduce a formal `SideDrawer + StreamingTextOutput` pattern.
   - What's unclear: For Phase 12, should the streamed text appear inline in the Textarea as it streams, or in a separate "preview" area the creator then accepts?
   - Recommendation: Stream directly into the Textarea field (simpler, no confirmation step needed for description/objectives). Creator can edit after generation. Phase 15 formalises this into a drawer for more complex cases.

2. **Creator Course List page vs shared CourseManagementPage?**
   - What we know: `/creator/courses` currently renders `CourseManagementPage` — same component as `/admin/courses`. The admin version does not need Modal 1A/1B.
   - Recommendation: Create `CreatorCourseListPage.tsx` that includes the course list (reuse list logic) and opens Modal 1A/1B. Do not modify `CourseManagementPage` to avoid admin regression.

3. **Does the creator navigate to Course Builder (/creator/courses/:id/builder) after Modal 1B, or stay on the list?**
   - What we know: Success criteria says "navigate to Course Builder with the empty modules and videos already scaffolded". Phase 13 builds the Course Builder. Phase 12 should navigate to that route even though the page doesn't exist yet (it will just 404 gracefully until Phase 13).
   - Recommendation: Navigate to `/creator/courses/:id/builder` on completion. Add the route stub in App.tsx now so it's wired but renders a "Coming Soon" placeholder.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (backend) + vitest (frontend) |
| Config file | `backend/pytest.ini` or inline; `frontend/vitest.config.ts` |
| Quick run command | `cd backend && python -m pytest tests/ -x -q` |
| Full suite command | `cd backend && python -m pytest tests/ && cd ../frontend && npm run test:unit` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| COURSE-01 | POST /api/courses saves audience_level, learning_objectives, ai_tone_preset | integration | `pytest tests/test_courses_phase12.py::test_create_course_with_identity -x` | Wave 0 |
| COURSE-02 | POST /api/courses/ai/generate-description returns SSE text/event-stream | integration | `pytest tests/test_courses_phase12.py::test_generate_description_sse -x` | Wave 0 |
| COURSE-03 | POST /api/courses/ai/generate-objectives returns SSE text/event-stream | integration | `pytest tests/test_courses_phase12.py::test_generate_objectives_sse -x` | Wave 0 |
| COURSE-04 | Skeleton tree preview updates on input change (client-side) | unit | `npm run test:unit -- SkeletonTreePreview` | Wave 0 |
| COURSE-05 | Scaffolding calls create expected modules + videos | integration | `pytest tests/test_courses_phase12.py::test_scaffold_structure -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `cd backend && python -m pytest tests/ -x -q`
- **Per wave merge:** Full backend + frontend suite
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `backend/tests/test_courses_phase12.py` — covers COURSE-01, COURSE-02, COURSE-03, COURSE-05
- [ ] `frontend/src/components/course/SkeletonTreePreview.test.tsx` — covers COURSE-04
- [ ] `pip install sse-starlette` — add to requirements.txt before any streaming test

---

## Sources

### Primary (HIGH confidence)
- Direct codebase inspection: `backend/models/models.py` — Course model columns confirmed
- Direct codebase inspection: `backend/routers/courses.py` — `CourseCreate` schema, endpoint order
- Direct codebase inspection: `backend/services/claude_service.py` — current non-streaming pattern
- Direct codebase inspection: `backend/requirements.txt` — sse-starlette absent, httpx 0.25.2 present
- Direct codebase inspection: `frontend/src/components/common/` — all 7 components verified
- Direct codebase inspection: `frontend/package.json` — Zustand/TanStack Query NOT installed
- Direct codebase inspection: `frontend/src/App.tsx` — current routes, `/creator/courses` confirmed
- Direct codebase inspection: `.planning/STATE.md` — Known Pitfall #4 (is_disconnected), pass_rate naming

### Secondary (MEDIUM confidence)
- sse-starlette docs pattern: EventSourceResponse + async generator is the standard FastAPI SSE approach
- Anthropic streaming API: `stream: true` + `content_block_delta` event type is the established pattern
- MDN ReadableStream: `fetch + ReadableStream` for consuming SSE from JS is documented standard

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — direct package.json and requirements.txt inspection
- Architecture patterns: HIGH — all patterns derived from reading actual codebase files
- Pitfalls: HIGH — Pitfalls 1/4 from STATE.md confirmed; Pitfall 3 from FastAPI routing docs behavior; Pitfall 4 from STATE.md naming decision

**Research date:** 2026-05-09
**Valid until:** 2026-06-09 (stable stack; sse-starlette 2.x API is stable)
