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
    _real = httpx.AsyncClient
    with patch("services.integrations.httpx.AsyncClient",
               lambda *a, **k: _real(transport=transport)):
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
    _real = httpx.AsyncClient
    with patch("services.integrations.httpx.AsyncClient",
               lambda *a, **k: _real(transport=transport)):
        status, url = await prov.poll("vid_7")
    assert status == "completed"
    assert url == "https://h/v.mp4?Expires=1"


def test_factory_picks_heygen_when_key_set():
    with patch("services.integrations.settings") as s:
        s.HEYGEN_API_KEY = "k"
        assert isinstance(get_avatar_provider(), HeyGenAvatarProvider)
        s.HEYGEN_API_KEY = ""
        assert isinstance(get_avatar_provider(), StubAvatarProvider)


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
    import os
    os.makedirs("uploads/audio", exist_ok=True)
    for i in range(2):
        open(f"uploads/audio/ilb_bcast_{bid}_seg_{i}.mp3", "wb").write(b"ID3test")
    r = client.post(f"/api/ilb/broadcasts/{bid}/render-avatar", headers=h)
    assert r.status_code == 200
    jobs = r.json()["jobs"]
    assert [j["heygen_video_id"] for j in jobs] == ["v0", "v1"]
    assert all(j["status"] == "processing" for j in jobs)


def test_avatar_status_completes_and_downloads(creator_token, db, monkeypatch):
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


def test_get_broadcast_serializes_partial_segment_video(creator_token, db):
    """A partially-rendered broadcast (segment_video has a None) must serialize, not 500."""
    bid, h = _make_broadcast(creator_token, db)
    from models import Broadcast
    b = db.query(Broadcast).get(bid)
    b.segment_video = [None, f"/api/media/video/ilb_bcast_{bid}_seg_1.mp4"]
    db.commit()
    r = client.get(f"/api/ilb/broadcasts/{bid}", headers=h)
    assert r.status_code == 200
    assert r.json()["segment_video"] == [None, f"/api/media/video/ilb_bcast_{bid}_seg_1.mp4"]


def test_update_broadcast_preserves_media_when_script_unchanged(creator_token, db):
    """A title/voice edit (script unchanged) must NOT wipe rendered audio/avatar."""
    bid, h = _make_broadcast(creator_token, db)  # script="Seg one.[SEGMENT BREAK]Seg two.", segment_audio set
    from models import Broadcast
    b = db.query(Broadcast).get(bid)
    b.segment_video = [f"/api/media/video/ilb_bcast_{bid}_seg_0.mp4", f"/api/media/video/ilb_bcast_{bid}_seg_1.mp4"]
    db.commit()
    r = client.put(
        f"/api/ilb/broadcasts/{bid}",
        json={"title": "Renamed", "script": "Seg one.[SEGMENT BREAK]Seg two."},  # same script
        headers=h,
    )
    assert r.status_code == 200
    db.refresh(b)
    assert b.title == "Renamed"
    assert b.segment_audio is not None      # preserved
    assert b.segment_video is not None       # preserved


def test_update_broadcast_clears_media_when_script_changes(creator_token, db):
    """Editing the script invalidates the (now-stale) rendered audio + avatar."""
    bid, h = _make_broadcast(creator_token, db)
    from models import Broadcast
    b = db.query(Broadcast).get(bid)
    b.segment_video = [f"/api/media/video/ilb_bcast_{bid}_seg_0.mp4", f"/api/media/video/ilb_bcast_{bid}_seg_1.mp4"]
    db.commit()
    r = client.put(
        f"/api/ilb/broadcasts/{bid}",
        json={"script": "A brand new opening.[SEGMENT BREAK]A different second part."},
        headers=h,
    )
    assert r.status_code == 200
    db.refresh(b)
    assert b.segment_audio is None
    assert b.segment_video is None
