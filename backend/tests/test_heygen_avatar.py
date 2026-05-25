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
