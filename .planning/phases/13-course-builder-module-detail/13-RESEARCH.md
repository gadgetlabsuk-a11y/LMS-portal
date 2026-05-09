# Phase 13: Course Builder & Module Detail - Research

**Researched:** 2026-05-09
**Domain:** React SPA authoring UI — left-rail tree navigation, dnd-kit sortable, SSE streaming, module form editing
**Confidence:** HIGH

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| BUILD-01 | Creator sees Course Builder with left-rail tree (modules, videos, quizzes) and module card list | API: GET /api/courses/:id/modules + GET /api/modules/:id/videos + GET /api/modules/:id/quizzes all exist; new CourseBuilderPage replaces stub |
| BUILD-02 | Creator can navigate to Module Detail, Video Detail, Quiz Builder from Course Builder | React Router nested routes; new route /creator/courses/:id/modules/:moduleId needed; Video/Quiz stub routes stubbed for Phase 14/16 |
| BUILD-03 | Creator sees module/video/quiz status pills in Course Builder | Badge component exists; Module.status, Video.status, Quiz.status all in API responses |
| BUILD-04 | Creator can edit module details (title, description, learning outcome, duration estimate, unlock rule) | PUT /api/modules/:id exists; fields: title, description, learning_objectives, estimated_duration_minutes, unlock_rule — all in ModuleUpdate schema |
| BUILD-05 | Creator can generate module description via AI from prompt or uploaded document (streaming) | New SSE endpoint needed in modules.py or courses.py; ClaudeService._stream_text() reusable; upload via POST /api/uploads (pdf/docx allowed) |
| BUILD-06 | Creator sees Module Overview with unified drag-drop reorder (modules, videos, quizzes) and insert-between | dnd-kit NOT installed yet — needs install; POST /api/courses/:id/modules/reorder + POST /api/modules/:id/videos/reorder exist; quizzes lack reorder endpoint at module level |
</phase_requirements>

---

## Summary

Phase 13 builds the Course Builder home screen and Module Detail editor on top of a fully working backend (Phases 10–12). All data endpoints already exist. The primary new work is frontend UI and one new backend SSE endpoint for module description generation.

**dnd-kit is not installed.** `frontend/package.json` has no `@dnd-kit/*` packages. It must be installed before any drag-drop work begins. This is the only missing dependency. The stack decision in STATE.md is `@dnd-kit/sortable` — that decision is locked.

BUILD-06 "unified drag-drop list" means modules AND videos reordered within their respective parent scopes (not one flat list mixing all three entity types). Modules reorder within the course; videos reorder within their parent module. Quizzes are fixed-position per module (no reorder endpoint for module-level quizzes exists, and REQUIREMENTS.md quiz reorder is in Phase 16). The "unified" phrasing means the Module Overview card shows all items in one visual list with drag handles, but the API calls split by entity type.

The AI description generation for BUILD-05 requires a new `POST /api/modules/:id/ai/generate-description` SSE endpoint. It should follow the exact pattern of `courses.py` `/ai/generate-description` — `EventSourceResponse` wrapping an async generator that calls `claude_service._stream_text()` and checks `request.is_disconnected()`. Document upload uses the existing `POST /api/uploads` endpoint (PDF/DOCX allowed, 50 MB limit) then passes the returned URL to the generation prompt.

Zustand is deferred — local `useState` is sufficient for Phase 13. The course tree state (modules + their videos + quizzes) can be fetched on mount and held in component state. Cross-component sharing in Phase 13 is minimal: the left-rail tree and the main content area both live inside `CourseBuilderPage`. Zustand becomes necessary in Phase 14 when slide canvas state must persist across route changes.

**Primary recommendation:** Install dnd-kit, build CourseBuilderPage with two-panel layout (left rail + main), add ModuleDetailPage, add one SSE endpoint for module description AI, wire new routes in App.tsx.

---

## Standard Stack

### Core (all already installed)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| react | ^18.3.1 | Component tree | Project standard |
| react-router-dom | ^6.28.0 | SPA routing | Project standard |
| tailwindcss | ^3.4.16 | Utility CSS | Project standard |

### New Dependency Required
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| @dnd-kit/core | ^6.x | Drag-drop primitives | STATE.md locked decision |
| @dnd-kit/sortable | ^8.x | Sortable list abstraction | STATE.md locked decision |
| @dnd-kit/utilities | ^3.x | CSS transform helpers | Companion to sortable |

**dnd-kit is NOT in package.json. Install required.**

**Installation:**
```bash
cd frontend && npm install @dnd-kit/core @dnd-kit/sortable @dnd-kit/utilities
```

### Deferred (do not introduce in Phase 13)
| Library | Reason |
|---------|--------|
| Zustand | Deferred from Phase 12; Phase 13 local state is sufficient |
| TanStack Query | Deferred; Phase 13 fetch-on-mount pattern matches existing page pattern |
| TipTap | Needed for Phase 14 rich text; not needed here (Textarea for description) |

---

## Architecture Patterns

### Recommended Structure (new files only)
```
frontend/src/
├── pages/creator/
│   ├── CourseBuilderPage.tsx        # replaces stub in App.tsx
│   └── ModuleDetailPage.tsx         # new — /creator/courses/:id/modules/:moduleId
├── components/builder/
│   ├── CourseTreeRail.tsx            # left-rail tree component
│   ├── ModuleOverviewList.tsx        # drag-drop sortable module+video list
│   └── AiDescriptionPanel.tsx       # SSE streaming panel for module description
backend/routers/
│   └── modules.py                   # add POST /api/modules/:id/ai/generate-description
```

### Pattern 1: Two-Panel Builder Layout
**What:** `CourseBuilderPage` renders a flex container with a fixed-width left rail (tree navigation) and a scrollable main content area. The left rail shows a nested tree of modules > videos/quizzes with status badges. The main area renders the Module Overview list (sortable).
**When to use:** Any time the course tree is visible alongside editable content.

```typescript
// CourseBuilderPage.tsx — layout skeleton
export function CourseBuilderPage() {
  const { id } = useParams<{ id: string }>()
  const [modules, setModules] = useState<Module[]>([])
  const [videos, setVideos] = useState<Record<number, Video[]>>({})
  const [quizzes, setQuizzes] = useState<Record<number, Quiz[]>>({})

  // fetch on mount — matches CreatorCourseListPage pattern
  useEffect(() => {
    fetchTree(Number(id))
  }, [id])

  return (
    <div style={{ display: 'flex', height: '100%' }}>
      <CourseTreeRail modules={modules} videos={videos} quizzes={quizzes} courseId={id} />
      <main style={{ flex: 1, overflow: 'auto', padding: '32px' }}>
        <ModuleOverviewList modules={modules} videos={videos} onReorder={handleReorder} courseId={Number(id)} />
      </main>
    </div>
  )
}
```

### Pattern 2: dnd-kit Sortable List
**What:** Use `SortableContext` with `verticalListSortingStrategy` for both modules-within-course and videos-within-module. Each sortable item wraps a card row. `onDragEnd` fires the atomic reorder API call with the new full sibling array.
**When to use:** Any ordered list that needs drag-drop reorder with persistence.

```typescript
// Source: dnd-kit official docs — sortable vertical list
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  DragEndEvent,
} from '@dnd-kit/core'
import {
  SortableContext,
  sortableKeyboardCoordinates,
  verticalListSortingStrategy,
  useSortable,
  arrayMove,
} from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'

function SortableModuleRow({ module }: { module: Module }) {
  const { attributes, listeners, setNodeRef, transform, transition } = useSortable({ id: module.id })
  const style = { transform: CSS.Transform.toString(transform), transition }
  return (
    <div ref={setNodeRef} style={style} {...attributes} {...listeners}>
      {/* module card content */}
    </div>
  )
}

function ModuleOverviewList({ modules, courseId, onReorder }) {
  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates })
  )

  const handleDragEnd = async (event: DragEndEvent) => {
    const { active, over } = event
    if (!over || active.id === over.id) return
    const oldIndex = modules.findIndex(m => m.id === active.id)
    const newIndex = modules.findIndex(m => m.id === over.id)
    const reordered = arrayMove(modules, oldIndex, newIndex)
    onReorder(reordered) // optimistic update in parent state
    await api.post(`/courses/${courseId}/modules/reorder`, {
      module_ids: reordered.map(m => m.id),
    })
  }

  return (
    <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
      <SortableContext items={modules.map(m => m.id)} strategy={verticalListSortingStrategy}>
        {modules.map(m => <SortableModuleRow key={m.id} module={m} />)}
      </SortableContext>
    </DndContext>
  )
}
```

### Pattern 3: SSE Streaming — Module Description
**What:** New endpoint `POST /api/modules/:id/ai/generate-description` in `modules.py`. Follows the exact pattern of courses.py SSE endpoints. Frontend uses `fetch` + `ReadableStream` — not `EventSource`. Same as Phase 12 `streamDescription` function in CourseIdentityModal.
**When to use:** All AI generation in this project.

Backend pattern (mirrors courses.py):
```python
# backend/routers/modules.py — new endpoint
from fastapi import Request
from sse_starlette.sse import EventSourceResponse
from services.claude_service import ClaudeService

claude_service = ClaudeService()

class AiModuleDescriptionRequest(BaseModel):
    prompt: str
    tone_preset: Optional[str] = "professional"
    document_url: Optional[str] = None  # pre-uploaded doc URL for context

@router.post("/api/modules/{module_id}/ai/generate-description")
async def generate_module_description_stream(
    module_id: int,
    request: Request,
    body: AiModuleDescriptionRequest,
    db: Session = Depends(get_db),
    current_user=Depends(require_creator),
):
    module = db.query(Module).filter(Module.id == module_id).first()
    if not module:
        raise HTTPException(status_code=404, detail="Module not found")
    _check_course_ownership(module.course, current_user)

    async def generator():
        async for token in claude_service.stream_module_description(body.prompt, body.tone_preset):
            if await request.is_disconnected():
                break
            yield {"data": token}

    return EventSourceResponse(generator())
```

Frontend pattern (mirrors CourseIdentityModal.streamDescription):
```typescript
// AiDescriptionPanel.tsx or inline in ModuleDetailPage
const streamModuleDescription = async (moduleId: number, prompt: string) => {
  const controller = new AbortController()
  setStreaming(true)
  setDescription('')
  try {
    const res = await fetch(`${API_BASE}/api/modules/${moduleId}/ai/generate-description`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${localStorage.getItem('token')}`,
      },
      body: JSON.stringify({ prompt, tone_preset: 'professional' }),
      signal: controller.signal,
    })
    const reader = res.body!.getReader()
    const decoder = new TextDecoder()
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      const text = decoder.decode(value)
      for (const line of text.split('\n')) {
        if (line.startsWith('data: ')) {
          setDescription(prev => prev + line.slice(6))
        }
      }
    }
  } finally {
    setStreaming(false)
  }
}
```

### Pattern 4: Module Detail Form
**What:** `ModuleDetailPage` fetches `GET /api/modules/:moduleId`, renders a form with all editable fields, saves via `PUT /api/modules/:moduleId`. Uses existing Input, Textarea, Select common components.
**Fields to expose:**
- `title` — Input (required)
- `description` — Textarea + AI generate button
- `learning_objectives` — repeatable text inputs (array, up to 5; mirrors CourseIdentityModal objectives UI)
- `estimated_duration_minutes` — Input type=number (field is `estimated_duration_minutes`, NOT `duration_estimate_minutes`)
- `unlock_rule` — Select (options: `after_previous`, `immediate`, `on_date`)
- `status` — Select (options: `draft`, `published`)

**CRITICAL field name:** The model uses `estimated_duration_minutes` (not `duration_estimate_minutes`). The REQUIREMENTS.md description says "duration estimate" but the actual schema field is `estimated_duration_minutes`. Phase 13 success criterion says "duration estimate" — the UI label can be "Duration Estimate (minutes)" while the API field is `estimated_duration_minutes`.

**CRITICAL field name 2:** `learning_objectives` (not `learning_outcome`). Success criterion says "learning outcome" singular — the actual schema field is `learning_objectives` (array). Show as "Learning Outcome" in the UI label but bind to `learning_objectives[0]` or allow multiple.

### Pattern 5: App.tsx Route Addition
**What:** Replace the builder stub and add ModuleDetailPage route. Both wrapped in `CreatorLayout` + `ProtectedRoute creatorRoute` — exactly like all existing creator routes.

```typescript
// App.tsx additions
import { CourseBuilderPage } from '@/pages/creator/CourseBuilderPage'
import { ModuleDetailPage } from '@/pages/creator/ModuleDetailPage'

// Replace stub:
<Route
  path="/creator/courses/:id/builder"
  element={
    <CreatorLayout>
      <ProtectedRoute creatorRoute>
        <CourseBuilderPage />
      </ProtectedRoute>
    </CreatorLayout>
  }
/>
// New route:
<Route
  path="/creator/courses/:id/modules/:moduleId"
  element={
    <CreatorLayout>
      <ProtectedRoute creatorRoute>
        <ModuleDetailPage />
      </ProtectedRoute>
    </CreatorLayout>
  }
/>
```

### Anti-Patterns to Avoid
- **Using EventSource for SSE:** The entire project uses `fetch` + `ReadableStream` (not `EventSource`). EventSource does not support POST bodies or custom Authorization headers.
- **Mixing dnd-kit/sortable with react-grid-layout:** STATE.md is explicit — sortable for lists, react-grid-layout for slide canvas. Do not use react-grid-layout here.
- **Local order_index increment on drag:** Never compute order_index locally. Send the full sibling id array to the reorder endpoint on every drag-end; let the backend assign indices atomically.
- **Fetching videos/quizzes for ALL modules on load:** Fetch module list on mount, then fetch videos+quizzes per module lazily (on expand or as needed). Loading all nested data upfront will be slow for large courses.
- **Using `learning_outcome` as field name:** The API field is `learning_objectives` (array). The UI label says "Learning Outcome" but the field binding is `learning_objectives`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Drag-drop sortable list | Custom mousedown/pointermove handlers | @dnd-kit/sortable | Handles accessibility, keyboard, touch, pointer cancel, scroll edge cases |
| order_index recomputation | Client-side index reassignment | Atomic reorder endpoint (`POST /api/courses/:id/modules/reorder`) | Single db.commit() prevents drift under concurrent edits |
| SSE reconnection | Custom retry loop | Server-side `request.is_disconnected()` + AbortController | Project pattern already established; EventSource auto-reconnect is not wanted |
| File content extraction | Manual PDF/DOCX parsing | Pass document_url to Claude prompt context (Phase 13 only); PyMuPDF used in Phase 15 | Full document ingestion pipeline is Phase 15 (AI-04); Phase 13 only needs URL passthrough |

**Key insight:** dnd-kit handles ~15 edge cases (touch, keyboard, scroll containers, portal rendering, accessibility announcements) that manual implementations consistently miss. Never build sortable drag-drop from scratch.

---

## Common Pitfalls

### Pitfall 1: order_index drift on repeated reorders
**What goes wrong:** After several drag operations, items appear in the wrong position on page reload.
**Why it happens:** If client assigns order_index incrementally (0, 1, 2, ...) but sends only the moved item rather than the full sibling list, out-of-sync indices accumulate.
**How to avoid:** Always call reorder with the FULL ordered list of sibling IDs. `POST /api/courses/:id/modules/reorder` body is `{ module_ids: [id, id, id, ...] }` — all siblings, not just the moved one. Use `arrayMove` from `@dnd-kit/sortable` to compute the new array, then send all IDs.
**Warning signs:** Items "jump" position after reload; order_index values have gaps or duplicates.

### Pitfall 2: Video reorder is scoped per module, not across modules
**What goes wrong:** Attempting to drag a video from Module 1 into Module 2 via a flat list. The reorder endpoint is `POST /api/modules/:moduleId/videos/reorder` — it only accepts video IDs belonging to that specific module.
**Why it happens:** BUILD-06 "unified list" is ambiguous — it means modules AND their videos are shown in one visual flow, but reorder is still per-scope.
**How to avoid:** Use separate `DndContext` instances per module's video list, or use `SortableContext` items scoped to each module's video array. Moving a video between modules is out of scope for Phase 13.
**Warning signs:** 400 error from reorder endpoint: "Some video IDs do not belong to this module."

### Pitfall 3: dnd-kit id prop must be unique across all sortable contexts
**What goes wrong:** Module IDs and Video IDs overlap numerically (e.g., module.id=1, video.id=1). dnd-kit uses `id` to identify items and active/over detection breaks.
**Why it happens:** Backend assigns IDs independently per table; a module and a video can have id=1.
**How to avoid:** Namespace the IDs passed to dnd-kit: `id={"module-" + module.id}` and `id={"video-" + video.id}`. Strip the prefix when constructing the API reorder payload.
**Warning signs:** Drag-drop moves wrong item, or `active.id === over.id` fires incorrectly.

### Pitfall 4: PointerSensor fires on click (triggering sort when user meant to navigate)
**What goes wrong:** Clicking a module row to navigate to Module Detail triggers the drag handler instead.
**Why it happens:** PointerSensor starts on `pointerdown` by default; a click is a pointerdown+pointerup.
**How to avoid:** Add `activationConstraint: { distance: 8 }` to PointerSensor — drag only activates after 8px movement.
```typescript
useSensor(PointerSensor, { activationConstraint: { distance: 8 } })
```
**Warning signs:** Clicking a row navigates AND changes order_index.

### Pitfall 5: Module Detail field name confusion
**What goes wrong:** Form binds to `duration_estimate_minutes` or `learning_outcome` — fields that don't exist in ModuleUpdate schema.
**Why it happens:** REQUIREMENTS.md and success criteria use human-readable names; the actual API schema uses different names.
**How to avoid:** Use `estimated_duration_minutes` and `learning_objectives[]` for all API calls. UI labels can say anything.
**Warning signs:** PUT /api/modules/:id returns 422 Unprocessable Entity.

### Pitfall 6: quiz reorder endpoint does not exist at module level
**What goes wrong:** Attempting to call `POST /api/modules/:moduleId/quizzes/reorder` — no such endpoint exists.
**Why it happens:** BUILD-06 mentions "modules, videos, quizzes" in one list. Quiz reorder is Phase 16 (QUIZ-07).
**How to avoid:** In Phase 13, quizzes are displayed in the tree/list as non-draggable items. Only modules and videos are draggable in this phase.

### Pitfall 7: SSE endpoint order collision in FastAPI
**What goes wrong:** The new `POST /api/modules/:module_id/ai/generate-description` endpoint is shadowed by the existing GET `/api/modules/:module_id` route.
**Why it happens:** FastAPI matches `/api/modules/{module_id}` before `/api/modules/{module_id}/ai/...` if registered in wrong order.
**How to avoid:** Register the `/ai/generate-description` route BEFORE the general `/{module_id}` routes in modules.py. This is the same fix as Phase 12 SSE routes being declared before `/{course_id}` routes in courses.py.
**Warning signs:** 405 Method Not Allowed or 422 when POSTing to the AI endpoint.

---

## Code Examples

### Existing API call pattern (from api.ts)
```typescript
// Source: frontend/src/services/api.ts
// POST with JSON body
const res = await api.post(`/courses/${courseId}/modules/reorder`, { module_ids: [3, 1, 2] })

// PUT for module update
const res = await api.put(`/modules/${moduleId}`, {
  title: 'Updated Title',
  estimated_duration_minutes: 30,
  unlock_rule: 'after_previous',
})
```

### Fetching module tree data
```typescript
// Fetch modules for a course
const modsRes = await api.get(`/courses/${courseId}/modules`)
const modules: Module[] = await modsRes.json()

// Fetch videos for a specific module
const vidsRes = await api.get(`/modules/${moduleId}/videos`)
const videos: Video[] = await vidsRes.json()

// Fetch quizzes for a module
const quizRes = await api.get(`/modules/${moduleId}/quizzes`)
const quizzes: Quiz[] = await quizRes.json()
```

### Module fields confirmed from ModuleResponse schema
```typescript
interface Module {
  id: number
  course_id: number
  order_index: number
  title: string
  description: string | null
  learning_objectives: unknown[] | null
  estimated_duration_minutes: number | null
  unlock_rule: string | null       // e.g. "after_previous", "immediate"
  status: string | null             // "draft" | "published"
  created_at: string
  updated_at: string | null
}
```

### Video fields confirmed from VideoResponse schema
```typescript
interface Video {
  id: number
  module_id: number
  order_index: number
  title: string
  description: string | null
  video_type: string | null          // "slideshow_narrated" etc.
  estimated_duration_seconds: number | null
  source_video_url: string | null
  status: string | null
  created_at: string
  updated_at: string | null
}
```

### Quiz fields confirmed from QuizResponse schema
```typescript
interface Quiz {
  id: number
  module_id: number | null
  video_id: number | null
  order_index: number
  title: string
  pass_rate: number
  attempts_allowed: number
  shuffle_questions: boolean
  show_feedback: string
  status: string | null
}
```

### Document upload for BUILD-05
```typescript
// POST /api/uploads — multipart form
const formData = new FormData()
formData.append('file', file)
formData.append('category', 'documents')
const res = await fetch(`${API_BASE}/api/uploads`, {
  method: 'POST',
  headers: { Authorization: `Bearer ${localStorage.getItem('token')}` },
  body: formData,
})
const { url } = await res.json()  // e.g. "/uploads/documents/abc123_file.pdf"
// Then pass url as document_url in the AI generation request body
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| react-beautiful-dnd (unmaintained) | @dnd-kit/sortable | ~2022 | dnd-kit is the successor; better TypeScript, smaller bundle |
| EventSource for SSE | fetch + ReadableStream | Phase 12 | EventSource can't send POST body or Bearer token |
| Inline JSX styles only | Tailwind classes preferred | Phase 9 baseline | Inline styles used where jsdom/PostCSS limitations exist (tests) |

**Note on Zustand deferral:** STATE.md deferred Zustand from Phase 12. Phase 13 does not need it. The course tree (modules + videos + quizzes) is fetched once on CourseBuilderPage mount and stored in local useState. ModuleDetailPage fetches its own module on mount. No cross-page state sharing is needed in Phase 13.

---

## Open Questions

1. **Quiz ordering in the unified list (BUILD-06)**
   - What we know: No `POST /api/modules/:id/quizzes/reorder` endpoint exists. Quiz reorder is Phase 16 (QUIZ-07).
   - What's unclear: Should quizzes appear in the BUILD-06 list at all, or only modules and videos?
   - Recommendation: Show quizzes as non-draggable items in the list (rendered without drag handles, positioned after their module's videos). Drag-drop is enabled for modules and videos only.

2. **"Insert between" capability in BUILD-06**
   - What we know: dnd-kit sortable supports dropping between items natively.
   - What's unclear: Does "insert between modules" mean moving a video into a different module's scope?
   - Recommendation: Limit Phase 13 insert-between to reordering within the same parent (module within course, video within module). Cross-module video movement deferred.

3. **Document content extraction for BUILD-05 AI generation**
   - What we know: `POST /api/uploads` accepts PDF/DOCX. Full document ingestion (PyMuPDF parsing) is Phase 15 (AI-04). The upload endpoint stores files and returns a URL.
   - What's unclear: How much document context to pass to Claude in Phase 13 (before Phase 15 ingestion pipeline exists).
   - Recommendation: Phase 13 passes the document_url as context in the Claude prompt string ("The user uploaded a document at {url}, use the module topic prompt to generate the description"). Full PDF text extraction is Phase 15.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Frontend framework | Vitest 2.1.8 + Testing Library React 16 |
| Frontend config | `frontend/vitest.config.ts` |
| Frontend quick run | `cd frontend && npm run test:unit` |
| Backend framework | pytest (FastAPI TestClient) |
| Backend config | `backend/pytest.ini` (inferred from test discovery) |
| Backend quick run | `cd backend && python -m pytest tests/ -x -q` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| BUILD-01 | CourseBuilderPage renders tree rail with modules | unit (vitest) | `cd frontend && npm run test:unit` | ❌ Wave 0 |
| BUILD-02 | Clicking module in tree navigates to /modules/:id | unit (vitest) | `cd frontend && npm run test:unit` | ❌ Wave 0 |
| BUILD-03 | Status pills visible for draft/published items | unit (vitest) | `cd frontend && npm run test:unit` | ❌ Wave 0 |
| BUILD-04 | Module Detail PUT saves all fields | integration (pytest) | `cd backend && python -m pytest tests/test_modules_router.py -x -q` | ✅ (partial — PUT tested) |
| BUILD-05 | SSE endpoint streams module description tokens | integration (pytest) | `cd backend && python -m pytest tests/test_modules_phase13.py -x -q` | ❌ Wave 0 |
| BUILD-06 | Reorder API accepts full sibling list, persists | integration (pytest) | `cd backend && python -m pytest tests/test_modules_router.py -x -q` | ✅ (partial — reorder tested) |

### Sampling Rate
- **Per task commit:** `cd frontend && npm run test:unit` (vitest, ~5s)
- **Per task commit (backend):** `cd backend && python -m pytest tests/test_modules_router.py tests/test_videos_slides_router.py -x -q`
- **Per wave merge:** Both frontend and backend full suites
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `frontend/src/pages/creator/__tests__/CourseBuilderPage.test.tsx` — covers BUILD-01, BUILD-02, BUILD-03
- [ ] `frontend/src/pages/creator/__tests__/ModuleDetailPage.test.tsx` — covers BUILD-04, BUILD-05 (stream panel)
- [ ] `backend/tests/test_modules_phase13.py` — covers BUILD-05 SSE endpoint (`POST /api/modules/:id/ai/generate-description`)

*(Existing `test_modules_router.py` covers BUILD-04 and BUILD-06 partially; new tests extend, not replace.)*

---

## Sources

### Primary (HIGH confidence)
- Codebase: `backend/routers/modules.py` — ModuleUpdate schema, reorder endpoint, field names confirmed
- Codebase: `backend/routers/videos.py` — VideoResponse fields, per-module reorder endpoint confirmed
- Codebase: `backend/routers/quizzes.py` — QuizResponse fields, quiz reorder is per-quiz not per-module
- Codebase: `backend/routers/courses.py` lines 256–289 — SSE pattern with EventSourceResponse, is_disconnected, exact generator structure
- Codebase: `backend/services/claude_service.py` lines 558–595 — `_stream_text()` reusable method
- Codebase: `frontend/package.json` — dnd-kit confirmed NOT installed
- Codebase: `frontend/src/App.tsx` — builder stub confirmed, route pattern for new routes
- Codebase: `backend/routers/uploads.py` — PDF/DOCX accepted, 50 MB limit
- Project: `.planning/STATE.md` — dnd-kit/sortable locked decision, Zustand deferred

### Secondary (MEDIUM confidence)
- dnd-kit official docs — `activationConstraint: { distance: 8 }` for click/drag disambiguation; `arrayMove` utility; namespace IDs for multiple sortable contexts

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — confirmed from package.json (missing dnd-kit) and STATE.md (locked)
- Architecture: HIGH — all API endpoints confirmed from source; SSE pattern confirmed from courses.py
- Pitfalls: HIGH — order_index atomic pattern from STATE.md pitfall #3; SSE route order from Phase 12 decision log; field name confusion confirmed by reading actual schemas
- dnd-kit click/drag disambiguation: MEDIUM — from dnd-kit docs; confirmed as common issue in community

**Research date:** 2026-05-09
**Valid until:** 2026-06-09 (stable stack; no fast-moving dependencies)
