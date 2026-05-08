# Pitfalls Research

**Domain:** Adding Vite+React frontend build and AI-powered course authoring to an existing FastAPI LMS
**Researched:** 2026-05-08
**Confidence:** HIGH — based on existing codebase inspection + verified sources

---

## Critical Pitfalls

### Pitfall 1: Vite `base` and React Router `basename` Are Not the Same Thing

**What goes wrong:**
The app builds successfully, assets load fine at the root, but all React Router deep links 404 when navigated to directly (e.g. `/creator/courses/123`). Or: assets load but with wrong paths (404 on JS/CSS chunks). The two config values are separate and have different format rules.

**Why it happens:**
Developers set one but not the other, or set them to the same format when the formats differ. Vite's `base` in `vite.config.ts` controls asset URL prefixing at build time. React Router's `basename` in `<BrowserRouter>` controls client-side route matching. They must both point to the same path but have slightly different format requirements: Vite wants a trailing slash (`'/lms/'`), React Router wants no trailing slash (`'/lms'`).

**How to avoid:**
```typescript
// vite.config.ts
export default defineConfig({
  base: '/lms/',  // trailing slash required
  ...
})

// main.tsx
<BrowserRouter basename="/lms">  // no trailing slash
  <App />
</BrowserRouter>
```
The existing Traefik stripprefix means the app is served without the prefix in practice, so `base: '/'` and no `basename` may be correct depending on whether Traefik strips before reaching nginx. Verify by inspecting actual asset request URLs in the browser network tab after first deploy.

**Warning signs:**
- JS/CSS chunks returning 404 but `index.html` loads fine
- Browser console shows `net::ERR_ABORTED 404` for `.js` files
- Hard refresh on any route except `/` shows blank page or 404

**Phase to address:**
Vite Migration phase (Phase 1). Must be verified before any other frontend work.

---

### Pitfall 2: Nginx SPA Fallback Breaks With Path Prefix

**What goes wrong:**
The current `Staticfile` with `status_codes: 404: /index.html` works for the current single-file app because there are no nested routes nginx needs to serve. After Vite migration, deep links to `/creator/courses/123` result in nginx returning the `index.html` correctly — but the path is wrong if nginx's root and the app's base path are misaligned. The git log shows this has already been painful (`5x nginx commits` in recent history: nixpacks.toml, Caddyfile, nginx.conf, Staticfile, try_files iterations).

**Why it happens:**
Nixpacks staticfile provider auto-generates an nginx config. When the Vite build outputs to `dist/`, and the app is served at a sub-path by Traefik, nginx's `try_files` must fall back to `/index.html` — but if `alias` is used instead of `root`, the fallback path must include the full local path. Coolify's static site tick + nixpacks can't be customised for nginx, forcing a Dockerfile approach for full control.

**How to avoid:**
Use a custom `nginx.conf` committed to the repo, co-located with the `frontend/` directory. The `Staticfile` approach is fragile because the generated config is opaque. A committed `nginx.conf` is transparent and reproducible:
```nginx
server {
    listen 80;
    root /app/dist;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }
}
```
Then use a `Dockerfile` in `frontend/` that builds Vite and copies `dist/` into an nginx image. This removes all nixpacks guesswork.

**Warning signs:**
- Deploying works but refreshing any route except `/` 404s
- Coolify build log shows nixpacks detecting conflicting providers
- Multiple urgent nginx-related commits in quick succession (already seen in this repo)

**Phase to address:**
Vite Migration phase (Phase 1). The nginx config strategy must be decided before first deploy.

---

### Pitfall 3: Breaking Existing Auth During Frontend Migration

**What goes wrong:**
The new Vite build ships but the login flow is broken — users cannot log in, JWT tokens from the old Babel app are incompatible with the new app's auth state shape, or the auth token stored in `localStorage` under the old key name is no longer read by the new app.

**Why it happens:**
The existing single-file app stores the JWT and user state in `localStorage` under specific key names (e.g. `token`, `user`). The new Vite app may use different key names, different state shapes, or initialise auth state before the token is hydrated. The existing app also uses `window.location.href` navigation in some places (evidenced by recent commit `fix: replace hard window.location navigations with SPA pushState`). If any of these survive into the Vite build, they bypass React Router and cause full-page reloads that break SPA state.

**How to avoid:**
1. Audit the existing `index.html` (3420 lines) for all `localStorage.setItem`, `localStorage.getItem`, `window.location.href =` and `window.location.replace(` calls before starting the migration.
2. Preserve the exact same `localStorage` key names in the new app, or write a one-time migration function that runs on first load.
3. Replace all `window.location.href =` navigations with `useNavigate()` from React Router.
4. Test the full auth cycle (login, refresh, logout, protected route redirect) in the Vite app before shipping.

**Warning signs:**
- Logged-in users are logged out after deployment
- Login redirects loop back to `/login`
- Console errors about undefined user in protected components on hard refresh

**Phase to address:**
Vite Migration phase (Phase 1). The auth hydration pattern must be the first thing wired up.

---

### Pitfall 4: New SQLAlchemy Models Orphan the Existing `Course.content` JSON Blob

**What goes wrong:**
The existing `Course` model stores all course structure in a single `content` JSON column. The new spec introduces proper relational models (Module, Video, Slide, Block, Quiz, Question). The migration adds new tables but the existing course CRUD routes still read/write `Course.content`. New AI-generated courses write to the new relational tables. Old courses exist only as JSON blobs. The two systems diverge and the frontend has to handle both shapes.

**Why it happens:**
It is tempting to add the new models and leave the old `content` column in place as a "migration safety net". In practice this creates a two-code-path problem: every query, every API response, and every frontend component must branch on which format a course uses.

**How to avoid:**
Decide before writing a single migration: either (a) migrate all existing `content` JSON to the new relational tables in a one-time script and remove the `content` column, or (b) accept the dual format explicitly and write a `CourseAdapter` service that normalises both formats into one API response shape. Option (a) is strongly preferred because it eliminates the branch. Write the migration script, run it on a copy of `lms.db`, verify, then apply.

**Warning signs:**
- API routes returning different shaped objects depending on how the course was created
- Frontend `course.modules` is sometimes an array, sometimes undefined
- Creator portal shows courses but builder cannot open them

**Phase to address:**
Data model phase (Phase 2). Schema decisions must be finalised before any builder UI is built.

---

### Pitfall 5: `order_index` Drift Under Concurrent Reorder Operations

**What goes wrong:**
A creator reorders modules by dragging. The frontend sends a PATCH with the new order. A second request (autosave of a field change) fires in parallel. The responses arrive out of order. `order_index` values in the DB end up as `[0, 0, 2, 1]` — duplicate zeros, skipped values. The UI reorders correctly but on next page load the order is wrong.

**Why it happens:**
Reorder is usually implemented as a `POST /modules/reorder` that accepts an ordered array of IDs and writes sequential `order_index` values. If two writes hit simultaneously, the last writer wins but the intermediate state is corrupt. SQLite (current DB) has limited concurrency protection compared to Postgres.

**How to avoid:**
Implement reorder as a single transaction that assigns sequential integers to all affected records atomically. Never update `order_index` fields in individual PATCH requests — always update the full sibling set in one transaction. On the frontend, debounce the reorder API call by 300ms to prevent rapid-fire requests from a single drag operation.

```python
# Correct: single transaction, all siblings at once
with db.begin():
    for idx, item_id in enumerate(ordered_ids):
        db.execute(
            update(Module).where(Module.id == item_id).values(order_index=idx)
        )
```

**Warning signs:**
- Slide or module order appears correct on screen but wrong after page refresh
- Duplicate `order_index` values in the DB (`SELECT order_index, COUNT(*) FROM modules GROUP BY order_index HAVING COUNT(*) > 1`)

**Phase to address:**
Data model + Course Builder phase (Phase 2/3). Implement correct reorder logic from the start.

---

### Pitfall 6: SSE Streaming — Orphaned Generators on Client Disconnect

**What goes wrong:**
A creator clicks "Generate slide outline", the stream starts, then navigates away or clicks Cancel. The frontend EventSource connection closes. The backend generator continues calling Claude API, consuming tokens and holding a DB connection open, until the full response completes. Under load, this accumulates into a background token-burning leak.

**Why it happens:**
FastAPI's `StreamingResponse` / `EventSourceResponse` does not automatically detect client disconnect and cancel the generator. The generator runs to completion regardless. The existing `claude_service.py` already uses a non-streaming `httpx.AsyncClient().post()` — when streaming is added, the generator will be yielding chunks from an open Claude connection that nobody is reading.

**How to avoid:**
Check `await request.is_disconnected()` at the start of each `yield` in the generator:
```python
async def generate_stream(request: Request):
    async with anthropic.stream(...) as stream:
        async for chunk in stream:
            if await request.is_disconnected():
                break
            yield f"data: {chunk.delta.text}\n\n"
```
Also implement a per-creator rate limiter (already required by the spec) to cap worst-case token spend regardless of disconnect detection.

**Warning signs:**
- Claude API usage metrics climbing without corresponding UI activity
- DB connection pool exhaustion under moderate creator load
- ElevenLabs API costs higher than expected

**Phase to address:**
AI Integration phase (Phase 4). Must be in the initial SSE implementation, not added later.

---

### Pitfall 7: TTS Audio Regeneration Storms

**What goes wrong:**
A creator edits a narration script on slide 3. They click "Regenerate narration for all slides" — which calls ElevenLabs 20 times in rapid succession. The existing `tts_service.py` already fires individual `httpx.AsyncClient().post()` calls with no concurrency limit. 20 simultaneous ElevenLabs requests saturates the API plan's concurrent request limit, returns 429 errors, and the creator sees a mix of new and old audio with no clear indication of what failed.

**Why it happens:**
Bulk TTS generation is implemented as `asyncio.gather()` over all slides. There is no semaphore limiting concurrent requests. ElevenLabs free/starter plans allow 2-5 concurrent requests; creator plans allow more but still have limits.

**How to avoid:**
Use `asyncio.Semaphore` to cap concurrent TTS requests:
```python
sem = asyncio.Semaphore(3)  # ElevenLabs plan limit

async def generate_one(slide):
    async with sem:
        return await tts_service.generate(slide.narration_script)

results = await asyncio.gather(*[generate_one(s) for s in slides])
```
Cache generated audio by content hash: if the narration script hasn't changed, serve the cached file without calling ElevenLabs. Store `narration_script_hash` alongside `narration_audio_url` in the Slide model.

**Warning signs:**
- 429 errors in logs during bulk TTS generation
- Some slides have new audio, others have old audio with no indication which
- ElevenLabs monthly character quota depleted faster than expected

**Phase to address:**
TTS phase (Phase 5). Caching and rate limiting must be in the first TTS implementation.

---

### Pitfall 8: PDF Text Extraction Silently Producing Garbage

**What goes wrong:**
A creator uploads a PDF training document. AI generates a module description. The description is incoherent — full of PDF binary artifacts, page numbers, header/footer repetitions, or raw PostScript commands. The creator assumes AI is the problem; the real problem is text extraction.

**Why it happens:**
The existing `document_service.py` extracts PDF text by decoding raw bytes as UTF-8 with `errors='ignore'`. This works for text-based PDFs but produces garbage for scanned PDFs, PDFs with embedded fonts, and most "print to PDF" outputs from Word/PowerPoint. The check `if len(extracted_text.strip()) < 100` only catches complete failures, not partial garbage.

**How to avoid:**
Replace the `_extract_pdf` method with `pdfminer.six` or `pymupdf` (fitz), which properly decode PDF content streams:
```python
from pdfminer.high_level import extract_text_to_fp
import io

def _extract_pdf(file_bytes: bytes) -> str:
    output = io.StringIO()
    extract_text_to_fp(io.BytesIO(file_bytes), output)
    return output.getvalue()
```
Add a minimum quality gate: if the extracted text has fewer than 200 unique words or a ratio of non-ASCII characters above 30%, reject the document and prompt the creator to try a different format.

**Warning signs:**
- AI-generated content contains random numbers, hex strings, or repeated partial words
- Generated module descriptions unrelated to the uploaded document's topic
- Text extraction produces text with very high character count but low word count

**Phase to address:**
Document ingestion phase (Phase 4). Fix `document_service.py` before connecting it to AI generation.

---

### Pitfall 9: Drag-Drop Canvas State Not Synced With Server on Slide Exit

**What goes wrong:**
A creator drags blocks around the slide canvas, edits text, then navigates to the next slide. Autosave was supposed to fire on every change, but rapid drag operations flood the API with PATCH requests. The debounce absorbs some; the final state before navigation fires after the navigation completes. The creator returns to find the slide in an earlier state.

**Why it happens:**
Drag-drop editors produce a very high rate of state change events (every pixel movement fires a position update). Debounced autosave means the last write may fire 500ms after the user has already navigated away. If the component unmounts before the debounced function fires, the save is lost. React's `useEffect` cleanup cancels pending debounced calls on unmount unless explicitly handled.

**How to avoid:**
Use a `beforeunload` or route-change guard to flush any pending save before navigation:
```typescript
// Flush pending save before unmounting
useEffect(() => {
  return () => {
    if (pendingSave.current) {
      pendingSave.current.flush(); // lodash debounce flush
    }
  };
}, []);
```
Treat block positions as a "committed" state that only persists on explicit save actions (drop completed), not during drag. Use an optimistic local state for in-progress drag, only write to server on `onDragEnd`.

**Warning signs:**
- "Changes saved" indicator briefly appears but content reverts after navigation
- Block positions correct in editor but different in preview
- Network tab shows PATCH requests arriving after navigation has occurred

**Phase to address:**
Slide Editor phase (Phase 6). Establish the autosave flush pattern before adding complex state.

---

### Pitfall 10: Course Versioning Collision — Learner Progress on Old Version

**What goes wrong:**
A creator publishes a course. Learners enrol and make progress (tracked against `course_id` and `order_index`). Creator adds a module, renumbers existing modules, and publishes an update. Existing learner progress records now point to the wrong modules. A learner who completed "Module 2" (now "Module 3" in v2) appears to have not completed it.

**Why it happens:**
The spec defines a `version` field on `Course` and describes a versioning state machine (`has_unpublished_changes` → publish update). But the `Enrollment` model currently only stores `course_id` and `progress` (a float). There is no version anchor. If modules are identified by `order_index` (positional), any insertion before an existing module shifts all subsequent indices.

**How to avoid:**
Enrollments must be anchored to a course version, not just a course ID. Either: (a) use stable UUIDs for Module/Video IDs (never reuse, never renumber) and track learner progress against IDs, or (b) snapshot the full course structure on publish and anchor progress to the snapshot. Option (a) is simpler. The `order_index` column is only for display ordering, never for identity.

**Warning signs:**
- Learners' completion percentages reset or change after a course update
- "Resume course" lands the learner in the wrong place
- Module completion status inconsistent between the course player and the creator's analytics view

**Phase to address:**
Data model phase (Phase 2). The enrollment schema must be designed for versioning before any learner-facing progress tracking is built.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Keep `Course.content` JSON column alongside new relational models | No migration needed immediately | Two code paths forever; API responses are inconsistent | Never — migrate fully or not at all |
| Store TTS audio under flat `/uploads/audio/course_N/` with no DB record | Simple first pass | Cannot regenerate or track staleness; breaks on course duplication | MVP only, replace before publish flow |
| Use `order_index` integers for learner progress tracking | Simple to implement | Breaks when creator reorders or inserts modules | Never — use stable IDs |
| Inline AI calls in FastAPI route handlers instead of a service layer | Faster to write | Rate limiting, logging, and model swapping require touching every route | Never — the spec already calls for a unified AI service |
| No chunking for large document uploads | Works for small docs | Server OOM on 25MB PDFs; already a known risk given current `extract_text(file_bytes: bytes)` pattern | Never for production; current code must be fixed |
| Single hardcoded voice ID in TTS service | Works for demo | Cannot support per-creator voice selection per spec | Acceptable for Phase 1 TTS, must be parameterised before Slide Editor ships |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| Claude API (streaming) | Re-using the existing non-streaming `httpx` call pattern, just adding `.stream()` without changing error handling | Use the Anthropic Python SDK's `with client.messages.stream()` context manager which handles SSE framing, retries, and error events correctly |
| ElevenLabs TTS | Calling `eleven_monolingual_v1` model (used in existing `tts_service.py`) for new slide narration | `eleven_monolingual_v1` is deprecated; use `eleven_turbo_v2_5` for low-latency narration generation |
| FastAPI + SQLite concurrent writes | Running AI generation + autosave + TTS in parallel with SQLite | SQLite's write lock will cause 500 errors under concurrent writes; the new models add write contention; plan migration to Postgres before multi-creator load |
| Vite dev server + FastAPI dev server | CORS errors when running both locally | Add `http://localhost:5173` to FastAPI CORS origins in dev; use Vite `proxy` config to forward `/api` calls to FastAPI so cookies/auth headers are same-origin |
| Coolify + Traefik stripprefix | Traefik strips `/lms` prefix before forwarding to nginx; nginx serves from `/`; Vite must be built with `base: '/'` not `base: '/lms/'` | Confirm strip behaviour in Traefik config before choosing Vite `base` value — this is the root cause of multiple prior deploy failures in this repo |

---

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Loading full course tree in one query (Course + Modules + Videos + Slides + Blocks) | Course builder takes 3-5 seconds to open large courses | Lazy-load: fetch course skeleton first, load module detail on demand | Any course with 5+ modules and 5+ videos per module |
| Re-rendering entire slide canvas on every block property change | Slide editor feels sluggish on slides with 8+ blocks | Use `React.memo` on Block components; keep block state local and only write to parent store on commit | Noticeable at 5+ blocks with rich text editors |
| Generating TTS for all slides serially (existing pattern: one by one) | "Generate narration" takes 60+ seconds for a 20-slide video | Parallelise with semaphore (max 3 concurrent); show per-slide progress | Any video with 10+ slides |
| Streaming AI responses with no timeout | A hung Claude request blocks the SSE connection indefinitely | Set `connect_timeout=10`, `read_timeout=120` on httpx, and cancel the generator if no token received in 30 seconds | First time Claude API has a slow response |
| Document text sent directly to Claude without chunking | Token limit exceeded silently (Claude truncates or errors) | Check character count before sending; chunk and summarise if over 150,000 chars | Any document over ~100 pages |

---

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Accepting document uploads without file type validation | A creator uploads a zip or executable disguised as a PDF | Validate MIME type server-side using `python-magic`, not just the filename extension |
| Storing TTS audio files under a predictable path (`/uploads/audio/course_N/lesson_M_N.mp3`) | Unenrolled learners can guess audio URLs and access paid content | Serve audio through an authenticated endpoint that checks enrollment, or use signed URLs with expiry |
| No rate limit on `/api/ai/generate` per creator | A compromised creator account drains Claude API budget | Implement per-creator hourly token quota stored in the DB; expose remaining quota in the UI (already in spec) |
| Preview mode bypasses sequential navigation lock but uses the same JWT | A learner could construct a preview token request and view unpublished content | Preview tokens must include `is_preview: true` claim and a course version anchor; backend must validate both |
| Embedding full course structure in GET response without checking enrollment | Course content exposed to unenrolled users | Ensure `/api/courses/:id` returns structure only; slide content and quiz answers only served to enrolled learners or creators |

---

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Autosave indicator that shows "Saved" even when the save was optimistic (not confirmed by server) | Creator thinks content is safe, closes browser, loses work | Show "Saving..." while request in flight, "Saved" only on 200 response, "Save failed — retry?" on error |
| AI generation replaces existing content without confirmation | Creator accidentally wipes a carefully written description by clicking "Generate" | Show generated content in a side drawer for review; never overwrite in place without an explicit "Accept" action (already in spec — enforce it) |
| Drag-drop reorder with no visual affordance for where an item will land | Creators repeatedly undo reorders because the drop target wasn't where they expected | Use dnd-kit's `DragOverlay` for drag previews and explicit drop zone highlighting |
| No clear distinction between "has unsaved changes" and "has unpublished changes" | Creators publish without saving, or save without publishing | Two distinct UI states: yellow "unsaved" dot on autosave fields; orange "unpublished" pill in top bar |
| Quiz builder allows saving a question with no correct answer marked | Course passes pre-flight check, learner encounters a quiz with unanswerable question | Enforce `Q002` validation gate at question save time, not just at publish |

---

## "Looks Done But Isn't" Checklist

- [ ] **Vite migration:** Verify asset loading, auth hydration, deep-link refresh, and API calls all work in a Coolify staging deploy — not just locally
- [ ] **Autosave:** Verify that pending saves are flushed on route change, not just on a timer — test by editing a field and immediately clicking "next slide"
- [ ] **Document ingestion:** Upload a real scanned PDF and verify extracted text is readable before connecting to AI generation
- [ ] **TTS caching:** Verify that editing a narration script and regenerating audio replaces the old file, and that the old URL is invalidated in the frontend
- [ ] **Reorder operations:** Verify `order_index` values after: insert in middle, delete from middle, drag to top, drag to bottom — check DB directly
- [ ] **Publish flow validation:** Run pre-flight check against a course with a deliberate broken slide (no alt text on an image) and verify the error links back to the correct slide
- [ ] **Version update:** Enrol a test learner, complete one module, publish a course update that inserts a new module before it — verify learner progress is preserved correctly
- [ ] **SSE cancel:** Start an AI generation, click Cancel, verify the Claude API request was actually stopped (check token usage, not just the UI)

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Vite base/basename misconfiguration breaks deploy | LOW | Fix `vite.config.ts` and `<BrowserRouter>`, rebuild, redeploy — ~30 min |
| Nginx SPA fallback misconfigured in Coolify | MEDIUM | Switch from nixpacks staticfile to custom Dockerfile with committed nginx.conf; requires Coolify reconfiguration |
| `Course.content` and new relational models diverged | HIGH | Write a one-time migration script; manual QA of all existing courses; ~1-2 days |
| `order_index` corruption across many courses | MEDIUM | Write a repair script that renumbers order_index to be sequential within each parent; test before running on production DB |
| TTS audio stored without DB record, cache broken | MEDIUM | Backfill `narration_audio_url` from filesystem scan; add DB record; ~half day |
| SSE streaming implemented without disconnect detection | LOW (if caught in Phase 4) / HIGH (if found in production with active users) | Add `request.is_disconnected()` check; deploy; no data migration needed |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Vite base/basename mismatch | Phase 1: Vite Migration | Deploy to Coolify staging, refresh on a deep link, confirm 200 |
| Nginx SPA fallback with path prefix | Phase 1: Vite Migration | Test every route with hard refresh in staging |
| Auth regression during migration | Phase 1: Vite Migration | Full auth test: login → protected route → refresh → logout → re-login |
| `Course.content` vs relational model divergence | Phase 2: Data Models | All existing courses load correctly in the new creator portal |
| `order_index` drift | Phase 2: Data Models | DB query for duplicate order_index after reorder test |
| SSE orphaned generators | Phase 4: AI Integration | Cancel mid-stream, check Claude API usage logs for 60s after cancel |
| TTS regeneration storms | Phase 5: TTS | Run bulk TTS on a 20-slide video, verify no 429s, verify cache hits on repeat |
| PDF extraction garbage | Phase 4: Document Ingestion | Upload a scanned PDF, inspect raw extracted text before sending to AI |
| Slide canvas save-on-navigate race | Phase 6: Slide Editor | Edit field, immediately navigate away, return, verify field retained |
| Versioning and learner progress | Phase 2: Data Models | Enrol learner, publish update, verify progress intact |

---

## Sources

- Existing codebase: `backend/services/document_service.py` (UTF-8 PDF decode confirmed), `backend/services/tts_service.py` (hardcoded voice, no caching, serial generation confirmed), `backend/services/claude_service.py` (non-streaming httpx pattern confirmed)
- Git history: 5 nginx/Staticfile/Caddyfile commits in rapid succession confirm the deployment path-prefix problem is already established
- Coolify nixpacks SPA issues: https://github.com/coollabsio/coolify/discussions/5763 and https://github.com/coollabsio/coolify/issues/7114
- Vite subdirectory deployment: https://medium.com/@krishnaananthvk/how-i-spent-2-hours-teaching-nginx-and-react-router-to-play-nice-in-subdirectories-spoiler-they-d261e76f44e0
- FastAPI SSE disconnect: https://github.com/fastapi/fastapi/discussions/7572 and https://github.com/fastapi/fastapi/issues/1342
- dnd-kit state management: https://dndkit.com/ and https://github.com/clauderic/dnd-kit/discussions/639
- ElevenLabs latency/models: https://elevenlabs.io/docs/overview/models (eleven_monolingual_v1 deprecation)
- Document ingestion async: https://medium.com/@connect.hashblock/async-file-uploads-in-fastapi-handling-gigabyte-scale-data-smoothly-aec421335680

---
*Pitfalls research for: Adding Vite+React + AI Course Builder to existing FastAPI LMS*
*Researched: 2026-05-08*
