# HeyGen Pre-rendered Avatar Video — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Render a HeyGen avatar video for each broadcast segment (lip-synced to the existing ElevenLabs narration) and play it in the ILB player, falling back to audio when a video isn't available.

**Architecture:** Async submit+poll. A `HeyGenAvatarProvider` uploads each segment's MP3 to HeyGen as an asset, submits a video-generation job, and polls for completion; the finished MP4 is downloaded and self-hosted under `/api/media/video/…`. The player shows a `<video>` for any segment that has a rendered URL (reusing the existing autoplay/auto-advance logic) and an `<audio>` otherwise.

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, httpx (async), React + TypeScript + Vitest, pytest.

**Spec:** `docs/superpowers/specs/2026-05-25-heygen-avatar-design.md`

---

## HeyGen API reference (verified 2026-05, target v1/v2)

- **Auth:** header `X-Api-Key: <key>`. Base `https://api.heygen.com`. Asset upload host `https://upload.heygen.com`.
- **Upload audio asset:** `POST https://upload.heygen.com/v1/asset`, **raw binary body**, `Content-Type: audio/mpeg`, header `X-Api-Key`. Response: `{"code":100,"data":{"id":"<asset_id>",...}}`.
- **Generate video:** `POST https://api.heygen.com/v2/video/generate`
  ```json
  {
    "title": "...", "test": false,
    "dimension": {"width": 1280, "height": 720},
    "video_inputs": [{
      "character": {"type": "avatar", "avatar_id": "<id>", "avatar_style": "normal"},
      "voice": {"type": "audio", "audio_asset_id": "<asset_id>"},
      "background": {"type": "color", "value": "#1F2937"}
    }]
  }
  ```
  Response: `{"data":{"video_id":"..."},"error":null}`. (Use `audio_asset_id` from upload — exactly one of `audio_asset_id`/`audio_url`.)
- **Status:** `GET https://api.heygen.com/v1/video_status.get?video_id=<id>` →
  `{"code":100,"data":{"status":"pending|processing|completed|failed","video_url":"<mp4?Expires=...>","error":null}}`. The `video_url` **expires (~7 days) → download immediately**.
- **Default stock avatar:** `Kristin_public_3_20240108` (style `normal`). List via `GET /v2/avatars`.
- **Gotchas:** API generation needs a paid plan; trial keys watermark output; render ~30s–few min; handle `failed` + unreachable inputs.

---

## File structure

**Backend**
- Modify `backend/models/models.py` — add `segment_video`, `video_render_jobs` to `Broadcast`.
- Create `backend/alembic/versions/014_broadcast_avatar_video.py` — migration.
- Modify `backend/services/integrations.py` — change `AvatarProvider` ABC; add `HeyGenAvatarProvider`; update `get_avatar_provider()`; add `DEFAULT_HEYGEN_AVATAR_ID`.
- Modify `backend/routers/ilb.py` — add `segment_video` to `BroadcastOut`; add `render-avatar` + `avatar-status` endpoints.
- Test `backend/tests/test_heygen_avatar.py` — provider + endpoints.

**Frontend**
- Modify `frontend/src/services/ilbApi.ts` — `segment_video` on types; `renderAvatar`, `avatarStatus`.
- Modify `frontend/src/pages/learn/ILBPlayerPage.tsx` — `<video>` rendering + generalized autoplay.
- Modify `frontend/src/pages/creator/CreatorStandaloneBroadcasts.tsx` — "Render avatar" control.
- Test `frontend/src/pages/learn/__tests__/ILBPlayerPage.test.tsx` — video render + advance.

---

## Task 1: Broadcast data model + migration

**Files:**
- Modify: `backend/models/models.py` (the `Broadcast` class — add two columns next to `segment_audio`)
- Create: `backend/alembic/versions/014_broadcast_avatar_video.py`

- [ ] **Step 1: Add columns to the Broadcast model**

In `backend/models/models.py`, find the `Broadcast` class. Immediately after its `segment_audio` column add:

```python
    segment_video = Column(JSON, nullable=True)        # parallel to segment_audio; MP4 URLs (or None per seg)
    video_render_jobs = Column(JSON, nullable=True)    # [{"seg_index": int, "heygen_video_id": str, "status": str}]
```

(`JSON` is already imported in this module.)

- [ ] **Step 2: Create migration 014**

Create `backend/alembic/versions/014_broadcast_avatar_video.py`:

```python
"""Add Broadcast.segment_video + video_render_jobs (HeyGen pre-rendered avatar).

Revision ID: 014
Revises: 013
Create Date: 2026-05-25
"""
from alembic import op
import sqlalchemy as sa

revision = '014'
down_revision = '013'
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table('broadcasts') as batch_op:
        batch_op.add_column(sa.Column('segment_video', sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column('video_render_jobs', sa.JSON(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('broadcasts') as batch_op:
        batch_op.drop_column('video_render_jobs')
        batch_op.drop_column('segment_video')
```

- [ ] **Step 3: Verify the model imports and the column exists**

Run: `cd backend && source venv/bin/activate && python -c "from models import Broadcast; print('segment_video' in Broadcast.__table__.columns, 'video_render_jobs' in Broadcast.__table__.columns)"`
Expected: `True True`

- [ ] **Step 4: Commit**

```bash
git add backend/models/models.py backend/alembic/versions/014_broadcast_avatar_video.py
git commit -m "feat(ilb): Broadcast.segment_video + video_render_jobs for HeyGen avatar"
```

---

## Task 2: HeyGen avatar provider

**Files:**
- Modify: `backend/services/integrations.py`
- Test: `backend/tests/test_heygen_avatar.py`

- [ ] **Step 1: Write the failing provider tests**

Create `backend/tests/test_heygen_avatar.py`:

```python
import pytest
from unittest.mock import patch, MagicMock
import httpx

from services.integrations import HeyGenAvatarProvider, StubAvatarProvider, get_avatar_provider


@pytest.mark.asyncio
async def test_stub_completes_immediately():
    stub = StubAvatarProvider()
    vid = await stub.submit_segment(b"audio", "audio/mpeg", "avatar1")
    assert isinstance(vid, str) and vid
    status, url = await stub.poll(vid)
    assert status == "completed"
    assert url and url.endswith(".mp4")


@pytest.mark.asyncio
async def test_heygen_submit_uploads_then_generates():
    prov = HeyGenAvatarProvider(api_key="k")
    calls = {}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "upload.heygen.com":
            calls["upload"] = request.headers.get("content-type")
            return httpx.Response(200, json={"code": 100, "data": {"id": "asset_9"}})
        if str(request.url).endswith("/v2/video/generate"):
            import json as _j
            calls["body"] = _j.loads(request.content)
            return httpx.Response(200, json={"data": {"video_id": "vid_7"}, "error": None})
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    with patch("services.integrations.httpx.AsyncClient",
               lambda *a, **k: httpx.AsyncClient(transport=transport)):
        vid = await prov.submit_segment(b"MP3BYTES", "audio/mpeg", "avatarX")

    assert vid == "vid_7"
    assert calls["upload"] == "audio/mpeg"
    vi = calls["body"]["video_inputs"][0]
    assert vi["character"]["avatar_id"] == "avatarX"
    assert vi["voice"] == {"type": "audio", "audio_asset_id": "asset_9"}


@pytest.mark.asyncio
async def test_heygen_poll_returns_status_and_url():
    prov = HeyGenAvatarProvider(api_key="k")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"code": 100, "data": {
            "status": "completed", "video_url": "https://h/v.mp4?Expires=1", "error": None}})

    transport = httpx.MockTransport(handler)
    with patch("services.integrations.httpx.AsyncClient",
               lambda *a, **k: httpx.AsyncClient(transport=transport)):
        status, url = await prov.poll("vid_7")
    assert status == "completed"
    assert url == "https://h/v.mp4?Expires=1"


def test_factory_picks_heygen_when_key_set():
    with patch("services.integrations.settings") as s:
        s.HEYGEN_API_KEY = "k"
        assert isinstance(get_avatar_provider(), HeyGenAvatarProvider)
        s.HEYGEN_API_KEY = ""
        assert isinstance(get_avatar_provider(), StubAvatarProvider)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && source venv/bin/activate && python -m pytest tests/test_heygen_avatar.py -q`
Expected: FAIL — `ImportError: cannot import name 'HeyGenAvatarProvider'`.

- [ ] **Step 3: Change the AvatarProvider ABC + implement providers**

In `backend/services/integrations.py`:

(a) Add imports near the top (after existing imports):
```python
from config import settings

DEFAULT_HEYGEN_AVATAR_ID = "Kristin_public_3_20240108"
HEYGEN_API_BASE = "https://api.heygen.com"
HEYGEN_UPLOAD_BASE = "https://upload.heygen.com"
```

(b) Replace the `AvatarProvider` ABC's `prerender` method (keep `create_live_session`):
```python
class AvatarProvider(ABC):
    @abstractmethod
    async def submit_segment(self, audio: bytes, content_type: str, avatar_id: str) -> str:
        """Submit a lip-synced avatar-video render job; return a provider job/video id."""
        raise NotImplementedError

    @abstractmethod
    async def poll(self, video_id: str) -> tuple[str, Optional[str]]:
        """Return (status, mp4_url|None). status in {processing, completed, failed}."""
        raise NotImplementedError

    @abstractmethod
    def create_live_session(self, avatar_id: str) -> Dict[str, Any]:
        """Open a live interactive-avatar session; return transport details for the client."""
        raise NotImplementedError
```

(c) Replace `StubAvatarProvider.prerender` with the new async methods (keep its `create_live_session`):
```python
    async def submit_segment(self, audio: bytes, content_type: str, avatar_id: str) -> str:
        return f"stub-video-{avatar_id}-{len(audio)}"

    async def poll(self, video_id: str) -> tuple[str, Optional[str]]:
        return ("completed", "/api/media/video/stub.mp4")
```

(d) Add the real provider after `StubAvatarProvider`:
```python
class HeyGenAvatarProvider(AvatarProvider):
    """HeyGen Video-Generation: upload audio asset -> generate lip-synced avatar video -> poll."""

    def __init__(self, api_key: Optional[str] = None):
        self._api_key = api_key

    @property
    def api_key(self) -> str:
        return self._api_key if self._api_key is not None else (settings.HEYGEN_API_KEY or "")

    async def _upload_audio(self, audio: bytes, content_type: str) -> str:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{HEYGEN_UPLOAD_BASE}/v1/asset",
                content=audio,
                headers={"X-Api-Key": self.api_key, "Content-Type": content_type or "audio/mpeg"},
                timeout=60.0,
            )
        if resp.status_code != 200:
            raise Exception(f"HeyGen asset upload failed: {resp.status_code} {resp.text[:200]}")
        return resp.json()["data"]["id"]

    async def submit_segment(self, audio: bytes, content_type: str, avatar_id: str) -> str:
        asset_id = await self._upload_audio(audio, content_type)
        body = {
            "test": False,
            "dimension": {"width": 1280, "height": 720},
            "video_inputs": [{
                "character": {"type": "avatar", "avatar_id": avatar_id, "avatar_style": "normal"},
                "voice": {"type": "audio", "audio_asset_id": asset_id},
                "background": {"type": "color", "value": "#1F2937"},
            }],
        }
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{HEYGEN_API_BASE}/v2/video/generate",
                json=body,
                headers={"X-Api-Key": self.api_key, "Content-Type": "application/json"},
                timeout=60.0,
            )
        if resp.status_code != 200:
            raise Exception(f"HeyGen generate failed: {resp.status_code} {resp.text[:200]}")
        data = resp.json().get("data") or {}
        video_id = data.get("video_id")
        if not video_id:
            raise Exception(f"HeyGen generate: no video_id ({resp.text[:200]})")
        return video_id

    async def poll(self, video_id: str) -> tuple[str, Optional[str]]:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{HEYGEN_API_BASE}/v1/video_status.get",
                params={"video_id": video_id},
                headers={"X-Api-Key": self.api_key},
                timeout=30.0,
            )
        if resp.status_code != 200:
            return ("processing", None)  # transient; caller retries
        data = resp.json().get("data") or {}
        status = data.get("status", "processing")
        if status == "completed":
            return ("completed", data.get("video_url"))
        if status == "failed":
            return ("failed", None)
        return ("processing", None)

    def create_live_session(self, avatar_id: str) -> Dict[str, Any]:
        # Live streaming avatar is out of scope for this increment — keep the stub transport.
        return StubAvatarProvider().create_live_session(avatar_id)
```

(e) Update the factory:
```python
def get_avatar_provider(real: Optional[AvatarProvider] = None) -> AvatarProvider:
    if real:
        return real
    if settings.HEYGEN_API_KEY:
        return HeyGenAvatarProvider()
    return StubAvatarProvider()
```

Ensure `Optional` and `httpx` are imported at the top of the module (they are).

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && source venv/bin/activate && python -m pytest tests/test_heygen_avatar.py -q`
Expected: PASS (4 passed).

- [ ] **Step 5: Regression — ensure ilb router still imports (create_live_session unchanged)**

Run: `cd backend && source venv/bin/activate && python -m pytest tests/test_ilb_router.py -q`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/services/integrations.py backend/tests/test_heygen_avatar.py
git commit -m "feat(ilb): HeyGen avatar provider (upload+generate+poll) with stub fallback"
```

---

## Task 3: render-avatar + avatar-status endpoints

**Files:**
- Modify: `backend/routers/ilb.py` (the standalone-broadcasts section, near `render-audio` at ~line 789, and `BroadcastOut` at ~line 641)
- Test: append to `backend/tests/test_heygen_avatar.py`

- [ ] **Step 1: Write failing endpoint tests**

Append to `backend/tests/test_heygen_avatar.py`:

```python
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock
from main import app
import routers.ilb as ilb_router

client = TestClient(app)


def _make_broadcast(creator_token, db):
    h = {"Authorization": f"Bearer {creator_token}"}
    bid = client.post("/api/ilb/broadcasts", json={"title": "AV"}, headers=h).json()["id"]
    client.put(f"/api/ilb/broadcasts/{bid}",
               json={"script": "Seg one.[SEGMENT BREAK]Seg two."}, headers=h)
    # pretend audio was rendered
    from models import Broadcast
    b = db.query(Broadcast).get(bid)
    b.segment_audio = [f"/api/media/audio/ilb_bcast_{bid}_seg_0.mp3",
                       f"/api/media/audio/ilb_bcast_{bid}_seg_1.mp3"]
    db.commit()
    return bid, h


def test_render_avatar_503_without_key(creator_token, db, monkeypatch):
    monkeypatch.setattr(ilb_router.settings, "HEYGEN_API_KEY", "")
    bid, h = _make_broadcast(creator_token, db)
    r = client.post(f"/api/ilb/broadcasts/{bid}/render-avatar", headers=h)
    assert r.status_code == 503


def test_render_avatar_submits_jobs(creator_token, db, monkeypatch):
    monkeypatch.setattr(ilb_router.settings, "HEYGEN_API_KEY", "k")
    bid, h = _make_broadcast(creator_token, db)
    fake = AsyncMock()
    fake.submit_segment = AsyncMock(side_effect=["v0", "v1"])
    monkeypatch.setattr(ilb_router, "get_avatar_provider", lambda: fake)
    # audio files must exist on disk for the endpoint to read them
    import os
    os.makedirs("uploads/audio", exist_ok=True)
    for i in range(2):
        open(f"uploads/audio/ilb_bcast_{bid}_seg_{i}.mp3", "wb").write(b"ID3test")
    r = client.post(f"/api/ilb/broadcasts/{bid}/render-avatar", headers=h)
    assert r.status_code == 200
    jobs = r.json()["jobs"]
    assert [j["heygen_video_id"] for j in jobs] == ["v0", "v1"]
    assert all(j["status"] == "processing" for j in jobs)


def test_avatar_status_completes_and_downloads(creator_token, db, monkeypatch, tmp_path):
    monkeypatch.setattr(ilb_router.settings, "HEYGEN_API_KEY", "k")
    bid, h = _make_broadcast(creator_token, db)
    from models import Broadcast
    b = db.query(Broadcast).get(bid)
    b.video_render_jobs = [{"seg_index": 0, "heygen_video_id": "v0", "status": "processing"}]
    b.segment_video = [None, None]
    db.commit()
    fake = AsyncMock()
    fake.poll = AsyncMock(return_value=("completed", "https://h/v0.mp4?Expires=1"))
    monkeypatch.setattr(ilb_router, "get_avatar_provider", lambda: fake)
    monkeypatch.setattr(ilb_router, "_download_bytes", AsyncMock(return_value=b"MP4DATA"))
    r = client.get(f"/api/ilb/broadcasts/{bid}/avatar-status", headers=h)
    assert r.status_code == 200
    body = r.json()
    assert body["overall"] == "complete"
    db.refresh(b)
    assert b.segment_video[0] == f"/api/media/video/ilb_bcast_{bid}_seg_0.mp4"
```

- [ ] **Step 2: Run to verify they fail**

Run: `cd backend && source venv/bin/activate && python -m pytest tests/test_heygen_avatar.py -q`
Expected: FAIL (endpoints / `_download_bytes` not defined; `segment_video` not on `BroadcastOut`).

- [ ] **Step 3: Add `segment_video` to BroadcastOut**

In `backend/routers/ilb.py`, in `class BroadcastOut`, after `segment_audio`:
```python
    segment_video: Optional[List[str]] = None
```

- [ ] **Step 4: Add a download helper + the two endpoints**

In `backend/routers/ilb.py`, ensure these imports exist at top: `from services.integrations import get_avatar_provider, get_stt_provider` (already present) and `from config import settings` (already imported inside functions; add a module-level `from config import settings` if not present at module scope — the tests monkeypatch `ilb_router.settings`, so it MUST be a module-level name). Add at module scope near other imports:
```python
from config import settings
```

Add a module-level helper (near the other helpers, before the endpoints):
```python
async def _download_bytes(url: str) -> bytes:
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, timeout=120.0)
    resp.raise_for_status()
    return resp.content
```
(`httpx` is already imported in this module.)

Add the endpoints right after `publish_broadcast`:
```python
@router.post("/broadcasts/{broadcast_id}/render-avatar")
async def render_broadcast_avatar(
    broadcast_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """Submit one HeyGen avatar-video job per segment (lip-synced to its narration audio)."""
    _require_creator(current_user)
    b = _get_broadcast(db, broadcast_id)
    if not settings.HEYGEN_API_KEY:
        raise HTTPException(status_code=503, detail="Avatar video not configured (HEYGEN_API_KEY)")
    segs = b.segments or []
    audio = b.segment_audio or []
    if not segs or not audio:
        raise HTTPException(status_code=422, detail="Render the narration audio first")

    from pathlib import Path
    avatar_id = b.avatar_id or DEFAULT_HEYGEN_AVATAR_ID
    provider = get_avatar_provider()
    jobs: List[Dict[str, Any]] = []
    seg_video: List[Optional[str]] = [None] * len(segs)
    for i, _seg in enumerate(segs):
        url = audio[i] if i < len(audio) else None
        if not url:
            jobs.append({"seg_index": i, "heygen_video_id": None, "status": "failed"})
            continue
        fname = url.rsplit("/", 1)[-1]            # ilb_bcast_{id}_seg_{i}.mp3
        path = Path(settings.UPLOAD_DIR) / "audio" / fname
        if not path.exists():
            jobs.append({"seg_index": i, "heygen_video_id": None, "status": "failed"})
            continue
        try:
            vid = await provider.submit_segment(path.read_bytes(), "audio/mpeg", avatar_id)
            jobs.append({"seg_index": i, "heygen_video_id": vid, "status": "processing"})
        except Exception as e:
            logger.error(f"HeyGen submit failed seg {i}: {e}")
            jobs.append({"seg_index": i, "heygen_video_id": None, "status": "failed"})

    b.video_render_jobs = jobs
    b.segment_video = seg_video
    db.commit()
    return {"jobs": jobs}


@router.get("/broadcasts/{broadcast_id}/avatar-status")
async def broadcast_avatar_status(
    broadcast_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """Poll HeyGen for each processing job; download completed MP4s and store the URL."""
    _require_creator(current_user)
    b = _get_broadcast(db, broadcast_id)
    jobs = list(b.video_render_jobs or [])
    seg_video = list(b.segment_video or [None] * len(b.segments or []))
    provider = get_avatar_provider()

    from pathlib import Path
    video_dir = Path(settings.UPLOAD_DIR) / "video"
    video_dir.mkdir(parents=True, exist_ok=True)

    changed = False
    for job in jobs:
        if job.get("status") != "processing":
            continue
        vid = job.get("heygen_video_id")
        i = job["seg_index"]
        try:
            status, url = await provider.poll(vid)
        except Exception as e:
            logger.error(f"HeyGen poll failed seg {i}: {e}")
            continue
        if status == "completed" and url:
            try:
                data = await _download_bytes(url)
                fname = f"ilb_bcast_{broadcast_id}_seg_{i}.mp4"
                (video_dir / fname).write_bytes(data)
                while len(seg_video) <= i:
                    seg_video.append(None)
                seg_video[i] = f"/api/media/video/{fname}"
                job["status"] = "completed"
                changed = True
            except Exception as e:
                logger.error(f"Avatar MP4 download failed seg {i}: {e}")
                job["status"] = "failed"
                changed = True
        elif status == "failed":
            job["status"] = "failed"
            changed = True

    if changed:
        b.video_render_jobs = jobs
        b.segment_video = seg_video
        db.commit()

    statuses = [j.get("status") for j in jobs]
    overall = "complete" if statuses and all(s in ("completed", "failed") for s in statuses) else "processing"
    return {"overall": overall, "segments": jobs, "segment_video": seg_video}
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd backend && source venv/bin/activate && python -m pytest tests/test_heygen_avatar.py -q`
Expected: PASS (7 passed).

- [ ] **Step 6: Commit**

```bash
git add backend/routers/ilb.py backend/tests/test_heygen_avatar.py
git commit -m "feat(ilb): render-avatar + avatar-status endpoints (submit/poll/download)"
```

---

## Task 4: Frontend ilbApi — types + methods

**Files:**
- Modify: `frontend/src/services/ilbApi.ts`

- [ ] **Step 1: Add `segment_video` to the broadcast/podcast types**

In `BroadcastDetail` and `PodcastConfig` interfaces, add after `segment_audio`:
```typescript
  segment_video: string[] | null
```

- [ ] **Step 2: Add the two API methods**

In the `ilbApi` object, after `renderBroadcastAudio`:
```typescript
  renderBroadcastAvatar: (id: number): Promise<{ jobs: { seg_index: number; status: string }[] }> =>
    api.post(`/ilb/broadcasts/${id}/render-avatar`, {}).then((r) => unwrap(r)),

  broadcastAvatarStatus: (id: number): Promise<{ overall: string; segments: { seg_index: number; status: string }[]; segment_video: (string | null)[] }> =>
    api.get(`/ilb/broadcasts/${id}/avatar-status`).then((r) => unwrap(r)),
```

- [ ] **Step 3: Typecheck**

Run: `cd frontend && npx tsc -b`
Expected: exit 0.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/services/ilbApi.ts
git commit -m "feat(ilb): ilbApi renderBroadcastAvatar + broadcastAvatarStatus + segment_video type"
```

---

## Task 5: Player — show avatar video + generalized autoplay

**Files:**
- Modify: `frontend/src/pages/learn/ILBPlayerPage.tsx`
- Test: `frontend/src/pages/learn/__tests__/ILBPlayerPage.test.tsx`

- [ ] **Step 1: Write a failing player test (video renders + advances on ended)**

Append a test to `ILBPlayerPage.test.tsx` (mirror existing setup; the broadcast config mock needs `segment_video`). Add inside the existing `describe`:

```typescript
  it('plays an avatar video and auto-advances on ended', async () => {
    mockedIlb.getPodcast.mockResolvedValue({
      ...publishedConfig,
      segments: ['Seg one.', 'Seg two.'],
      segment_audio: null,
      segment_video: ['/api/media/video/a.mp4', '/api/media/video/b.mp4'],
    })
    mockedIlb.startSession.mockResolvedValue({
      session: { id: 1, enrollment_id: 1, mode: 'interrupt', completion_status: 'in_progress', started_at: '', completed_at: null, final_score: null },
      live: { provider: 'stub', avatar_id: 'demo', livekit_url: '', token: '', session_id: 's1' },
    })
    renderPlayer()
    await userEvent.click(await screen.findByText('Start broadcast'))
    const video = document.querySelector('video') as HTMLVideoElement
    expect(video).toBeTruthy()
    expect(video.getAttribute('src')).toContain('/api/media/video/a.mp4')
    // simulate the first clip ending → should advance to segment 2/3 wording
    video.dispatchEvent(new Event('ended'))
    expect(await screen.findByText(/Segment 2\/2/)).toBeInTheDocument()
  })
```

(Note: `publishedConfig` currently has no `segment_video`; add `segment_video: null` to the shared `publishedConfig` object so existing tests still type-match.)

- [ ] **Step 2: Run to verify it fails**

Run: `cd frontend && npx vitest run src/pages/learn/__tests__/ILBPlayerPage.test.tsx`
Expected: FAIL (no `<video>` rendered).

- [ ] **Step 3: Add segment_video state + currentVideo + a media ref that covers both**

In `ILBPlayerPage.tsx`:

(a) Add state near `segmentAudio`:
```typescript
  const [segmentVideo, setSegmentVideo] = useState<string[]>([])
```
(b) In the config `.then((cfg) => {...})` block, after `setSegmentAudio(...)`:
```typescript
      setSegmentVideo(cfg.segment_video ?? [])
```
(c) Add a derived value near `currentAudio`:
```typescript
  const currentVideo = segmentVideo.length > 0 ? segmentVideo[Math.min(segIdx, segmentVideo.length - 1)] : null
```
(d) Generalize the existing play/pause effect and `audioRef` to also drive the video. Change the ref type and the effect to query whichever media element is mounted:
```typescript
  const mediaRef = useRef<HTMLMediaElement | null>(null)
```
Replace `audioRef` usages with `mediaRef`. Update the play/pause effect dependency list to include `currentVideo`:
```typescript
  useEffect(() => {
    const el = mediaRef.current
    if (!el) return
    if (state === 'playing') void el.play().catch(() => {})
    else el.pause()
  }, [state, segIdx, currentAudio, currentVideo])
```
(e) Update the timer-fallback effect guard so it does NOT run when a video is present (video drives advance via onEnded):
```typescript
    if (currentAudio || currentVideo) return
```
and add `currentVideo` to that effect's dependency array.

- [ ] **Step 4: Render the `<video>` in the avatar stage**

In the avatar stage JSX, replace the block that currently renders the segment text + `<audio>` so that when `currentVideo` exists it renders a `<video>` (which carries its own audio), else the existing audio/text path:

```tsx
            ) : started && currentSegment ? (
              <div className="w-full h-full flex flex-col gap-2 overflow-y-auto">
                {currentVideo ? (
                  <video
                    key={`v-${segIdx}`}
                    ref={mediaRef as React.RefObject<HTMLVideoElement>}
                    controls
                    onEnded={handleSegmentEnded}
                    src={`${API_BASE}${currentVideo}`}
                    className="w-full h-full object-contain"
                  />
                ) : (
                  <>
                    <p className="text-gray-200 text-sm leading-relaxed">{currentSegment}</p>
                    {currentAudio && (
                      <audio
                        key={`a-${segIdx}`}
                        ref={mediaRef as React.RefObject<HTMLAudioElement>}
                        controls
                        onEnded={handleSegmentEnded}
                        src={`${API_BASE}${currentAudio}`}
                        className="w-full mt-auto"
                      />
                    )}
                  </>
                )}
              </div>
            ) : (
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd frontend && npx vitest run src/pages/learn/__tests__/ILBPlayerPage.test.tsx`
Expected: PASS.

- [ ] **Step 6: Typecheck**

Run: `cd frontend && npx tsc -b`
Expected: exit 0.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/pages/learn/ILBPlayerPage.tsx frontend/src/pages/learn/__tests__/ILBPlayerPage.test.tsx
git commit -m "feat(ilb): player renders avatar <video> with audio fallback + shared autoplay"
```

---

## Task 6: Authoring — "Render avatar" control

**Files:**
- Modify: `frontend/src/pages/creator/CreatorStandaloneBroadcasts.tsx`

- [ ] **Step 1: Add a videoCount state + a renderAvatar action**

Near the existing `const [audioCount, setAudioCount] = useState<...>(...)`, add:
```typescript
  const [videoCount, setVideoCount] = useState<number | null>(null)
```
In the broadcast-load effect where `setAudioCount(b.segment_audio?.length ?? null)` is set, also add:
```typescript
      setVideoCount(b.segment_video?.filter(Boolean).length ?? null)
```

Add this function next to `renderAudio()`:
```typescript
  async function renderAvatar() {
    if (selectedId == null) return
    await run('avatar', async () => {
      await ilbApi.renderBroadcastAvatar(selectedId)
      setStatus('Avatar render started…')
      // poll until all jobs settle
      for (let i = 0; i < 60; i++) {
        await new Promise((r) => setTimeout(r, 5000))
        const s = await ilbApi.broadcastAvatarStatus(selectedId)
        const done = s.segments.filter((j) => j.status === 'completed').length
        setStatus(`Rendering avatar… ${done}/${s.segments.length}`)
        if (s.overall === 'complete') {
          setVideoCount(s.segment_video.filter(Boolean).length)
          setStatus(`Avatar video ready — ${s.segment_video.filter(Boolean).length} clip(s).`)
          return
        }
      }
      setStatus('Avatar render still processing — check back shortly.')
    })
  }
```

- [ ] **Step 2: Add the button**

After the "Render audio" `<button>` in the action row, add:
```tsx
            <button onClick={() => void renderAvatar()} disabled={busy != null || !audioCount} className="px-4 py-2 rounded bg-fuchsia-700 text-white text-sm font-medium hover:bg-fuchsia-600 disabled:opacity-50">
              {busy === 'avatar' ? 'Rendering…' : videoCount ? `Re-render avatar (${videoCount})` : 'Render avatar'}
            </button>
```

- [ ] **Step 3: Typecheck**

Run: `cd frontend && npx tsc -b`
Expected: exit 0.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/creator/CreatorStandaloneBroadcasts.tsx
git commit -m "feat(ilb): creator 'Render avatar' control with status polling"
```

---

## Task 7: Full verification + deploy

- [ ] **Step 1: Backend suite**

Run: `cd backend && source venv/bin/activate && python -m pytest tests/test_heygen_avatar.py tests/test_ilb_router.py tests/test_tts_phase17.py -q`
Expected: all PASS.

- [ ] **Step 2: Frontend tests + build**

Run: `cd frontend && npx tsc -b && npx vitest run src/pages/learn src/pages/admin`
Expected: tsc exit 0; tests PASS.

- [ ] **Step 3: Commit any fixups, then push**

```bash
git push origin main
```

- [ ] **Step 4: Deploy backend + frontend via Coolify API** (uuids: backend `grezgrjpzsiy1x1aqlqu4yml`, frontend `dta9d9jm5k5tb94wnomxfxps`) and wait for both `finished`.

- [ ] **Step 5: Live check (manual, needs HeyGen key in Settings + a paid HeyGen plan)**

As admin/creator: create a 2-segment broadcast, Render audio, Render avatar, wait for completion, open `/learn/broadcast/<id>`, Start — confirm the avatar **video** plays and auto-advances on each clip's end, stopping at the last segment. If HeyGen is on a trial tier, expect a watermark (still validates the pipeline).

---

## Notes for the executor
- Prod SQLite has **no persistent volume**: every backend redeploy wipes the DB and `uploads/`. Rendered videos/audio and DB rows do not survive a redeploy — re-create test data after deploying. `init_db()` (`create_all`) recreates the new columns from the model, so the feature works on the wiped prod DB even though migration 014 is for the dev chain.
- HeyGen video URLs expire (~7 days) — that's why `avatar-status` downloads the MP4 immediately and serves it from `/api/media/video/…`.
- Keep changes scoped to standalone broadcasts. Course-attached podcast parity (mirror the columns/endpoints on `Course`) is a deliberate follow-up, not part of this plan.
