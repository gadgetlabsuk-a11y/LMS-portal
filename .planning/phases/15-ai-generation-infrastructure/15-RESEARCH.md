# Phase 15: AI Generation Infrastructure - Research

**Researched:** 2026-05-09
**Domain:** SSE streaming unification, document ingestion, AI suggestions rail, tone propagation
**Confidence:** HIGH (all findings verified against existing codebase + locked decisions from STATE.md)

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| AI-01 | All AI generation uses SSE streaming (POST endpoint; `fetch` + `ReadableStream` on client — not `EventSource`) | 4 existing ad-hoc fetch+ReadableStream implementations identified; pattern is consistent and extractable |
| AI-02 | A single reusable AI generation drawer (`SideDrawer` + `StreamingTextOutput`) is used across all generation surfaces | No SideDrawer or StreamingTextOutput component exists yet; all 4 ad-hoc streaming implementations can be replaced |
| AI-03 | Creator can generate a slide outline from a prompt or uploaded document (document ingestion pipeline) | SlideOutlineWizard already sends prompt+tone_preset to POST /api/slides/{id}/ai/generate-outline; document upload path not yet wired |
| AI-04 | Document ingestion supports PDF and DOCX upload → Claude parses → returns module/slide structure | DOCX extraction already works via python-docx. PDF extraction is broken (raw UTF-8 decode). PyMuPDF NOT installed — must add to requirements.txt |
| AI-05 | SSE generator checks `request.is_disconnected()` on every yield to prevent orphaned tokens | All 3 backend SSE routers already call `await request.is_disconnected()` — confirmed in courses.py, modules.py, slides.py. Pattern verified. |
| AI-06 | Creator sees AI suggestions rail in Course Builder (proactive completeness nudges: missing descriptions, empty modules, etc.) | CourseBuilderPage already fetches full module+video+quiz tree; suggestions rail needs new component reading that data — no backend endpoint needed |
| AI-07 | AI tone preset from Modal 1A is passed as context to all AI generation calls for that course | Course.ai_tone_preset stored in DB; frontend currently hardcodes 'professional' in ModuleDetailPage, NarrationTab. Must propagate from course fetch to each generation call. |
</phase_requirements>

---

## Summary

Phase 15 is primarily a **refactoring and wiring phase** — the underlying SSE machinery is already working and battle-tested. Four ad-hoc streaming implementations exist across `CourseIdentityModal.tsx`, `ModuleDetailPage.tsx`, `NarrationTab.tsx`, and `SlideOutlineWizard.tsx`. They all use an identical fetch+ReadableStream+TextDecoder+AbortController pattern. The task is to extract that pattern into a reusable `SideDrawer` + `StreamingTextOutput` component pair and route each surface through it.

The biggest new capability is the **document ingestion pipeline for AI-03/AI-04**. DOCX extraction already works via python-docx. The PDF path is broken — it currently raw-decodes file bytes as UTF-8, which produces garbage for binary PDFs. PyMuPDF (`pymupdf`) must be added to `requirements.txt` and `document_service.py._extract_pdf()` must be replaced entirely. PyMuPDF is not currently installed in the backend venv.

The **AI suggestions rail (AI-06)** is a frontend-only component: `CourseBuilderPage` already fetches the full module/video/quiz tree on mount. The suggestions rail simply needs to analyse that already-available data and display completeness nudges — no new backend endpoint is required. The **tone propagation fix (AI-07)** requires fetching `course.ai_tone_preset` alongside other course data and threading it through each generation call; the backend already stores and returns it in `CourseResponse`.

**Primary recommendation:** Implement in this order: (1) PyMuPDF PDF fix, (2) SideDrawer + StreamingTextOutput shared components, (3) wire each existing surface through the shared components, (4) tone propagation, (5) AI suggestions rail.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| sse-starlette | 2.1.3 | Backend EventSourceResponse | Already installed, locked |
| fetch + ReadableStream | browser built-in | Frontend SSE client | Locked — POST SSE requires fetch, not EventSource |
| AbortController | browser built-in | Stream cancellation | Already used in all 4 existing implementations |
| python-docx | 1.1.0 | DOCX text extraction | Already installed, working |
| pymupdf (fitz) | 1.26+ | PDF text extraction | NOT installed — must add to requirements.txt |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Zustand 5 | 5.0.13 | Drawer open/loading state | Already installed; use for shared streaming UI state if drawer is global |
| React 18.3 | built-in | useCallback, useState | All drawer state managed locally per-surface via props |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| PyMuPDF | pdfminer.six, pypdf | PyMuPDF is locked in STATE.md; no exploration needed |
| fetch+ReadableStream | EventSource | EventSource is locked out — no POST support |

**Installation (backend only):**
```bash
pip install pymupdf==1.26.0
# Add to requirements.txt: pymupdf==1.26.0
```

---

## Architecture Patterns

### Recommended Project Structure (new files only)
```
frontend/src/
├── components/
│   └── ai/
│       ├── SideDrawer.tsx          # Slide-out panel, accepts children
│       ├── StreamingTextOutput.tsx # Displays live streaming tokens
│       └── __tests__/
│           ├── SideDrawer.test.tsx
│           └── StreamingTextOutput.test.tsx
backend/
├── services/
│   └── document_service.py         # Fix _extract_pdf() with PyMuPDF
└── tests/
    └── test_ai_phase15.py          # Wave 0 stubs for AI-01 through AI-07
```

### Pattern 1: SideDrawer Component Contract
**What:** A slide-out panel rendered via a portal that accepts title, isOpen, onClose, and children props.
**When to use:** Every AI generation surface — description, objectives, module description, narration, slide outline, quiz questions.

```typescript
// frontend/src/components/ai/SideDrawer.tsx
interface SideDrawerProps {
  isOpen: boolean
  onClose: () => void
  title: string
  children: React.ReactNode
}
// Renders as fixed right-side panel, overlay backdrop, closes on Escape key
// Returns null when isOpen=false (same pattern as Modal.tsx in this codebase)
```

### Pattern 2: StreamingTextOutput Component Contract
**What:** Displays tokens as they arrive; shows a blinking cursor while streaming; exposes the accumulated text via onComplete callback.
**When to use:** Inside SideDrawer for all text generation surfaces.

```typescript
// frontend/src/components/ai/StreamingTextOutput.tsx
interface StreamingTextOutputProps {
  isStreaming: boolean
  text: string              // accumulated tokens from parent
  placeholder?: string
}
// Does NOT own fetch logic — parent owns AbortController + fetch
// Renders text in a pre-wrap div; cursor via CSS animation
```

### Pattern 3: Shared useSSEStream Hook (extracted from 4 existing implementations)
**What:** Encapsulates the fetch+ReadableStream+TextDecoder+AbortController pattern that is currently duplicated in all 4 surfaces.
**When to use:** Called by every AI generation trigger.

```typescript
// Extracted pattern (identical across CourseIdentityModal, ModuleDetailPage,
// NarrationTab, SlideOutlineWizard — source: existing codebase)
const useSSEStream = () => {
  const [text, setText] = useState('')
  const [isStreaming, setIsStreaming] = useState(false)
  const abortRef = useRef<AbortController | null>(null)

  const startStream = async (url: string, body: object, onToken?: (t: string) => void) => {
    abortRef.current?.abort()
    const controller = new AbortController()
    abortRef.current = controller
    setIsStreaming(true)
    setText('')
    try {
      const res = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${localStorage.getItem('token')}`,
        },
        body: JSON.stringify(body),
        signal: controller.signal,
      })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const reader = res.body!.getReader()
      const decoder = new TextDecoder()
      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        const chunk = decoder.decode(value)
        for (const line of chunk.split('\n')) {
          if (line.startsWith('data: ')) {
            const token = line.slice(6)
            setText(prev => prev + token)
            onToken?.(token)
          }
        }
      }
    } catch (e: unknown) {
      if (e instanceof Error && e.name !== 'AbortError') console.error('SSE error:', e)
    } finally {
      setIsStreaming(false)
    }
  }

  const cancel = () => abortRef.current?.abort()
  return { text, isStreaming, startStream, cancel, setText }
}
```

### Pattern 4: PyMuPDF PDF Extraction Replacement
**What:** Replace the broken `_extract_pdf()` raw UTF-8 decode with PyMuPDF's page text extraction.
**When to use:** Only for PDF files in DocumentService.

```python
# backend/services/document_service.py — _extract_pdf replacement
# Source: STATE.md pitfall #7 + PyMuPDF fitz API
import fitz  # pymupdf

@staticmethod
def _extract_pdf(file_bytes: bytes) -> str:
    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        content_parts = []
        for page in doc:
            text = page.get_text()
            if text.strip():
                content_parts.append(text)
        doc.close()
        extracted_text = "\n".join(content_parts)
        if len(extracted_text.strip()) < 100:
            logger.warning("PDF extraction produced minimal text — may be scanned")
        logger.info(f"Extracted text from PDF: {len(extracted_text)} characters")
        return extracted_text
    except Exception as e:
        logger.error(f"Error extracting PDF: {str(e)}")
        raise ValueError(f"Failed to extract text from PDF file: {str(e)}")
```

### Pattern 5: AI Suggestions Rail (frontend-only)
**What:** A right-side rail in CourseBuilderPage that analyses already-fetched module/video/quiz data and displays completeness nudges.
**When to use:** Rendered beside the main builder content area.

```typescript
// frontend/src/components/builder/AISuggestionsRail.tsx
interface AISuggestionsRailProps {
  modules: Module[]
  videos: Record<number, Video[]>
  quizzes: Record<number, Quiz[]>
}
// Nudge rules:
// 1. Module has no description → "Add a description to [module title]"
// 2. Module has no videos/quizzes → "Module [title] is empty — add content"
// 3. Course has 0 modules → "Add your first module to get started"
// Renders as a fixed-width panel (200–280px) using Tailwind classes
// No backend call needed — all data already in CourseBuilderPage state
```

### Pattern 6: Tone Preset Propagation
**What:** CourseBuilderPage (and any page with an AI generation surface) fetches `course.ai_tone_preset` from GET /api/courses/{id} and passes it to each generation call body as `tone_preset`.
**When to use:** ModuleDetailPage, NarrationTab, SlideOutlineWizard — everywhere `tone_preset: 'professional'` is currently hardcoded.

```typescript
// Pattern: fetch course on mount, extract tone
const [tonePreset, setTonePreset] = useState<string>('professional')
useEffect(() => {
  api.get(`/courses/${courseId}`).then(r => r.json()).then(course => {
    setTonePreset(course.ai_tone_preset || 'professional')
  })
}, [courseId])
// Pass to SSE body: { ..., tone_preset: tonePreset }
```

**Important:** `courseId` must flow down via props or useParams into ModuleDetailPage and SlideBuilderPage. ModuleDetailPage already has `courseId` from `useParams`. NarrationTab is inside SlideEditorPage — needs courseId threaded through.

### Pattern 7: Document Upload in SlideOutlineWizard (AI-03/AI-04)
**What:** SlideOutlineWizard Step 1 already has a document upload path in its source selection UI. The document must be uploaded to POST /api/uploads, the returned URL passed to a new or existing backend endpoint that extracts text with DocumentService and feeds it to Claude.
**When to use:** When the user selects "Upload document" in SlideOutlineWizard Step 1.

The existing `POST /api/slides/{id}/ai/generate-outline` endpoint already accepts `prompt` + `tone_preset`. It needs a `document_url` field added (Optional[str]) so the backend can fetch+extract+include the document text in the Claude prompt. This mirrors what `modules.py` already does (`doc_context = f"\nReference document available at: {body.document_url}"`).

**Alternatively (simpler):** Accept the file bytes directly in a multipart request rather than a URL. Given the existing upload architecture (POST /api/uploads → returns URL), the two-step approach (upload first, then pass URL) is consistent with the established pattern.

### Anti-Patterns to Avoid
- **Do not use `EventSource`:** POST endpoints cannot use EventSource — all SSE clients must use `fetch` + `ReadableStream`.
- **Do not create a new SSE backend endpoint for the suggestions rail:** The nudges are derived from already-fetched module tree data, not a stream.
- **Do not mix drawer state into Zustand global store prematurely:** Each surface manages its own drawer open/streaming state locally. Only promote to Zustand if cross-surface coordination is needed (it won't be in Phase 15).
- **Do not hardcode tone_preset as 'professional' anywhere after this phase:** All generation calls must read from the course.ai_tone_preset field.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| PDF text extraction | Custom binary parser, UTF-8 decode | PyMuPDF (fitz) | Binary PDF structure; UTF-8 decode produces garbage for most PDFs |
| DOCX text extraction | Custom XML parser | python-docx (already installed) | DOCX is a zip of XML — python-docx handles all the OOXML complexity |
| SSE connection abort | Custom timeout/polling | AbortController (browser built-in) | Already used correctly in all 4 existing implementations |
| SSE parse | Custom event stream parser | line.startsWith('data: ') slice | sse-starlette always emits `data: {token}\n\n` — simple string split is sufficient |

**Key insight:** The document extraction problem looks simple (files are just text) but PDF is a layout/page-description format — raw UTF-8 decode always fails for real PDFs. PyMuPDF's `page.get_text()` handles the binary structure correctly.

---

## Common Pitfalls

### Pitfall 1: PyMuPDF Not Installed
**What goes wrong:** `import fitz` raises `ModuleNotFoundError` at runtime; document upload endpoint returns 500.
**Why it happens:** PyMuPDF is not in requirements.txt and not in the venv (confirmed by inspection).
**How to avoid:** Add `pymupdf==1.26.0` to requirements.txt in Wave 0 plan (15-01) and install before any document extraction test.
**Warning signs:** `ImportError: No module named 'fitz'` in pytest output.

### Pitfall 2: AppStatus.should_exit_event Cross-Loop RuntimeError in SSE Tests
**What goes wrong:** sse-starlette 2.x creates a class-level `anyio.Event`; TestClient cycles the event loop between tests, causing `RuntimeError: Event loop is closed` on second and subsequent SSE tests.
**Why it happens:** sse-starlette stores state at the class level, not per-request.
**How to avoid:** Add `AppStatus.should_exit_event = None` reset in an `autouse` fixture for all SSE tests — same fix as 12-02 and 13-02 decisions in STATE.md.
**Warning signs:** Tests pass in isolation but fail when run together; error says "Event loop is closed".

### Pitfall 3: SSE Routes Before Wildcard Routes (FastAPI Path Collision)
**What goes wrong:** A POST to `/api/slides/42/ai/generate-outline` matches the GET `/api/slides/{slide_id}` wildcard if routes are declared in the wrong order.
**Why it happens:** FastAPI evaluates routes in declaration order; `{slide_id}` matches any path segment.
**How to avoid:** Declare all `/ai/*` SSE routes BEFORE any `/{resource_id}` wildcard routes — confirmed pattern from 14-02 decision. Already done in slides.py, courses.py, modules.py.
**Warning signs:** 422 Unprocessable Entity or 405 Method Not Allowed on SSE endpoints.

### Pitfall 4: Tone Preset Not Threaded to NarrationTab
**What goes wrong:** NarrationTab is a child of SlideEditorPage which is a child of SlideBuilderPage. The `courseId` is available in SlideBuilderPage via useParams, but NarrationTab does not currently receive `tonePreset` — it will need it as a prop or the course must be fetched within NarrationTab.
**Why it happens:** Component tree depth; tone context was not considered during Phase 14.
**How to avoid:** Pass `tonePreset` as a prop from SlideBuilderPage → SlideEditorPage → NarrationTab. Alternatively, NarrationTab can do a one-shot GET /api/courses/{courseId} fetch. The prop threading is simpler and avoids an extra API call.
**Warning signs:** NarrationTab generates text in 'professional' tone regardless of course setting.

### Pitfall 5: DOCX Document Bytes vs URL
**What goes wrong:** `DocxDocument(file_bytes)` in the current DOCX extractor passes raw bytes, but python-docx's `Document()` constructor expects a file-like object (BytesIO), not raw bytes.
**Why it happens:** API misunderstanding — `Document(bytes)` tries to open as a path string.
**How to avoid:** Wrap bytes in `io.BytesIO(file_bytes)` before passing to `DocxDocument`. Check if the existing code already does this (the current code passes `file_bytes` directly — this may be a latent bug that only surfaces when testing the new document upload path).
**Warning signs:** `BadZipFile` or `TypeError` when extracting DOCX from upload.

### Pitfall 6: SideDrawer Blocks Scrollable Content
**What goes wrong:** A fixed-position drawer that overlays the main content area can trap scroll focus or cause layout shifts.
**Why it happens:** CSS fixed positioning and z-index stacking.
**How to avoid:** Use `position: fixed; right: 0; top: 0; height: 100%` with an overlay backdrop div. The Modal.tsx in this codebase uses a similar pattern — follow it.

### Pitfall 7: Partial-JSON Parse in Slide Outline Wizard
**What goes wrong:** SlideOutlineWizard accumulates SSE tokens into a buffer and JSON.parses on completion. If the document extraction produces noisy text that causes Claude to output extra prose, the JSON parse will fail.
**Why it happens:** Claude sometimes wraps JSON in prose if the prompt is ambiguous.
**How to avoid:** The existing `_parse_course_content()` in `claude_service.py` already handles markdown-wrapped JSON (extracts from ` ```json ` blocks). Use the same extraction logic in the outline generation prompt and handler. The SlideOutlineWizard already accumulates all tokens before parsing (confirmed from 14-05 decision in STATE.md) — maintain this pattern.

---

## Code Examples

Verified patterns from existing codebase:

### Existing SSE Backend Pattern (slides.py — confirmed)
```python
# Source: backend/routers/slides.py (confirmed in codebase)
async def generator():
    async for token in claude_service._stream_text(full_prompt):
        if await request.is_disconnected():
            break
        yield {"data": token}

return EventSourceResponse(generator())
```

### Existing SSE Frontend Pattern (CourseIdentityModal.tsx — confirmed)
```typescript
// Source: frontend/src/components/course/CourseIdentityModal.tsx
const controller = new AbortController()
const res = await fetch(`${API_BASE}/api/courses/ai/generate-description`, {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    Authorization: `Bearer ${localStorage.getItem('token')}`,
  },
  body: JSON.stringify({ topic: title, tone_preset: tonePreset || 'professional' }),
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
```

### AppStatus Reset for SSE Tests (from STATE.md decisions)
```python
# Source: STATE.md decision from 12-02 / 13-02
@pytest.fixture(autouse=True)
def reset_sse_state():
    from sse_starlette.sse import AppStatus
    AppStatus.should_exit_event = None
    yield
```

### Course ai_tone_preset Access (confirmed in models.py)
```python
# Course model column: ai_tone_preset = Column(String(50), nullable=True)
# CourseResponse includes ai_tone_preset: Optional[str]
# Frontend: course.ai_tone_preset from GET /api/courses/{id}
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Raw UTF-8 decode for PDF | PyMuPDF fitz page.get_text() | Phase 15 (this phase) | Enables real PDF text extraction |
| Ad-hoc inline SSE fetch | useSSEStream hook + SideDrawer | Phase 15 (this phase) | Removes ~80 lines of duplicated fetch/stream logic |
| Hardcoded 'professional' tone | Course.ai_tone_preset fetched and propagated | Phase 15 (this phase) | Tone setting from Modal 1A actually affects generation |

**Confirmed working (no changes needed):**
- `request.is_disconnected()` check: already in all 3 backend SSE routers (courses.py, modules.py, slides.py)
- DOCX extraction: python-docx already installed and working
- SSE route ordering: already correct in all routers
- sse-starlette EventSourceResponse: already used correctly

---

## Open Questions

1. **DocxDocument bytes vs BytesIO**
   - What we know: `document_service.py` line 58 calls `DocxDocument(file_bytes)` with raw bytes
   - What's unclear: Whether python-docx accepts raw bytes or requires BytesIO — the existing code has never been tested with the new upload path
   - Recommendation: In 15-02, test DOCX extraction first; if it fails with TypeError, wrap in `io.BytesIO(file_bytes)`

2. **Document upload endpoint for SlideOutlineWizard**
   - What we know: POST /api/uploads exists and returns a URL. POST /api/slides/{id}/ai/generate-outline accepts `prompt` + `tone_preset`.
   - What's unclear: Should document text extraction happen client-side (upload → get URL → pass URL to outline endpoint, backend fetches+extracts) or should the wizard upload the file directly to the outline endpoint as multipart?
   - Recommendation: Two-step approach (upload first → pass URL) is consistent with the established `document_url` pattern in modules.py and aligns with the existing upload infrastructure. Add `document_url: Optional[str]` to the outline request body.

3. **SideDrawer placement relative to CourseIdentityModal**
   - What we know: CourseIdentityModal already has inline streaming for description + objectives. AI-02 requires these to migrate to the shared SideDrawer.
   - What's unclear: The modal + drawer combination might feel cluttered — a drawer inside a modal is unconventional.
   - Recommendation: For CourseIdentityModal specifically, the drawer can open over/above the modal (higher z-index). Alternatively, the modal streaming targets could remain inline (text updates in-place) while the drawer is used for all standalone generation surfaces (Module Detail, NarrationTab, Slide Outline Wizard). Check the spec — AI-02 says "all generation surfaces" use the same drawer. Implement literally.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (backend) + vitest (frontend) |
| Config file | `backend/pytest.ini` or inline; `frontend/vitest.config.ts` |
| Quick run command (backend) | `cd backend && source venv/bin/activate && python -m pytest tests/test_ai_phase15.py -x` |
| Quick run command (frontend) | `cd frontend && npm run test -- --run src/components/ai/` |
| Full suite command (backend) | `cd backend && source venv/bin/activate && python -m pytest tests/ -x` |
| Full suite command (frontend) | `cd frontend && npm run test -- --run` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| AI-01 | SSE endpoints return `text/event-stream`; client reads via ReadableStream | integration | `pytest tests/test_ai_phase15.py::test_sse_courses_returns_event_stream -x` | ❌ Wave 0 |
| AI-02 | SideDrawer renders with title; StreamingTextOutput shows tokens; existing surfaces use shared component | unit | `npm run test -- --run src/components/ai/SideDrawer.test.tsx` | ❌ Wave 0 |
| AI-03 | Slide outline can be generated from document URL | integration | `pytest tests/test_ai_phase15.py::test_outline_from_document -x` | ❌ Wave 0 |
| AI-04 | PDF extraction via PyMuPDF returns non-empty text; DOCX extraction returns text | unit | `pytest tests/test_ai_phase15.py::test_pdf_extraction_pymupdf -x` | ❌ Wave 0 |
| AI-05 | SSE generator yields no tokens after is_disconnected returns True | unit | `pytest tests/test_ai_phase15.py::test_sse_stops_on_disconnect -x` | ❌ Wave 0 |
| AI-06 | Suggestions rail shows nudge for module with no description | unit | `npm run test -- --run src/components/builder/AISuggestionsRail.test.tsx` | ❌ Wave 0 |
| AI-07 | Tone preset from course propagates to generation call body | unit | `pytest tests/test_ai_phase15.py::test_tone_preset_in_prompt` + `npm run test -- --run src/pages/creator/ModuleDetailPage.test.tsx` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** Quick run for the specific test file changed
- **Per wave merge:** Full suite command
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `backend/tests/test_ai_phase15.py` — covers AI-01, AI-03, AI-04, AI-05, AI-07 (backend)
- [ ] `frontend/src/components/ai/SideDrawer.test.tsx` — covers AI-02
- [ ] `frontend/src/components/ai/StreamingTextOutput.test.tsx` — covers AI-02
- [ ] `frontend/src/components/builder/AISuggestionsRail.test.tsx` — covers AI-06
- [ ] `pymupdf==1.26.0` in `requirements.txt` and installed in venv — required for AI-04

---

## Sources

### Primary (HIGH confidence)
- Existing codebase (`backend/services/document_service.py`) — confirmed raw UTF-8 PDF decode is broken
- Existing codebase (`backend/services/claude_service.py`) — confirmed `_stream_text()` method signature and SSE token format
- Existing codebase (`backend/routers/courses.py`, `modules.py`, `slides.py`) — confirmed `is_disconnected()` pattern, SSE route ordering, tone_preset usage
- Existing codebase (`frontend/src/components/course/CourseIdentityModal.tsx`) — confirmed SSE fetch pattern to extract into hook
- STATE.md decisions — locked decisions, known pitfalls, all verified against current code

### Secondary (MEDIUM confidence)
- PyMuPDF API (`fitz.open(stream=bytes, filetype="pdf")`, `page.get_text()`) — standard API documented at pymupdf.readthedocs.io; confirmed pattern consistent with STATE.md pitfall #7 guidance

### Tertiary (LOW confidence)
- None — all phase 15 claims are grounded in verified codebase inspection or locked STATE.md decisions

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries confirmed in requirements.txt or locked in STATE.md; PyMuPDF absence confirmed by venv inspection
- Architecture: HIGH — patterns extracted directly from existing ad-hoc implementations in the codebase
- Pitfalls: HIGH — all pitfalls either confirmed by existing code inspection or carried forward from STATE.md decisions that were verified in prior phases

**Research date:** 2026-05-09
**Valid until:** 2026-07-09 (stable stack; Python/React library APIs unlikely to change)
