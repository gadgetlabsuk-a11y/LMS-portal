# Stack Research

**Domain:** LMS AI Course Builder — Vite+React migration + drag-drop slide editor + TTS + AI streaming
**Researched:** 2026-05-08
**Confidence:** HIGH (all critical choices verified via official docs or current npm/PyPI)

---

## Context: What Already Exists (DO NOT RE-RESEARCH)

| Layer | Technology | Notes |
|-------|------------|-------|
| Backend | FastAPI 0.104 + SQLAlchemy 2.0 + Python 3.14 | Keep as-is |
| Auth | python-jose JWT + passlib bcrypt | Keep as-is |
| AI | claude_service.py (Anthropic Claude) | Extend, don't replace |
| Doc parsing | python-docx 1.1.0 already installed | Already present |
| Frontend (current) | Single-file index.html + Babel standalone + CDN React 18 | Being replaced |
| Serving | nginx via nixpacks staticfile provider on Coolify | Keep serving strategy |
| Routing | Traefik stripprefix at /lms | No change needed — Traefik strips /lms before nginx sees it |

---

## Recommended Stack — New Additions Only

### Core Frontend Build System

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| Vite | 6.x | Build tool, dev server, HMR | Fastest cold start and HMR in class; official React plugin; `base` config handles /lms subpath cleanly |
| React | 18.3.x | UI framework | Already proven in this codebase; React 19 is out but ecosystem lag is real, stay on 18.3 for v1 |
| TypeScript | 5.x | Type safety | dnd-kit, TipTap, TanStack Query all ship first-class TypeScript; prevents block/slide data model bugs |
| react-router-dom | 6.28.x | SPA routing | v7 Framework mode adds complexity with no benefit here; v6 with createBrowserRouter is sufficient |

**Vite base config for /lms subpath:**
```typescript
// vite.config.ts
export default defineConfig({
  base: '/lms/',          // trailing slash required by Vite
  plugins: [react()],
  // ...
})

// main.tsx — router gets import.meta.env.BASE_URL (resolves to '/lms/')
const router = createBrowserRouter(routes, {
  basename: import.meta.env.BASE_URL.replace(/\/$/, ''), // strip trailing slash for RR
})
```
Note: Traefik stripprefix removes /lms before the request reaches nginx, so nginx still serves from /. Vite `base` is only needed so asset URLs in the built HTML point to `/lms/assets/...` correctly before Traefik strips.

---

### Component Library

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| shadcn/ui | latest (copy-paste) | Base UI components (buttons, dialogs, tabs, tooltips, modals, sliders, etc.) | Components are copied into the repo — no vendor lock-in. Built on Radix UI primitives (fully accessible). Tailwind-based so consistent with existing CDN Tailwind usage. Best choice for LMS admin dashboard patterns per 2025 comparisons. |
| Tailwind CSS | 3.4.x | Utility styling | Already used via CDN in current app. Vite build switches CDN to proper PostCSS pipeline. |
| Radix UI | (via shadcn) | Accessible primitives for dialog, dropdown, tooltip etc. | shadcn bundles this — no separate install needed |

**NOT Mantine:** Mantine is strong for dashboards but the existing app already uses Tailwind; mixing Mantine's CSS-in-JS system would create conflicts. shadcn/Tailwind is the coherent path forward.

---

### Drag and Drop

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| @dnd-kit/core | ^6.3.x | Drag-drop engine | 2.8M weekly downloads; TypeScript-first; accessible; ~6KB core; actively maintained. react-beautiful-dnd is deprecated. |
| @dnd-kit/sortable | ^10.0.0 | Sortable lists (modules, slides, quiz questions) | Official preset for the vertical/horizontal list reorder pattern used in Course Builder, Slide Builder, Quiz Builder |
| @dnd-kit/utilities | ^3.2.x | CSS transforms for drag animations | Required companion for sortable |

**Use dnd-kit for:** module card reordering, slide thumbnail strip reordering, quiz question reordering, module overview content interleaving.

**Do NOT use dnd-kit for:** the slide canvas grid (blocks on a 12-column canvas). That requires a different approach — see Canvas Grid below.

---

### Slide Canvas Grid (Block Placement)

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| react-grid-layout | ^1.4.x | Resizable/draggable grid for slide canvas | Purpose-built for snap-to-grid placement of resizable blocks — exactly the 12-column canvas described in spec section 4.8. Ships its own drag system so dnd-kit should NOT be applied to canvas blocks. |

`react-grid-layout` provides the `grid_position (x, y, width, height)` model described in the Block data model exactly. It handles collision detection, resize handles, and snap grid natively.

---

### Rich Text Editor

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| @tiptap/react | ^3.22.x | Rich text editing for course/module/video descriptions, quiz question prompts | 1.8M monthly downloads; TypeScript; extension-based (only install what you need); ProseMirror underneath; best-in-class accessibility; actively developed (v3 current as of 2026). Quill is legacy. Plate.js is React-only and collaboration story is weaker. |
| @tiptap/pm | ^3.22.x | ProseMirror peer dependency | Required companion |
| @tiptap/starter-kit | ^3.22.x | Paragraphs, headings, bold, italic, lists, code blocks, blockquote | Covers ~90% of needed formatting for descriptions |
| @tiptap/extension-image | ^3.22.x | Image paste support in descriptions | Spec requires "image paste" in RichTextEditor component |
| @tiptap/extension-link | ^3.22.x | Link insert in rich text | Needed for description fields |
| @tiptap/extension-code-block-lowlight | ^3.22.x | Syntax-highlighted code blocks in slide content | Spec section 4.8 includes code block type |
| lowlight | ^3.x | Syntax highlighting engine for code blocks | Peer dependency of extension above |

**Scope:** TipTap is used for description fields (course/module/video) and quiz question prompts. It is NOT used for the slide canvas — blocks on the slide canvas are individual components, not a document editor.

---

### File Upload

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| react-dropzone | ^15.0.0 | File upload zones (document ingestion, image upload, video upload, thumbnail) | 4.5K dependents; hook-based; handles multi-format validation, file type filtering, drag+click; actively maintained. |

`react-dropzone` handles the `DragDropZone` component spec from section 8. It is separate from dnd-kit — react-dropzone handles file drops from the OS, dnd-kit handles UI element reordering.

---

### State Management

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| Zustand | ^5.0.x | Global client state (active course, slide editor state, AI generation status, streaming state) | 5.0.13 current; tiny (no provider wrapper); TypeScript-first; handles the streaming AI response state and multi-level editor state (course > module > video > slide) without Redux boilerplate. Redux Toolkit is overkill for this team size. |
| @tanstack/react-query | ^5.x | Server state (API data fetching, caching, mutations) | Separates server state from UI state cleanly. Handles cache invalidation when AI generation updates course data. Mutations with optimistic updates suit the autosave pattern. SWR is lighter but TanStack Query's mutation + invalidation API is needed for the nested CRUD pattern. |

**Pattern:** Zustand for editor UI state (which slide is selected, canvas drag state, streaming output buffer). TanStack Query for all API calls (courses, modules, slides, etc.). Do not put API data in Zustand.

---

### AI Streaming (SSE)

| Technology | Stack | Purpose | Why Recommended |
|------------|-------|---------|-----------------|
| sse-starlette | ^2.x (Python) | FastAPI SSE endpoint for streaming AI responses | 204K weekly downloads; purpose-built EventSourceResponse for Starlette/FastAPI; W3C compliant; handles client disconnect cleanly. Already compatible with existing FastAPI version. |
| Native EventSource / fetch + ReadableStream | Browser built-in | SSE client in React | No library needed. For simple SSE: `new EventSource(url)`. For POST-based SSE (needed here since AI requests send JSON body): use `fetch` with `ReadableStream` + custom hook. EventSource only supports GET. |

**Pattern for POST SSE:**
```typescript
// React hook — no extra library needed
const response = await fetch('/api/ai/generate', {
  method: 'POST', body: JSON.stringify(payload),
  headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` }
})
const reader = response.body!.getReader()
// decode chunks, update Zustand streaming state
```

---

### TTS Provider — Recommendation: OpenAI TTS

**Decision: OpenAI TTS (`tts-1` / `tts-1-hd`)**

| Provider | Cost | Quality | Voices | Integration |
|----------|------|---------|--------|-------------|
| OpenAI TTS | $15/1M chars (tts-1), $30/1M (tts-1-hd) | Good; acceptable for e-learning narration | 11 preset voices | 1 API key already likely present for Claude fallback; Python SDK |
| ElevenLabs | Credit-based (premium); higher naturalness scores (81.97% pronunciation accuracy vs OpenAI 39.25% context accuracy) | Best quality | 4,000+ voices, voice cloning | Separate API key and billing |
| Azure Speech | $15-30/1M chars; 500+ voices | Good, enterprise-grade | Best for enterprise/compliance | Extra vendor |

**Rationale:** The existing codebase uses Anthropic Claude via `claude_service.py`. OpenAI TTS requires a separate OpenAI API key but is the lowest-friction option: one SDK (`openai` Python package), standard REST, no new billing relationship if you already have OpenAI access. Quality is sufficient for LMS narration. If voice quality proves insufficient post-testing, ElevenLabs is the upgrade path — design the `NarrationService` abstraction layer so the provider is swappable.

**OPEN QUESTION for Stuart:** Do you have an OpenAI API key already, or does the project use only Anthropic? If Anthropic-only, ElevenLabs is the recommendation (best quality narration, simple REST API). Leave the TTS provider config in environment variables, not hardcoded.

Backend addition needed:
```
openai>=1.30.0   # for TTS; also provides gpt-4o-mini-tts option
# OR
elevenlabs>=1.0  # if ElevenLabs chosen
```

---

### Document Ingestion (Backend)

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| PyMuPDF (fitz) | ^1.26.x | PDF text extraction | 6x faster than pdfminer.six; comparable accuracy; outputs Markdown via `to_markdown()`; OCR support for scanned PDFs. Replaces pdfminer.six recommendation in spec. |
| python-docx | 1.1.0 | DOCX extraction | Already installed. No change needed. |
| readability-lxml | ^0.8.x | URL ingestion (extract article text from web pages) | Spec section 5 calls for URL ingestion. readability-lxml is the Python port of Mozilla Readability. |

Note: pdfminer.six is NOT recommended despite being mentioned in the spec. PyMuPDF is strictly better: 6x faster, similar accuracy, native Markdown output. No pdfminer.six installation needed.

---

### Development Toolchain

| Tool | Version | Purpose | Notes |
|------|---------|---------|-------|
| @vitejs/plugin-react | ^4.x | Vite React plugin (Babel fast refresh) | Use this not @vitejs/plugin-react-swc for now — swc has occasional edge cases with TipTap |
| ESLint | ^9.x | Linting | Use eslint-config-react-app or @eslint/js with typescript-eslint |
| Prettier | ^3.x | Code formatting | Standard; pair with eslint-config-prettier |
| @types/react | ^18.3.x | TypeScript defs for React 18 | |
| @types/react-dom | ^18.3.x | TypeScript defs for ReactDOM | |
| vite-tsconfig-paths | ^5.x | Resolve `@/components/...` path aliases | Avoids relative import hell in nested component tree |

---

## Installation

```bash
# In /frontend directory
npm create vite@latest . -- --template react-ts

# Core routing + state
npm install react-router-dom@6 zustand@5 @tanstack/react-query@5

# UI
npm install tailwindcss@3 postcss autoprefixer
npx tailwindcss init -p
npx shadcn-ui@latest init

# Drag and drop
npm install @dnd-kit/core @dnd-kit/sortable @dnd-kit/utilities
npm install react-grid-layout
npm install @types/react-grid-layout -D

# Rich text
npm install @tiptap/react @tiptap/pm @tiptap/starter-kit
npm install @tiptap/extension-image @tiptap/extension-link @tiptap/extension-code-block-lowlight lowlight

# File upload
npm install react-dropzone@15

# Dev tools
npm install -D vite-tsconfig-paths eslint prettier @types/react @types/react-dom
```

```bash
# Backend additions (requirements.txt)
sse-starlette>=2.0.0
PyMuPDF>=1.26.0
readability-lxml>=0.8.0
openai>=1.30.0          # if OpenAI TTS chosen
# elevenlabs>=1.0.0     # if ElevenLabs TTS chosen
```

---

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Drag-drop | @dnd-kit | react-beautiful-dnd | Deprecated by Atlassian; React 19 compatibility uncertain |
| Drag-drop | @dnd-kit | pragmatic-drag-and-drop (Atlassian) | More complex headless API; overkill for this scale |
| Canvas grid | react-grid-layout | Build custom | Snap-to-grid + resize handles + collision detection is weeks of work; react-grid-layout solves it in one install |
| Rich text | TipTap v3 | Plate.js | React-only; collaboration via Hocuspocus only; smaller ecosystem |
| Rich text | TipTap v3 | Quill | Legacy; v2 rewrite still catching up; consensus is don't use for new projects |
| Rich text | TipTap v3 | Lexical (Meta) | Excellent performance but API is lower-level; extension ecosystem smaller than TipTap |
| State | Zustand | Redux Toolkit | 3x more boilerplate; not justified for single-team project |
| State | Zustand + TanStack Query | TanStack Query only | TanStack Query doesn't manage UI state (selected slide, canvas drag position, streaming buffer) |
| PDF | PyMuPDF | pdfminer.six | 6x slower; spec mentions pdfminer but PyMuPDF is strictly better |
| PDF | PyMuPDF | pypdf | PyMuPDF faster, better accuracy, Markdown output |
| TTS | OpenAI TTS | Azure Speech | Extra vendor, no existing relationship; Azure adds compliance overhead |
| Component lib | shadcn/ui | Mantine | Mantine uses CSS-in-JS; conflicts with existing Tailwind. shadcn is Tailwind-native. |
| Build | Vite 6 | Create React App | CRA is deprecated and unmaintained |

---

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| react-beautiful-dnd | Deprecated by Atlassian; no React 19 commitment; project is in maintenance-only mode | @dnd-kit/sortable |
| pdfminer.six | 6x slower than PyMuPDF; no Markdown output; spec mentions it but it's the wrong choice | PyMuPDF (fitz) |
| Quill / react-quill | Legacy; v2 still catching up; 2026 consensus is "don't start new projects on Quill" | @tiptap/react |
| @vitejs/plugin-react-swc | Has edge cases with TipTap ProseMirror transforms; extra complexity for no meaningful gain here | @vitejs/plugin-react (Babel) |
| WebSockets for AI streaming | SSE is simpler for unidirectional AI text streaming; WebSockets only needed for bidirectional comms (not the case here) | SSE via sse-starlette + fetch ReadableStream |
| Canvas-native DnD for slide blocks | react-grid-layout already handles snap grid + resize; using dnd-kit on top creates conflicting event handling | react-grid-layout standalone for canvas |

---

## Vite + Deployment Constraint Notes

The existing nginx.conf (generated by nixpacks staticfile provider) serves with `try_files $uri $uri/ /index.html` for SPA deep links. This works unchanged after Vite migration. The Traefik stripprefix middleware removes `/lms` before requests reach nginx, so nginx sees paths starting at `/`.

**Vite `base: '/lms/'` is required** so that built asset URLs in `index.html` read `src="/lms/assets/main.js"` — this is what the browser requests, and Traefik passes through to nginx with the /lms prefix intact for static assets.

**React Router `basename`** should be set to `import.meta.env.BASE_URL` (which resolves to `/lms/` from Vite base, with trailing slash stripped for RR). This ensures in-app navigation generates `/lms/creator/...` URLs correctly.

---

## Version Compatibility

| Package | Compatible With | Notes |
|---------|-----------------|-------|
| @tiptap/react ^3.x | React 18.3 | v3 dropped React 16 support; React 18 is fine |
| @dnd-kit/core ^6.x | React 18 | No issues; hooks-based |
| react-grid-layout ^1.4 | React 18 | Check: uses legacy findDOMNode internally; functional but may emit a warning |
| Zustand ^5 | React 18 | v5 is the current stable; fully compatible |
| @tanstack/react-query ^5 | React 18 | v5 API change from v4: no `useQuery(key, fn)` shorthand — use `queryFn` object form |
| sse-starlette ^2 | FastAPI 0.104 / Starlette | Fully compatible with existing FastAPI version |

---

## Sources

- [Vite Shared Options — base config](https://vite.dev/config/shared-options) — HIGH confidence
- [React Router v6/v7 basename docs](https://api.reactrouter.com/v7/types/_react_router_dev.config.Config.html) — HIGH confidence
- [@dnd-kit/sortable npm](https://www.npmjs.com/package/@dnd-kit/sortable) — v10.0.0 confirmed — HIGH confidence
- [dnd-kit vs pragmatic DnD comparison 2026](https://www.pkgpulse.com/blog/dnd-kit-vs-react-beautiful-dnd-vs-pragmatic-drag-drop-2026) — MEDIUM confidence
- [@tiptap/react npm](https://www.npmjs.com/package/@tiptap/react) — v3.22.5 confirmed — HIGH confidence
- [TipTap v3 announcement](https://tiptap.dev/tiptap-editor-v3) — HIGH confidence
- [Liveblocks rich text editor comparison 2025](https://liveblocks.io/blog/which-rich-text-editor-framework-should-you-choose-in-2025) — MEDIUM confidence
- [react-dropzone npm](https://www.npmjs.com/package/react-dropzone) — v15.0.0 confirmed — HIGH confidence
- [Zustand npm](https://www.npmjs.com/package/zustand) — v5.0.13 confirmed — HIGH confidence
- [sse-starlette PyPI](https://pypi.org/project/sse-starlette/) — HIGH confidence
- [OpenAI TTS pricing](https://openai.com/api/pricing/) — $15/1M chars tts-1 confirmed — HIGH confidence
- [ElevenLabs vs OpenAI TTS comparison](https://vapi.ai/blog/elevenlabs-vs-openai) — MEDIUM confidence (quality claims from third-party benchmark)
- [PyMuPDF vs pdfminer benchmark](https://github.com/py-pdf/benchmarks) — MEDIUM confidence
- [TanStack Query vs SWR 2025](https://refine.dev/blog/react-query-vs-tanstack-query-vs-swr-2025/) — MEDIUM confidence
- [shadcn/ui vs Mantine comparison 2025](https://makersden.io/blog/react-ui-libs-2025-comparing-shadcn-radix-mantine-mui-chakra) — MEDIUM confidence

---

*Stack research for: LMS Platform — Vite+React migration + AI Course Builder*
*Researched: 2026-05-08*
