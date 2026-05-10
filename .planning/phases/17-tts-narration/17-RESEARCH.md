# Phase 17: TTS & Narration - Research

**Researched:** 2026-05-10
**Domain:** ElevenLabs TTS API, FastAPI async patterns, React audio playback
**Confidence:** HIGH

---

## Summary

Phase 17 adds ElevenLabs narration audio generation to the Slide Editor. The data model already has both required columns (`narration_audio_url` and `narration_script_hash` on `Slide`) — no migration needed. A legacy `TTSService` exists in `backend/services/tts_service.py` but it targets the retired `Course.content` JSON blob architecture; it must be rewritten for the new per-slide model. The new service should use `model_id: "eleven_flash_v2_5"` (supersedes `eleven_turbo_v2_5`), call `POST /v1/text-to-speech/{voice_id}`, store MP3 under `uploads/audio/slide_{slide_id}.mp3`, and update `Slide.narration_audio_url` + `Slide.narration_script_hash` atomically. A `Video`-level `narration_voice_id` column already exists for the chosen voice — no schema change needed.

Bulk generation uses `asyncio.Semaphore(3)` (established in STATE.md pitfall #6) to avoid 429s from ElevenLabs' concurrent request limit. Script-hash caching compares `hashlib.sha256(narration_script.encode()).hexdigest()` against the stored `narration_script_hash` to skip unchanged slides. On the frontend, `NarrationTab` gains an audio player (`<audio>` element — no new library) and a "Generate audio" button; `SlideBuilderPage` already has a placeholder `"Generate Narration"` button (`data-testid="bulk-narration-btn"`) that is currently disabled and needs to be wired up.

**Primary recommendation:** Rewrite the legacy `TTSService` around per-slide generation, add two new endpoints to a new `tts.py` router (per-slide + bulk), and extend `NarrationTab` with audio playback and a generate button. Do not stream TTS audio — return a JSON response with the final URL.

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| TTS-01 | Creator can generate narration audio for a slide from its narration script (ElevenLabs) | New endpoint POST /api/slides/{id}/tts/generate; updated TTSService._call_elevenlabs_for_slide(); NarrationTab gets "Generate audio" button + audio player |
| TTS-02 | Creator can bulk generate narration audio for all slides in a video with populated scripts | New endpoint POST /api/videos/{id}/tts/bulk-generate; asyncio.Semaphore(3) concurrency guard; SLIDE-03 checkbox in REQUIREMENTS.md finally checked |
| TTS-03 | TTS service uses a semaphore to rate-limit concurrent requests and prevent 429s on bulk generation | asyncio.Semaphore(3) module-level in tts.py; each slide acquires semaphore before httpx call |
| TTS-04 | Generated narration audio is cached; bulk re-generate only reprocesses slides with changed scripts | hashlib.sha256(script.encode()).hexdigest() compared against Slide.narration_script_hash; skip if equal |
| TTS-05 | Creator can select from available ElevenLabs voice options | Voice stored on Video.narration_voice_id; voice selection UI in SlideBuilderPage header (dropdown of 2-3 curated voices) or NarrationTab; at least Rachel + Adam IDs hardcoded |
</phase_requirements>

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| httpx | 0.25.2 (already installed) | ElevenLabs API calls | Already used for Claude/document fetch; async client with timeout control |
| hashlib | stdlib | SHA-256 script hashing | No install; deterministic; 64-char hex fits `narration_script_hash String(64)` |
| asyncio.Semaphore | stdlib | Concurrency limit for bulk TTS | Prevents concurrent request storm; STATE.md pitfall #6 mandates this |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| HTML5 `<audio>` element | browser native | Audio playback in NarrationTab | No library needed; plays MP3 from relative URL |
| pathlib.Path | stdlib | Audio file storage | Consistent with uploads.py pattern |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| eleven_flash_v2_5 | eleven_multilingual_v2 | Flash is ~75ms latency, multilingual is higher quality but slower and pricier; Flash sufficient for course narration |
| hashlib.sha256 | hashlib.md5 | sha256 is 64 chars (fits the column), md5 is 32 chars but cryptographically weaker; sha256 preferred |
| Hardcoded voice list | GET /v2/voices premade list | Dynamic list adds API call on page load; 2-3 curated voices hardcoded is simpler and sufficient for TTS-05 |

**Installation:** No new packages needed. httpx already in requirements.txt.

---

## Architecture Patterns

### Recommended Project Structure
```
backend/
├── routers/
│   └── tts.py               # NEW: per-slide + bulk endpoints
├── services/
│   └── tts_service.py       # REWRITE: per-slide ElevenLabs calls
├── tests/
│   └── test_tts_phase17.py  # NEW: TTS-01 through TTS-05

frontend/src/
├── components/slide/
│   └── NarrationTab.tsx     # EXTEND: add audio player + generate button
├── pages/creator/
│   └── SlideBuilderPage.tsx # EXTEND: wire bulk narration button + voice picker
```

### Pattern 1: Per-Slide TTS Endpoint (non-streaming JSON)
**What:** POST endpoint generates audio, stores file, updates Slide, returns URL.
**When to use:** TTS-01 single-slide generation.
**Example:**
```python
# backend/routers/tts.py
import asyncio
import hashlib
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from database import get_db
from models import Slide, Video, Module, Course
from middleware.auth_middleware import require_creator
from services.tts_service import TTSService

router = APIRouter(tags=["tts"])
tts_service = TTSService()

class TTSGenerateRequest(BaseModel):
    voice_id: Optional[str] = None  # falls back to Video.narration_voice_id or DEFAULT

@router.post("/api/slides/{slide_id}/tts/generate")
async def generate_slide_audio(
    slide_id: int,
    body: TTSGenerateRequest,
    db: Session = Depends(get_db),
    current_user=Depends(require_creator),
):
    slide = _get_slide_or_404(slide_id, db, current_user)
    if not slide.narration_script:
        raise HTTPException(status_code=400, detail="Slide has no narration script")
    voice_id = body.voice_id or slide.video.narration_voice_id or TTSService.DEFAULT_VOICE_ID
    audio_url = await tts_service.generate_for_slide(slide, voice_id)
    db.refresh(slide)
    return {"audio_url": audio_url, "slide_id": slide_id}
```

### Pattern 2: TTSService Per-Slide Method
**What:** Rewritten service method targeting per-slide architecture.
**When to use:** Called by both per-slide and bulk endpoints.
**Example:**
```python
# backend/services/tts_service.py (rewrite)
import asyncio
import hashlib
import logging
from pathlib import Path
from typing import Optional
import httpx
from config import settings
from models import Slide
from database import get_db  # caller passes db

logger = logging.getLogger(__name__)

_bulk_semaphore = asyncio.Semaphore(3)  # module-level; shared across bulk calls

class TTSService:
    API_URL = "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    DEFAULT_VOICE_ID = "21m00Tcm4TlvDq8ikWAM"  # Rachel

    AVAILABLE_VOICES = [
        {"voice_id": "21m00Tcm4TlvDq8ikWAM", "name": "Rachel", "description": "Calm, American female"},
        {"voice_id": "TxGEqnHWrfWFTfGW9XjX", "name": "Josh", "description": "Deep, American male"},
        {"voice_id": "EXAVITQu4vr4xnSDxMaL", "name": "Bella", "description": "Warm, British female"},
    ]

    def __init__(self):
        self.api_key = settings.ELEVENLABS_API_KEY

    async def generate_for_slide(self, slide: "Slide", voice_id: str, db) -> str:
        """
        Generate MP3 for a slide's narration_script.
        Updates Slide.narration_audio_url and Slide.narration_script_hash.
        Returns the audio URL.
        """
        script = slide.narration_script or ""
        script_hash = hashlib.sha256(script.encode()).hexdigest()

        audio_dir = Path(settings.UPLOAD_DIR) / "audio"
        audio_dir.mkdir(parents=True, exist_ok=True)
        filename = f"slide_{slide.id}.mp3"
        filepath = audio_dir / filename

        audio_bytes = await self._call_elevenlabs(script, voice_id)
        filepath.write_bytes(audio_bytes)

        audio_url = f"/uploads/audio/{filename}"
        slide.narration_audio_url = audio_url
        slide.narration_script_hash = script_hash
        db.commit()
        db.refresh(slide)
        return audio_url

    async def _call_elevenlabs(self, text: str, voice_id: str) -> bytes:
        url = self.API_URL.format(voice_id=voice_id)
        headers = {
            "xi-api-key": self.api_key,
            "Content-Type": "application/json",
            "Accept": "audio/mpeg",
        }
        body = {
            "text": text[:2500],
            "model_id": "eleven_flash_v2_5",
            "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
        }
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, json=body, headers=headers, timeout=30.0)
        if resp.status_code == 429:
            raise HTTPException(status_code=429, detail="ElevenLabs rate limit exceeded. Try again shortly.")
        if resp.status_code != 200:
            raise Exception(f"ElevenLabs API error: {resp.status_code}")
        return resp.content
```

### Pattern 3: Bulk Endpoint with Semaphore + Hash Cache
**What:** Processes all slides with scripts; skips unchanged; rate-limits to 3 concurrent.
**When to use:** TTS-02, TTS-03, TTS-04 — bulk generation from SlideBuilderPage.
**Example:**
```python
# backend/routers/tts.py
@router.post("/api/videos/{video_id}/tts/bulk-generate")
async def bulk_generate_audio(
    video_id: int,
    body: TTSGenerateRequest,
    db: Session = Depends(get_db),
    current_user=Depends(require_creator),
):
    video = _get_video_or_404(video_id, db, current_user)
    slides = db.query(Slide).filter(Slide.video_id == video_id).order_by(Slide.order_index).all()
    voice_id = body.voice_id or video.narration_voice_id or TTSService.DEFAULT_VOICE_ID

    results = {"generated": 0, "skipped_no_script": 0, "skipped_cached": 0, "errors": 0}

    async def process_slide(slide: Slide):
        if not slide.narration_script:
            results["skipped_no_script"] += 1
            return
        new_hash = hashlib.sha256(slide.narration_script.encode()).hexdigest()
        if slide.narration_script_hash == new_hash and slide.narration_audio_url:
            results["skipped_cached"] += 1
            return
        async with _bulk_semaphore:   # <-- module-level Semaphore(3)
            try:
                await tts_service.generate_for_slide(slide, voice_id, db)
                results["generated"] += 1
            except Exception as e:
                logger.error(f"Bulk TTS failed for slide {slide.id}: {e}")
                results["errors"] += 1

    await asyncio.gather(*[process_slide(s) for s in slides])
    return results
```

### Pattern 4: Frontend Audio Player in NarrationTab
**What:** HTML5 `<audio>` element with controls; shown when `narration_audio_url` is set.
**When to use:** TTS-01 — after per-slide audio generation completes.
**Example:**
```tsx
// NarrationTab.tsx additions
const [audioUrl, setAudioUrl] = useState<string | null>(slide.narration_audio_url ?? null)
const [generating, setGenerating] = useState(false)

const handleGenerateAudio = async () => {
  setGenerating(true)
  try {
    const res = await api.post(`/slides/${slideId}/tts/generate`, { voice_id: selectedVoiceId })
    const data = await res.json()
    setAudioUrl(data.audio_url)
  } finally {
    setGenerating(false)
  }
}

// In JSX:
{audioUrl && (
  <audio
    data-testid="narration-audio-player"
    controls
    src={`${API_BASE}${audioUrl}`}
    className="w-full mt-2"
  />
)}
<button
  data-testid="generate-audio-btn"
  onClick={handleGenerateAudio}
  disabled={!narrationScript || generating}
>
  {generating ? 'Generating...' : 'Generate audio'}
</button>
```

### Pattern 5: Voice Selection
**What:** Curated voice dropdown, stored on Video (already has `narration_voice_id` column).
**When to use:** TTS-05 — voice picker in NarrationTab or SlideBuilderPage header.
**Decision:** Place voice selector in NarrationTab (next to "Generate audio" button) since that is where audio is generated per-slide. Use `PATCH /api/videos/{id}` to persist `narration_voice_id`. Hardcode 3 voices; do not fetch dynamic list from ElevenLabs on page load.

### Anti-Patterns to Avoid
- **SSE streaming for TTS:** TTS returns binary audio bytes, not text tokens. Use regular `async def` endpoint returning JSON `{audio_url}` — not `EventSourceResponse`.
- **Storing audio bytes in DB:** Store the MP3 file under `uploads/audio/` and return the URL. Never store binary in a text column.
- **Re-instantiating Semaphore per request:** `_bulk_semaphore = asyncio.Semaphore(3)` must be module-level in `tts.py`, not created inside the endpoint function.
- **Calling ElevenLabs on every bulk run:** Always check `narration_script_hash` first; skip if hash matches and `narration_audio_url` is set.
- **Using eleven_monolingual_v1:** The legacy TTSService uses this deprecated model. Replace with `eleven_flash_v2_5`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Concurrent request limiting | Custom queue class | `asyncio.Semaphore(3)` | Stdlib; exact STATE.md recommendation; simple and battle-tested |
| Script change detection | String comparison of full text | `hashlib.sha256(s.encode()).hexdigest()` | O(1) comparison; 64-char string fits existing DB column type |
| Audio playback | Custom audio component | HTML5 `<audio controls>` | Zero deps; works in all modern browsers; plays MP3 natively |
| HTTP calls to ElevenLabs | Custom retry logic | `httpx.AsyncClient` + explicit 429 handling | httpx already installed; avoids adding elevenlabs SDK dependency |

**Key insight:** ElevenLabs offers a Python SDK (`elevenlabs` package) but the project already uses raw httpx for all external API calls (Claude, document fetch). Keeping httpx is more consistent and avoids an extra dependency.

---

## Common Pitfalls

### Pitfall 1: Semaphore Created Inside Endpoint Function
**What goes wrong:** Each request creates a fresh `Semaphore(3)`, so concurrency is never actually limited.
**Why it happens:** Forgetting that Semaphores are only effective when shared across coroutines.
**How to avoid:** Declare `_bulk_semaphore = asyncio.Semaphore(3)` at module level in `tts.py`, just like `claude_service = ClaudeService()` in `slides.py`.
**Warning signs:** All slides generate simultaneously; 429 errors appear in logs.

### Pitfall 2: DB Session Passed Across asyncio.gather Boundary
**What goes wrong:** SQLAlchemy sessions are not thread-safe. Sharing one session across concurrent coroutines in `gather()` causes integrity errors.
**Why it happens:** Passing the FastAPI `db` session (from `Depends(get_db)`) directly into parallel coroutines.
**How to avoid:** In `bulk_generate_audio`, the `process_slide` coroutine must operate with the same single session but because SQLite with `asyncio.gather` is serial in practice (GIL + sync ORM), this is acceptable if commits happen inside the semaphore block. With PostgreSQL, use `run_in_executor` or per-slide session. For SQLite target, the gather approach is safe.
**Warning signs:** `sqlite3.ProgrammingError: SQLite objects created in a thread can only be used in that thread`.

### Pitfall 3: Legacy TTSService Constructor Raises on Missing Key
**What goes wrong:** The existing `TTSService.__init__` raises `ValueError("ELEVENLABS_API_KEY not configured")` if the key is missing. This crashes the app at startup if the service is imported as a module-level singleton and the key is not set in `.env`.
**Why it happens:** Unlike `ClaudeService`, TTS was not designed as a lazy singleton.
**How to avoid:** Either (a) move the key check inside the method (lazy), or (b) use `settings.ELEVENLABS_API_KEY or ""` and raise on actual API calls only. The module-level singleton pattern (`tts_service = TTSService()`) is still correct — just defer the key check.
**Warning signs:** `ValueError: ELEVENLABS_API_KEY not configured` on any test run or server start.

### Pitfall 4: audio_url Served Without API_BASE Prefix
**What goes wrong:** `<audio src="/uploads/audio/slide_5.mp3">` works in production (nginx serves `/uploads/`) but fails in local dev where the FastAPI dev server serves static files.
**Why it happens:** Forgetting that uploads are served as static files by FastAPI `StaticFiles` mount (confirmed in main.py).
**How to avoid:** In the frontend, use `src={`${API_BASE}${audioUrl}`}` — same pattern as other asset URLs in the project.
**Warning signs:** Audio player shows but audio does not load (404 or CORS error in browser console).

### Pitfall 5: Slide.narration_audio_url Not Returned in SlideResponse
**What goes wrong:** NarrationTab renders `audioUrl` as null even after generation because `SlideResponse` in slides.py already includes `narration_audio_url` but the frontend `Slide` TypeScript type might not.
**Why it happens:** TypeScript interface in `NarrationTab` or `SlideEditorPage` defining `Slide` locally without `narration_audio_url`.
**How to avoid:** Extend the frontend `Slide` type to include `narration_audio_url: string | null` and `narration_script_hash: string | null`. The backend `SlideResponse` already exposes both (confirmed in slides.py lines 51-63).
**Warning signs:** `audioUrl` is always null after generation despite 200 response from endpoint.

### Pitfall 6: Missing ElevenLabs API Key in Test Environment
**What goes wrong:** Tests that call `TTSService()` as a module-level singleton raise `ValueError` at collection time, not at test execution.
**Why it happens:** `settings.ELEVENLABS_API_KEY` is empty in CI/test environment.
**How to avoid:** In `test_tts_phase17.py`, patch `services.tts_service.TTSService._call_elevenlabs` to return `b"fake_mp3_bytes"` before the service singleton is imported. Use `unittest.mock.patch` with `side_effect=AsyncMock(return_value=b"fake")`. Also ensure `tts_service = TTSService()` is instantiated lazily (after env check is removed from `__init__`).

---

## Code Examples

### ElevenLabs TTS API Call (verified from official docs)
```python
# Source: https://elevenlabs.io/docs/api-reference/text-to-speech/convert
# POST https://api.elevenlabs.io/v1/text-to-speech/{voice_id}
headers = {
    "xi-api-key": api_key,
    "Content-Type": "application/json",
    "Accept": "audio/mpeg",
}
body = {
    "text": "Hello world",
    "model_id": "eleven_flash_v2_5",          # recommended over turbo v2.5
    "voice_settings": {
        "stability": 0.5,
        "similarity_boost": 0.75,
    },
}
# Response: binary MP3 bytes (HTTP 200), application/octet-stream
# Error: HTTP 429 = rate limit (too_many_concurrent_requests or system_busy)
```

### Known-Good Voice IDs (pre-made, stable across accounts)
```python
AVAILABLE_VOICES = [
    {"voice_id": "21m00Tcm4TlvDq8ikWAM", "name": "Rachel"},  # calm, American female
    {"voice_id": "TxGEqnHWrfWFTfGW9XjX", "name": "Josh"},    # deep, American male
    {"voice_id": "EXAVITQu4vr4xnSDxMaL", "name": "Bella"},   # warm, British female
]
```
Note: These are pre-made library voices with stable IDs. Custom/cloned voices would need the creator's account voice IDs.

### Script Hash Computation
```python
import hashlib
script_hash = hashlib.sha256(narration_script.encode()).hexdigest()
# Returns 64-char hex string; fits Slide.narration_script_hash String(64)
```

### asyncio.Semaphore Bulk Pattern
```python
# Module-level — declared once, shared across all requests
_bulk_semaphore = asyncio.Semaphore(3)

async def process_slide(slide):
    async with _bulk_semaphore:
        await tts_service.generate_for_slide(slide, voice_id, db)

await asyncio.gather(*[process_slide(s) for s in slides])
```

### SlideBuilderPage Bulk Narration Button (currently disabled)
```tsx
// Current (disabled placeholder):
<button data-testid="bulk-narration-btn" disabled ...>Generate Narration</button>

// Phase 17 target (wired up):
<button
  data-testid="bulk-narration-btn"
  onClick={handleBulkGenerate}
  disabled={bulkGenerating}
>
  {bulkGenerating ? `Generating (${progress.generated}/${progress.total})...` : 'Generate Narration'}
</button>
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| eleven_monolingual_v1 | eleven_flash_v2_5 | ElevenLabs 2024-2025 | Flash is faster (~75ms), supports 32 languages, 40k char limit vs monolingual's limited scope |
| eleven_turbo_v2_5 | eleven_flash_v2_5 | ElevenLabs 2025 | Flash = functionally identical to Turbo but lower latency; Turbo deprecated in favour of Flash |
| Course.content JSON-based TTS | Per-Slide TTS with Slide model | Phase 10 migration | Old TTSService targets retired architecture; full rewrite needed |

**Deprecated/outdated:**
- `eleven_monolingual_v1`: Used in existing `tts_service.py`; replaced by `eleven_flash_v2_5`
- `generate_audio_for_course()` method in TTSService: Targets `Course.content` JSON blob (retired Phase 10). Replace entirely with `generate_for_slide()`.

---

## Open Questions

1. **ElevenLabs API key environment**
   - What we know: `settings.ELEVENLABS_API_KEY` is defined in `config.py` and reads from `ELEVENLABS_API_KEY` env var; defaults to empty string
   - What's unclear: Whether the key is configured in the Coolify production environment. STATE.md "Open Decisions" notes: "TTS provider: ElevenLabs vs OpenAI TTS — resolve before Phase 17. REQUIREMENTS.md specifies ElevenLabs; confirm API key exists."
   - Recommendation: Proceed with ElevenLabs (as specified in REQUIREMENTS.md). Include a health-check-style guard in the endpoint that returns HTTP 503 with `{"detail": "TTS service not configured — set ELEVENLABS_API_KEY"}` if the key is empty, rather than crashing.

2. **Voice IDs are account-specific for non-pre-made voices**
   - What we know: Pre-made voices (Rachel, Josh, Bella) have stable IDs across all ElevenLabs accounts
   - What's unclear: Whether the project owner's account has a subscription plan that unlocks all pre-made voices
   - Recommendation: Hardcode the three pre-made voices listed above; they are available on free and paid tiers.

3. **Bulk progress visibility — SSE vs JSON counts**
   - What we know: REQUIREMENTS.md TTS-02 says "progress is visible" but does not specify SSE vs polling
   - What's unclear: Whether real-time SSE progress updates are expected or a simple "X/Y slides generated" result count is sufficient
   - Recommendation: Return a simple JSON result `{generated, skipped_no_script, skipped_cached, errors}` after `asyncio.gather` completes. Show a spinner with slide count total during generation. This avoids SSE complexity for a non-streaming operation. If real-time progress is needed, upgrade to SSE in a later iteration.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (backend); vitest (frontend) |
| Config file | backend: pytest.ini / pyproject.toml not present — uses defaults; frontend: `frontend/vitest.config.ts` |
| Quick run command | `cd backend && source venv/bin/activate && python -m pytest tests/test_tts_phase17.py -x` |
| Full suite command | `cd backend && source venv/bin/activate && python -m pytest tests/ -x` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| TTS-01 | POST /api/slides/{id}/tts/generate returns audio_url; updates Slide | integration | `pytest tests/test_tts_phase17.py::test_generate_slide_audio -x` | Wave 0 |
| TTS-02 | POST /api/videos/{id}/tts/bulk-generate processes slides with scripts | integration | `pytest tests/test_tts_phase17.py::test_bulk_generate -x` | Wave 0 |
| TTS-03 | Semaphore limits to 3 concurrent ElevenLabs calls | unit | `pytest tests/test_tts_phase17.py::test_semaphore_limits_concurrency -x` | Wave 0 |
| TTS-04 | Bulk skips slides whose hash matches stored hash | integration | `pytest tests/test_tts_phase17.py::test_bulk_skips_cached_slides -x` | Wave 0 |
| TTS-05 | Voice ID selection reflected in ElevenLabs call | unit | `pytest tests/test_tts_phase17.py::test_voice_id_passed_to_elevenlabs -x` | Wave 0 |
| TTS-01 (FE) | NarrationTab renders audio player after generation | unit | `npx vitest run src/components/slide/__tests__/NarrationTab.test.tsx` | Wave 0 |

### Sampling Rate
- **Per task commit:** `python -m pytest tests/test_tts_phase17.py -x`
- **Per wave merge:** `python -m pytest tests/ -x`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `backend/tests/test_tts_phase17.py` — covers TTS-01 through TTS-05 (pytest.fail() stubs)
- [ ] Frontend NarrationTab test extensions in `frontend/src/components/slide/__tests__/NarrationTab.test.tsx` — covers TTS-01 audio player rendering

*(No new framework installs needed — pytest and vitest already configured)*

---

## Key Findings Summary

1. **No migration needed.** `Slide.narration_audio_url` (String 500) and `Slide.narration_script_hash` (String 64) already exist in `models.py` and the Phase 10 Alembic migration `002_create_new_tables.py`. The `Video.narration_voice_id` column also exists for storing the chosen voice.

2. **Legacy TTSService must be rewritten.** The existing `backend/services/tts_service.py` targets the retired `Course.content` JSON blob with `generate_audio_for_course()`. It must be replaced with a `generate_for_slide()` method. Model should change from `eleven_monolingual_v1` to `eleven_flash_v2_5`.

3. **Bulk button already exists in SlideBuilderPage.** `data-testid="bulk-narration-btn"` is rendered but `disabled` with a placeholder title. Wiring it up (SLIDE-03) is entirely a frontend change in SlideBuilderPage + a new bulk endpoint.

4. **`asyncio.Semaphore(3)` is mandatory at module level.** STATE.md pitfall #6 explicitly calls this out. The semaphore must be declared once as a module-level variable in `tts.py`.

5. **Use `eleven_flash_v2_5`.** ElevenLabs documentation (2025/2026) recommends Flash over Turbo in all cases; they are functionally equivalent but Flash has lower latency. The legacy service used the deprecated `eleven_monolingual_v1`.

---

## Sources

### Primary (HIGH confidence)
- Direct codebase inspection — `backend/models/models.py`, `backend/services/tts_service.py`, `backend/routers/slides.py`, `backend/config.py`, `frontend/src/components/slide/NarrationTab.tsx`, `frontend/src/pages/creator/SlideBuilderPage.tsx`
- `https://elevenlabs.io/docs/api-reference/text-to-speech/convert` — endpoint, headers, body fields, response format
- `https://elevenlabs.io/docs/overview/models` — model comparison, eleven_flash_v2_5 vs turbo recommendation

### Secondary (MEDIUM confidence)
- ElevenLabs voice IDs for Rachel/Josh: confirmed by multiple sources including `https://json2video.com/ai-voices/elevenlabs/voices/21m00Tcm4TlvDq8ikWAM/` (Rachel) and search results showing TxGEqnHWrfWFTfGW9XjX for Josh
- Concurrent limit handling patterns: `https://help.elevenlabs.io/hc/en-us/articles/19571824571921-API-Error-Code-429` (referenced in search results)

### Tertiary (LOW confidence)
- Bella voice ID `EXAVITQu4vr4xnSDxMaL` — from audio-generation-plugin.com listing; should be verified against the ElevenLabs API `GET /v2/voices?category=premade` before shipping

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries are already installed; ElevenLabs API documented at official source
- Architecture: HIGH — data model confirmed directly in codebase; endpoint patterns follow established project conventions
- Pitfalls: HIGH — semaphore requirement from STATE.md; others from direct code inspection
- Voice IDs: MEDIUM — Rachel confirmed by multiple sources; Josh and Bella from secondary sources only

**Research date:** 2026-05-10
**Valid until:** 2026-06-10 (ElevenLabs API is stable; model names confirmed current)
