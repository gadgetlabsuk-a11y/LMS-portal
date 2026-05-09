# Phase 14: Slide Builder & Slide Editor — Research

**Researched:** 2026-05-09
**Domain:** React drag-drop canvas editor (react-grid-layout), rich text (TipTap v3), client state (Zustand 5), SSE streaming (sse-starlette 2.x), FastAPI slide/block CRUD
**Confidence:** HIGH (stack locked; backend models/API fully built; prior phase patterns directly applicable)

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| SLIDE-01 | Creator can access Slide Builder for a video and see a thumbnail strip of slides | `GET /api/videos/{video_id}/slides` exists; need SlideBuilderPage + VideoSlideStrip component |
| SLIDE-02 | Creator can add, reorder, duplicate, and delete slides from the thumbnail strip | All CRUD + reorder endpoints exist; duplicate = POST with copied layout_id + narration_script; dnd-kit for strip reorder (list, not canvas) |
| SLIDE-03 | Creator can trigger bulk narration audio generation for all slides with populated scripts | Backend SSE endpoint needed: `POST /api/videos/{video_id}/slides/bulk-narrate`; Phase 17 implements ElevenLabs; Phase 14 wires the button + status indicators |
| SLIDE-04 | Creator can open Slide Editor for any slide | SlideEditorPage routed at `/creator/courses/:id/videos/:videoId/slides/:slideId/editor` |
| SLIDE-05 | Creator can drag content blocks onto a 12-column snap-grid canvas | react-grid-layout with `cols=12`; block library palette on left; drop creates block via `POST /api/slides/{slide_id}/blocks` |
| SLIDE-06 | Creator can resize and reposition blocks on the canvas | react-grid-layout `isResizable + isDraggable`; `onDragStop`/`onResizeStop` persist grid_position via `PUT /api/blocks/{block_id}` |
| SLIDE-07 | Creator can undo and redo canvas changes (minimum 20-step history) | Zustand 5 with temporal middleware (`zustand/middleware/temporal`) — wraps canvas layout slice |
| SLIDE-08 | Slide content autosaves on change; pending save flushes before navigation | Debounced autosave (500ms) in Zustand; `useBeforeUnload` + React Router `useBlocker` to flush on route change |
| SLIDE-09 | Creator can select a layout preset | Layout presets are pre-defined block arrangements; applying a preset replaces canvas blocks via bulk-delete + bulk-create or a dedicated preset endpoint |
| SLIDE-10 | Creator can write or edit a narration script for a slide in the Narration tab | Controlled textarea bound to `PUT /api/slides/{slide_id}` with `narration_script` field |
| SLIDE-11 | Creator can generate a narration script via AI from slide content blocks (streaming) | New SSE endpoint `POST /api/slides/{slide_id}/ai/generate-narration`; pattern identical to modules.py generate-description |
| SLIDE-12 | Creator can generate a slide outline via AI wizard (4-step: source → config → generation → commit) | 4-step modal wizard; generation = SSE stream returning JSON outline; commit = bulk POST slides + blocks |
</phase_requirements>

---

## Summary

Phase 14 is the most complex frontend phase in v1.0. It introduces three distinct interaction surfaces: a thumbnail strip (list drag-drop via dnd-kit — already installed), a 12-column snap-grid canvas (react-grid-layout — not yet installed), and a narration/AI tab with SSE streaming. All backend CRUD endpoints already exist from Phase 11. Two new backend SSE endpoints are needed: narration script generation (SLIDE-11) and the slide outline wizard backend (SLIDE-12).

The primary complexity is the canvas editor itself: react-grid-layout needs to be installed and configured with `cols=12`, block create/update/delete must be wired to the existing blocks API, and undo/redo requires Zustand 5 with the `temporal` middleware (zundo or the built-in temporal). Autosave must write block `grid_position` only on `onDragStop`/`onResizeStop` (not during drag) to avoid a race condition explicitly called out in STATE.md.

TipTap v3 is needed for text/heading/code blocks but can be scoped: only the blocks that need rich text (text, heading) get a TipTap editor; simpler blocks (image URL, code, quote, list, callout, divider) use plain inputs or textareas.

**Primary recommendation:** Install react-grid-layout + Zustand 5 + TipTap v3 in Wave 0. Build the two-panel layout (strip left, editor right) before tackling individual block editors. Wire autosave with the debounce+flush pattern before implementing undo/redo — order matters.

---

## Standard Stack

### Core (not yet installed — install in Wave 0)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| react-grid-layout | ^1.4.4 | 12-column snap-grid canvas | Locked decision in STATE.md; purpose-built for draggable resizable grid layouts; do NOT substitute dnd-kit |
| zustand | ^5.0.x | Canvas/editor local state, undo history | Locked decision in STATE.md; lightweight, no boilerplate, temporal middleware built-in |
| @tiptap/react | ^3.x | Rich text for text/heading blocks | Locked decision in STATE.md; headless, Tailwind-compatible, no global CSS fights |
| @tiptap/starter-kit | ^3.x | TipTap extension bundle (bold, italic, lists, headings) | Standard TipTap starter; avoids picking individual extensions |

### Already Installed

| Library | Version | Purpose | Notes |
|---------|---------|---------|-------|
| @dnd-kit/core | ^6.3.1 | Drag-drop for thumbnail strip reorder | Already used in Phase 13 ModuleOverviewList |
| @dnd-kit/sortable | ^10.0.0 | Sortable list primitives | Already installed |
| react-router-dom | ^6.28.0 | Routing / `useBlocker` for nav guard | Already installed |

### Supporting (need to install)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| react-grid-layout CSS | bundled | Required CSS import for grid rendering | Import `react-grid-layout/css/styles.css` and `react-grid-layout/css/resizable.css` in SlideEditorPage |
| zundo | ^2.x | Temporal (undo/redo) middleware for Zustand | Use if Zustand 5's built-in `temporal` is insufficient; zundo is the ecosystem standard |

**Installation:**
```bash
cd frontend && npm install react-grid-layout zustand @tiptap/react @tiptap/starter-kit
npm install --save-dev @types/react-grid-layout
```

---

## Architecture Patterns

### Recommended Project Structure

```
frontend/src/
├── pages/creator/
│   ├── SlideBuilderPage.tsx          # Thumbnail strip + "open editor" nav
│   └── SlideEditorPage.tsx           # Canvas + narration tabs
├── components/slide/
│   ├── VideoSlideStrip.tsx           # dnd-kit sortable thumbnail strip
│   ├── SlideCanvas.tsx               # react-grid-layout wrapper
│   ├── BlockLibraryPalette.tsx       # Draggable block type buttons
│   ├── LayoutPresetPicker.tsx        # Layout preset cards
│   ├── NarrationTab.tsx              # Script textarea + AI generation
│   ├── SlideOutlineWizard.tsx        # 4-step wizard modal
│   └── blocks/
│       ├── TextBlock.tsx             # TipTap rich text
│       ├── HeadingBlock.tsx          # TipTap heading
│       ├── ImageBlock.tsx            # URL input + preview
│       ├── VideoEmbedBlock.tsx       # URL input
│       ├── CodeBlock.tsx             # Plain textarea (monospace)
│       ├── QuoteBlock.tsx            # Styled textarea
│       ├── ListBlock.tsx             # Managed list items
│       ├── CalloutBlock.tsx          # Icon + text
│       └── DividerBlock.tsx          # Visual separator
└── store/
    └── slideEditorStore.ts           # Zustand 5 store with temporal slice
```

### Pattern 1: react-grid-layout Canvas (12 columns)

**What:** Drag-and-drop resizable grid. Each block is a grid item identified by `i` (block ID as string).
**When to use:** The slide canvas. Not the thumbnail strip (that uses dnd-kit sortable).

```typescript
// Source: react-grid-layout official docs
import GridLayout from 'react-grid-layout'
import 'react-grid-layout/css/styles.css'
import 'react-grid-layout/css/resizable.css'

interface GridBlock {
  i: string    // block.id as string
  x: number    // col 0–11
  y: number    // row unit
  w: number    // width in cols
  h: number    // height in row units
}

<GridLayout
  className="slide-canvas"
  layout={gridLayout}
  cols={12}
  rowHeight={40}
  width={960}
  onDragStop={handleDragStop}
  onResizeStop={handleResizeStop}
  isDraggable
  isResizable
  compactType={null}       // free placement, no auto-pack
  preventCollision={false}
>
  {blocks.map(block => (
    <div key={block.id.toString()}>
      <BlockRenderer block={block} />
    </div>
  ))}
</GridLayout>
```

**Key pitfall:** Only write `grid_position` to the API on `onDragStop`/`onResizeStop`, not `onDrag`/`onResize`. The latter fires dozens of times per interaction — autosave on every call will overwhelm the API and cause race conditions. This is explicitly documented in STATE.md.

### Pattern 2: Zustand 5 Canvas Store with Undo/Redo

**What:** Local canvas state (blocks, layout, dirty flag) with temporal slice for undo/redo.
**When to use:** All canvas mutations go through this store; side effects (API calls) triggered from store subscriptions or component handlers.

```typescript
// Source: Zustand 5 docs + zundo pattern
import { create } from 'zustand'
import { temporal } from 'zundo'  // or zustand/middleware/temporal in zustand 5

interface CanvasBlock {
  id: number
  type: string
  content: Record<string, unknown>
  grid_position: { x: number; y: number; w: number; h: number }
}

interface SlideEditorState {
  blocks: CanvasBlock[]
  isDirty: boolean
  addBlock: (block: CanvasBlock) => void
  updateBlock: (id: number, updates: Partial<CanvasBlock>) => void
  deleteBlock: (id: number) => void
  setBlocks: (blocks: CanvasBlock[]) => void
}

export const useSlideEditorStore = create<SlideEditorState>()(
  temporal(
    (set) => ({
      blocks: [],
      isDirty: false,
      addBlock: (block) => set(s => ({ blocks: [...s.blocks, block], isDirty: true })),
      updateBlock: (id, updates) => set(s => ({
        blocks: s.blocks.map(b => b.id === id ? { ...b, ...updates } : b),
        isDirty: true,
      })),
      deleteBlock: (id) => set(s => ({
        blocks: s.blocks.filter(b => b.id !== id),
        isDirty: true,
      })),
      setBlocks: (blocks) => set({ blocks, isDirty: false }),
    }),
    { limit: 20 }  // SLIDE-07: minimum 20-step history
  )
)
```

**Undo/redo usage:**
```typescript
const { undo, redo, pastStates, futureStates } = useSlideEditorStore.temporal.getState()
```

### Pattern 3: Autosave with Debounce + Navigation Flush (SLIDE-08)

**What:** Debounced save fires 500ms after last change; navigation guard flushes immediately.
**When to use:** For block content changes and narration script edits.

```typescript
// In SlideEditorPage
const isDirty = useSlideEditorStore(s => s.isDirty)
const blocks = useSlideEditorStore(s => s.blocks)

// Debounced autosave
useEffect(() => {
  if (!isDirty) return
  const timer = setTimeout(() => flushSave(blocks), 500)
  return () => clearTimeout(timer)
}, [blocks, isDirty])

// Navigation guard — flush before leaving
const blocker = useBlocker(isDirty)
useEffect(() => {
  if (blocker.state === 'blocked') {
    flushSave(blocks).then(() => blocker.proceed())
  }
}, [blocker])
```

`flushSave` calls `PUT /api/blocks/{id}` for each dirty block, then calls `PUT /api/slides/{id}` if narration_script changed.

### Pattern 4: SSE Narration Script Generation (SLIDE-11)

**What:** POST SSE endpoint on slides router — identical pattern to modules.py generate-description.
**When to use:** "Generate narration" button in NarrationTab.

Backend endpoint (add to slides.py):
```python
# MUST be declared BEFORE /api/slides/{slide_id} wildcard — FastAPI path collision rule
@router.post("/api/slides/{slide_id}/ai/generate-narration")
async def generate_narration_script(
    slide_id: int,
    body: AiNarrationRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_creator),
):
    slide = get_slide_or_404(slide_id, db, current_user)
    blocks = db.query(Block).filter(Block.slide_id == slide.id).all()
    block_summary = "\n".join(
        f"- {b.type}: {b.content}" for b in blocks if b.content
    )

    async def event_generator():
        async for token in claude_service._stream_text(prompt):
            if await request.is_disconnected():
                break
            yield {"data": token}

    return EventSourceResponse(event_generator())
```

Frontend SSE consumption — identical pattern to ModuleDetailPage.tsx `handleGenerateDescription`:
```typescript
const res = await fetch(`${API_BASE}/api/slides/${slideId}/ai/generate-narration`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
  body: JSON.stringify({ tone_preset: 'professional' }),
})
const reader = res.body!.getReader()
const decoder = new TextDecoder()
while (true) {
  const { done, value } = await reader.read()
  if (done) break
  for (const line of decoder.decode(value).split('\n')) {
    if (line.startsWith('data: ')) setNarrationScript(prev => prev + line.slice(6))
  }
}
```

### Pattern 5: 4-Step Slide Outline Wizard (SLIDE-12)

**What:** Modal with 4 wizard steps: (1) source selection (prompt or document), (2) config (slides count, tone), (3) AI generation with SSE preview, (4) commit (POST bulk slides + blocks).
**When to use:** "Generate slide outline" button in SlideBuilderPage.

Step 3 generates a JSON outline via SSE. The AI response must be valid JSON describing slide titles and block content. Step 4 iterates the outline and calls:
1. `POST /api/videos/{video_id}/slides` for each slide
2. `POST /api/slides/{new_slide_id}/blocks` for each block in that slide

This is a sequential async loop — no bulk endpoint needed.

### Pattern 6: Slide Duplicate

**What:** SLIDE-02 requires duplicate. No backend endpoint exists — implement client-side.
**Implementation:** `GET /api/slides/{id}` to fetch blocks, then `POST /api/videos/{video_id}/slides` for the new slide, then `POST /api/slides/{new_id}/blocks` for each block. Show spinner during multi-step creation.

### Anti-Patterns to Avoid

- **Writing grid_position on `onDrag`:** Fires 60fps during drag. Only write on `onDragStop`. (STATE.md pitfall #5)
- **Mixing dnd-kit and react-grid-layout in the same drag context:** dnd-kit for the thumbnail strip; react-grid-layout for the canvas. Never nest them. (STATE.md locked decision)
- **Saving narration_script to blocks API:** Narration script is on the Slide model (`PUT /api/slides/{id}`), not on blocks.
- **Using EventSource for SSE:** This project uses `fetch + ReadableStream` for SSE (POST endpoints). EventSource only supports GET. (STATE.md locked decision)
- **Declaring SSE routes after wildcard routes in FastAPI:** SSE endpoint `POST /api/slides/{slide_id}/ai/generate-narration` must be declared BEFORE `GET /api/slides/{slide_id}` in slides.py to avoid FastAPI path collision. (STATE.md locked decision)

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| 12-column snap grid | Custom CSS grid + mouse event tracking | react-grid-layout | Handles collision, resizing handles, auto-pack, row height, responsive breakpoints — thousands of edge cases |
| Undo/redo history | Custom stack with push/pop | Zustand temporal middleware (zundo) | Handles branching, max depth, pause/resume — not trivial with setState |
| Rich text blocks | `contenteditable` + execCommand | TipTap v3 | TipTap handles cursor position, paste sanitisation, schema validation, extensions |
| Debounced save | setInterval polling | useEffect + clearTimeout pattern | Simpler; correctly handles cleanup; React lifecycle-safe |
| Block ID for grid key | Random UUID | Actual `block.id` from DB | Stable keys prevent react-grid-layout re-mounting items on re-render |

---

## Common Pitfalls

### Pitfall 1: CSS Not Imported for react-grid-layout
**What goes wrong:** Grid items overlap each other; resize handles invisible or broken.
**Why it happens:** react-grid-layout requires two CSS files that are not auto-injected.
**How to avoid:** Add these two imports to SlideEditorPage.tsx (or a global CSS entry point):
```typescript
import 'react-grid-layout/css/styles.css'
import 'react-grid-layout/css/resizable.css'
```
**Warning signs:** Items stack at top-left on initial render.

### Pitfall 2: Grid Layout `i` Key Must Be String
**What goes wrong:** react-grid-layout silently drops items or throws key warnings.
**Why it happens:** The `i` field in layout items must be a string; block IDs from DB are numbers.
**How to avoid:** Always convert: `i: block.id.toString()`. When reconciling after API response, convert back: `parseInt(item.i)`.

### Pitfall 3: Autosave Race on Concurrent Drag + Content Edit
**What goes wrong:** A block's content edit saves after its grid_position was updated, overwriting with a stale `grid_position`.
**Why it happens:** Two separate debounce timers fire independently.
**How to avoid:** Use a single Zustand store slice with a unified dirty state. The `flushSave` function reads all pending dirty blocks in a single pass and PUTs each one with both content and grid_position together.

### Pitfall 4: AppStatus.should_exit_event Cross-Loop Error in SSE Tests
**What goes wrong:** `anyio.Event` created in one test loop is used in the next test, causing `RuntimeError: Event loop is closed`.
**Why it happens:** sse-starlette 2.x stores a class-level event. TestClient creates a new event loop per test.
**How to avoid:** Add `AppStatus.should_exit_event = None` before each SSE test (established pattern from Phase 12/13 tests in STATE.md).

### Pitfall 5: TipTap v3 Import Paths Changed from v2
**What goes wrong:** `@tiptap/react` imports that worked in v2 (`useEditor`, `EditorContent`) exist in v3 but extension API has changed.
**Why it happens:** v3 released with breaking changes in extension configuration.
**How to avoid:** Import directly from `@tiptap/react` and `@tiptap/starter-kit`. Avoid copying v2 snippets from older blog posts. Check official TipTap v3 migration guide.

### Pitfall 6: react-grid-layout Width Must Be Set Explicitly
**What goes wrong:** Grid collapses to 0px width; items invisible.
**Why it happens:** `GridLayout` needs an explicit `width` prop. Use `react-grid-layout/lib/ResponsiveGridLayout` or measure the container with a ResizeObserver.
**How to avoid:** For the slide canvas, use a fixed width (e.g. 960px) matching the slide aspect ratio. Wrap in a container div and use `react-use` or a simple ResizeObserver hook if responsive width is needed.

### Pitfall 7: Slide Outline Wizard JSON Parsing from SSE Stream
**What goes wrong:** AI returns JSON as streamed tokens; partial JSON cannot be parsed mid-stream.
**Why it happens:** SSE yields tokens one by one; JSON is only valid when complete.
**How to avoid:** Accumulate all tokens into a string buffer during streaming. Only attempt `JSON.parse()` on stream completion (`done === true`). Show a progress/spinner during generation; show the parsed result in step 3 preview after completion.

### Pitfall 8: Block Content Varies by Type — No Unified Schema
**What goes wrong:** Trying to use one generic content form for all block types.
**Why it happens:** Each block type has different content structure (text has `html`, image has `url`+`caption`, code has `language`+`code`, etc.).
**How to avoid:** Define a `BlockContentSchema` type union keyed by block type. Use a `BlockRenderer` component that switches on `block.type` and renders the appropriate editor. Each block editor owns its content schema.

---

## Code Examples

### Creating a Block on Drop to Canvas

```typescript
// Source: react-grid-layout drop pattern + blocks API
const handleDrop = async (layout: Layout[], item: Layout, _event: Event) => {
  const blockType = draggedBlockType  // from drag-start state
  const defaultSize = BLOCK_DEFAULTS[blockType]  // { w: 6, h: 3 }

  const newBlock = await api.post(`/slides/${slideId}/blocks`, {
    type: blockType,
    content: getDefaultContent(blockType),
    grid_position: { x: item.x, y: item.y, w: defaultSize.w, h: defaultSize.h },
    order_index: 0,
  }).then(r => r.json())

  addBlock(newBlock)  // Zustand store
}
```

### Persisting Grid Position on Drag/Resize Stop

```typescript
// Source: react-grid-layout onDragStop / onResizeStop callback pattern
const handleDragStop = async (_layout: Layout[], _old: Layout, newItem: Layout) => {
  const blockId = parseInt(newItem.i)
  const grid_position = { x: newItem.x, y: newItem.y, w: newItem.w, h: newItem.h }

  // Update store immediately (optimistic)
  updateBlock(blockId, { grid_position })

  // Persist to API (no debounce — this is a terminal event, fire immediately)
  await api.put(`/blocks/${blockId}`, { grid_position })
}
```

### Thumbnail Strip with dnd-kit Sortable (reuses Phase 13 pattern)

```typescript
// Source: @dnd-kit/sortable — same pattern as ModuleOverviewList.tsx
import { SortableContext, verticalListSortingStrategy, useSortable } from '@dnd-kit/sortable'
import { DndContext, closestCenter } from '@dnd-kit/core'

// Reorder commits: send full sibling ID array in single request (STATE.md pattern)
const handleDragEnd = (event: DragEndEvent) => {
  const { active, over } = event
  if (!over || active.id === over.id) return
  const newOrder = arrayMove(slides, oldIndex, newIndex)
  setSlides(newOrder)  // optimistic
  api.post(`/videos/${videoId}/slides/reorder`, {
    slide_ids: newOrder.map(s => s.id)
  })
}
```

### Backend: New SSE Endpoint in slides.py

```python
# Source: modules.py generate-description pattern (Phase 13)
# MUST be declared BEFORE the /{slide_id} wildcard route

claude_service = ClaudeService()  # module-level singleton

class AiNarrationRequest(BaseModel):
    tone_preset: Optional[str] = "professional"

@router.post("/api/slides/{slide_id}/ai/generate-narration")
async def generate_narration(
    slide_id: int,
    body: AiNarrationRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_creator),
):
    slide = _get_slide_or_404_for_sse(slide_id, db, current_user)
    blocks = db.query(Block).filter(Block.slide_id == slide.id).all()
    block_text = " ".join(
        str(b.content.get("text") or b.content.get("html") or "")
        for b in blocks if b.content
    )
    prompt = (
        f"Write a narration script for a slide with the following content: {block_text}. "
        f"Tone: {body.tone_preset}. Be concise, 2-4 sentences."
    )

    async def event_generator():
        async for token in claude_service._stream_text(prompt):
            if await request.is_disconnected():
                break
            yield {"data": token}

    return EventSourceResponse(event_generator())
```

### Block Default Sizes by Type

```typescript
// Prescriptive defaults — use exactly these for consistent initial layout
const BLOCK_DEFAULTS: Record<string, { w: number; h: number }> = {
  heading:     { w: 12, h: 2 },
  text:        { w: 8,  h: 4 },
  image:       { w: 6,  h: 5 },
  video_embed: { w: 8,  h: 5 },
  code:        { w: 8,  h: 6 },
  quote:       { w: 8,  h: 3 },
  list:        { w: 6,  h: 5 },
  callout:     { w: 12, h: 3 },
  divider:     { w: 12, h: 1 },
}
```

### Layout Presets

```typescript
// Layout presets define initial block arrangements applied when user picks a preset
// Applying a preset = delete all current blocks, create new blocks from preset template
const LAYOUT_PRESETS = {
  'title-content': [
    { type: 'heading', grid_position: { x: 0, y: 0, w: 12, h: 2 } },
    { type: 'text',    grid_position: { x: 0, y: 2, w: 12, h: 6 } },
  ],
  'two-column': [
    { type: 'text',  grid_position: { x: 0, y: 0, w: 6, h: 8 } },
    { type: 'image', grid_position: { x: 6, y: 0, w: 6, h: 8 } },
  ],
  'full-bleed-image': [
    { type: 'image',   grid_position: { x: 0, y: 0, w: 12, h: 8 } },
    { type: 'heading', grid_position: { x: 1, y: 8, w: 10, h: 2 } },
  ],
  'blank': [],
}
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `EventSource` for SSE | `fetch + ReadableStream` | Project decision (Phase 12) | Enables POST endpoints, auth headers |
| Function-local `ClaudeService()` | Module-level singleton | Phase 12 decision | Prevents re-instantiation per request |
| Block CRUD via ad-hoc JS | Existing `/api/slides/{id}/blocks` API | Phase 11 | API fully available; no backend work needed for basic CRUD |
| dnd-kit for canvas | react-grid-layout for canvas | STATE.md locked | Grid snapping, resize handles, collision detection |

**Deprecated/outdated:**
- `onDrag`/`onResize` for position persistence: use `onDragStop`/`onResizeStop` only
- TipTap v2 examples: v3 has breaking changes; use official v3 docs

---

## Open Questions

1. **Block content HTML sanitisation**
   - What we know: TipTap produces HTML strings for text/heading blocks; stored in `content.html`
   - What's unclear: Whether DOMPurify or similar is needed server-side before storing
   - Recommendation: Phase 14 can skip sanitisation (creator-only surface, not learner-facing); add DOMPurify in Phase 18 Preview when learners see the content

2. **Slide thumbnail rendering**
   - What we know: SLIDE-01 requires a "thumbnail strip" for slides
   - What's unclear: Whether thumbnails are visual previews (expensive to render) or just title/number labels
   - Recommendation: Use title + slide number label thumbnails. True CSS mini-preview (scaled-down canvas) can be added later. Requirements say "thumbnail strip" not "thumbnail images."

3. **Bulk narration trigger (SLIDE-03)**
   - What we know: SLIDE-03 is "bulk narration audio generation" — TTS is Phase 17
   - What's unclear: Does Phase 14 implement the UI button only (disabled, or "coming soon"), or does it need a backend endpoint?
   - Recommendation: Phase 14 implements the button UI in the slide strip with a disabled state and tooltip "Audio generation available after narration scripts are written." The backend TTS endpoint is Phase 17. The planner should wire only the frontend affordance now.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | vitest 2.1.8 (frontend) + pytest 8.1.1 (backend) |
| Config file | `frontend/vitest.config.ts` (exists) / `backend/tests/conftest.py` (exists) |
| Quick run command | `cd frontend && npm run test:unit` / `cd backend && source venv/bin/activate && python -m pytest tests/test_slides_phase14.py -x` |
| Full suite command | `cd frontend && npm run test:unit` / `cd backend && source venv/bin/activate && python -m pytest tests/ -x` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SLIDE-01 | SlideBuilderPage renders slide strip for a video | unit (vitest) | `npm run test:unit -- SlideBuilderPage` | Wave 0 |
| SLIDE-02 | Add, reorder, duplicate, delete slides from strip | unit (vitest) | `npm run test:unit -- VideoSlideStrip` | Wave 0 |
| SLIDE-03 | Bulk narration button visible (disabled state) | unit (vitest) | `npm run test:unit -- VideoSlideStrip` | Wave 0 |
| SLIDE-04 | SlideEditorPage route renders for a slide | unit (vitest) | `npm run test:unit -- SlideEditorPage` | Wave 0 |
| SLIDE-05 | Dropping a block type creates a block via API | unit (vitest + mock) | `npm run test:unit -- SlideCanvas` | Wave 0 |
| SLIDE-06 | onDragStop fires PUT /blocks/{id} with grid_position | unit (vitest + mock) | `npm run test:unit -- SlideCanvas` | Wave 0 |
| SLIDE-07 | Undo/redo 20-step history in store | unit (vitest) | `npm run test:unit -- slideEditorStore` | Wave 0 |
| SLIDE-08 | isDirty triggers autosave; navigation blocked when dirty | unit (vitest) | `npm run test:unit -- SlideEditorPage` | Wave 0 |
| SLIDE-09 | Applying layout preset replaces canvas blocks | unit (vitest + mock) | `npm run test:unit -- LayoutPresetPicker` | Wave 0 |
| SLIDE-10 | Narration script textarea persists to PUT /slides/{id} | unit (vitest + mock) | `npm run test:unit -- NarrationTab` | Wave 0 |
| SLIDE-11 | POST /api/slides/{id}/ai/generate-narration streams tokens | integration (pytest) | `python -m pytest tests/test_slides_phase14.py::test_generate_narration_streams_tokens` | Wave 0 |
| SLIDE-12 | Slide outline wizard completes 4 steps and commits slides | unit (vitest + mock) | `npm run test:unit -- SlideOutlineWizard` | Wave 0 |

### Sampling Rate

- **Per task commit:** `npm run test:unit` (frontend) or `python -m pytest tests/test_slides_phase14.py -x` (backend)
- **Per wave merge:** Full `npm run test:unit` + `python -m pytest tests/ -x`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `frontend/src/pages/creator/__tests__/SlideBuilderPage.test.tsx` — covers SLIDE-01, SLIDE-02, SLIDE-03
- [ ] `frontend/src/pages/creator/__tests__/SlideEditorPage.test.tsx` — covers SLIDE-04, SLIDE-05, SLIDE-06, SLIDE-07, SLIDE-08
- [ ] `frontend/src/components/slide/__tests__/NarrationTab.test.tsx` — covers SLIDE-10, SLIDE-11
- [ ] `frontend/src/components/slide/__tests__/SlideOutlineWizard.test.tsx` — covers SLIDE-12
- [ ] `frontend/src/store/__tests__/slideEditorStore.test.ts` — covers SLIDE-07
- [ ] `backend/tests/test_slides_phase14.py` — covers SLIDE-11 (SSE endpoint integration)
- [ ] Framework installs: `npm install react-grid-layout zustand @tiptap/react @tiptap/starter-kit @types/react-grid-layout` — required before any implementation

---

## Route Map for App.tsx

Two new creator routes needed (add to App.tsx alongside existing creator routes):

```
/creator/courses/:id/videos/:videoId/slides           → SlideBuilderPage (wrapped in CreatorLayout + ProtectedRoute creatorRoute)
/creator/courses/:id/videos/:videoId/slides/:slideId/editor  → SlideEditorPage (wrapped in CreatorLayout + ProtectedRoute creatorRoute)
```

Navigation from CourseBuilderPage/CourseTreeRail: clicking a video of type `slideshow_narrated` should route to the SlideBuilderPage. This requires adding video click handlers in CourseTreeRail.tsx (currently only module rows are clickable).

---

## Backend API Gap Summary

All block/slide CRUD exists. Two new endpoints needed:

| Endpoint | Method | Purpose | Router File |
|----------|--------|---------|-------------|
| `/api/slides/{slide_id}/ai/generate-narration` | POST SSE | SLIDE-11 | slides.py — add claude_service singleton + EventSourceResponse |
| `/api/slides/{slide_id}/ai/generate-outline` | POST SSE | SLIDE-12 (generation step) | slides.py — returns JSON outline as streamed text |

Both follow the exact `modules.py` generate-description pattern. Both must be declared BEFORE the `GET /api/slides/{slide_id}` wildcard.

---

## Sources

### Primary (HIGH confidence)

- STATE.md — locked decisions: react-grid-layout for canvas, dnd-kit for strip, TipTap v3, Zustand 5, SSE pattern, autosave pitfall
- Existing codebase: `backend/routers/slides.py`, `backend/routers/blocks.py`, `backend/models/models.py` — all CRUD endpoints confirmed present
- Existing codebase: `frontend/src/pages/creator/ModuleDetailPage.tsx` — SSE streaming pattern confirmed working
- Existing codebase: `backend/routers/modules.py` — SSE endpoint pattern, claude_service singleton, AppStatus reset

### Secondary (MEDIUM confidence)

- react-grid-layout npm package not yet installed; API confirmed via official docs pattern (cols, layout, onDragStop, onResizeStop)
- Zustand 5 temporal middleware (zundo) — documented pattern from Zustand ecosystem; may use `zustand/middleware/temporal` directly in Zustand 5.x

### Tertiary (LOW confidence)

- TipTap v3 breaking changes from v2 — flagged as pitfall; verify against official TipTap v3 migration guide before writing block editors

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all locked in STATE.md
- Architecture: HIGH — backend APIs fully exist; frontend structure follows established Phase 13 patterns exactly
- react-grid-layout specifics: MEDIUM — not yet installed; API pattern well-established but CSS import requirement and width requirement are known gotchas
- TipTap v3: MEDIUM — breaking changes from v2 documented as known risk; use official v3 docs during implementation
- Pitfalls: HIGH — autosave race, SSE path collision, AppStatus reset all confirmed from prior phases

**Research date:** 2026-05-09
**Valid until:** 2026-06-09 (stable libraries; SSE pattern locked by project convention)
