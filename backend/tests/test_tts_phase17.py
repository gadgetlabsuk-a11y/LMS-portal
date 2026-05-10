import asyncio
import hashlib
import pytest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
from main import app
from routers.tts import tts_service as tts_service_module
from models import Slide

client = TestClient(app)


# ---------------------------------------------------------------------------
# Creator-slide fixture chain
# ---------------------------------------------------------------------------
@pytest.fixture
def creator_slide(creator_token, creator_course, db):
    """
    Build: module → video → slide via API calls.
    Mirrors the creator_slide fixture pattern from test_slides_phase14.py.
    Sets narration_script on the slide so TTS endpoint does not return 400.
    """
    headers = {"Authorization": f"Bearer {creator_token}"}

    # Create module
    mod_res = client.post(
        f"/api/courses/{creator_course.id}/modules",
        json={"title": "TTS Module", "order_index": 1},
        headers=headers,
    )
    assert mod_res.status_code == 201, f"module create failed: {mod_res.text}"
    module_id = mod_res.json()["id"]

    # Create video
    vid_res = client.post(
        f"/api/modules/{module_id}/videos",
        json={"title": "TTS Video", "order_index": 1, "video_type": "slideshow_narrated"},
        headers=headers,
    )
    assert vid_res.status_code == 201, f"video create failed: {vid_res.text}"
    video_id = vid_res.json()["id"]

    # Create slide
    slide_res = client.post(
        f"/api/videos/{video_id}/slides",
        json={"title": "TTS Slide", "order_index": 1},
        headers=headers,
    )
    assert slide_res.status_code == 201, f"slide create failed: {slide_res.text}"
    slide_id = slide_res.json()["id"]

    # Set narration_script via PUT so endpoint doesn't return 400
    put_res = client.put(
        f"/api/slides/{slide_id}",
        json={"narration_script": "Hello world. This is a test narration."},
        headers=headers,
    )
    assert put_res.status_code in (200, 201), f"slide PUT failed: {put_res.text}"
    return put_res.json()


# ---------------------------------------------------------------------------
# TTS-01: Per-slide audio generation endpoint
# ---------------------------------------------------------------------------
def test_generate_slide_audio(creator_token, creator_slide):
    """
    POST /api/slides/{slide_id}/tts/generate
    Should return {"audio_url": ..., "slide_id": ...} and update Slide.narration_audio_url.
    """
    with patch("routers.tts.tts_service.api_key", "fake-api-key"), \
         patch("routers.tts.tts_service._call_elevenlabs", new_callable=AsyncMock) as mock_el:
        mock_el.return_value = b"fake_mp3_bytes"
        res = client.post(
            f"/api/slides/{creator_slide['id']}/tts/generate",
            json={},
            headers={"Authorization": f"Bearer {creator_token}"},
        )

    assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
    data = res.json()
    assert "audio_url" in data
    assert "slide_id" in data
    assert data["audio_url"].endswith(".mp3")
    assert data["slide_id"] == creator_slide["id"]


# ---------------------------------------------------------------------------
# TTS-05: Voice ID is passed through to the ElevenLabs API call
# ---------------------------------------------------------------------------
def test_voice_id_passed_to_elevenlabs(creator_token, creator_slide):
    """
    When a voice_id is provided in the request body, the TTSService must
    pass that exact voice_id to _call_elevenlabs as the second positional arg.
    """
    josh_voice_id = "TxGEqnHWrfWFTfGW9XjX"

    with patch("routers.tts.tts_service.api_key", "fake-api-key"), \
         patch("routers.tts.tts_service._call_elevenlabs", new_callable=AsyncMock) as mock_el:
        mock_el.return_value = b"fake_mp3_bytes"
        client.post(
            f"/api/slides/{creator_slide['id']}/tts/generate",
            json={"voice_id": josh_voice_id},
            headers={"Authorization": f"Bearer {creator_token}"},
        )

    mock_el.assert_called_once()
    call_args = mock_el.call_args
    # _call_elevenlabs(text, voice_id) — second positional arg is voice_id
    assert call_args[0][1] == josh_voice_id


# ---------------------------------------------------------------------------
# TTS-01 error cases
# ---------------------------------------------------------------------------
def test_generate_slide_audio_no_script(creator_token, creator_course, db):
    """
    POST /api/slides/{id}/tts/generate returns 400 when slide has no narration_script.
    """
    headers = {"Authorization": f"Bearer {creator_token}"}

    # Build chain without setting narration_script
    mod_res = client.post(
        f"/api/courses/{creator_course.id}/modules",
        json={"title": "No Script Module", "order_index": 2},
        headers=headers,
    )
    assert mod_res.status_code == 201
    module_id = mod_res.json()["id"]

    vid_res = client.post(
        f"/api/modules/{module_id}/videos",
        json={"title": "No Script Video", "order_index": 1, "video_type": "slideshow_narrated"},
        headers=headers,
    )
    assert vid_res.status_code == 201
    video_id = vid_res.json()["id"]

    slide_res = client.post(
        f"/api/videos/{video_id}/slides",
        json={"title": "No Script Slide", "order_index": 1},
        headers=headers,
    )
    assert slide_res.status_code == 201
    slide_id = slide_res.json()["id"]

    with patch("routers.tts.tts_service.api_key", "fake-api-key"):
        res = client.post(
            f"/api/slides/{slide_id}/tts/generate",
            json={},
            headers=headers,
        )

    assert res.status_code == 400
    assert "narration script" in res.json()["detail"].lower()


def test_generate_slide_audio_no_key(creator_token, creator_slide):
    """
    POST /api/slides/{id}/tts/generate returns 503 when ELEVENLABS_API_KEY is empty.
    """
    with patch.object(tts_service_module, "api_key", ""):
        res = client.post(
            f"/api/slides/{creator_slide['id']}/tts/generate",
            json={},
            headers={"Authorization": f"Bearer {creator_token}"},
        )

    assert res.status_code == 503
    assert "TTS not configured" in res.json()["detail"]


# ---------------------------------------------------------------------------
# Shared helper fixture: module + video (no slides) for bulk tests
# ---------------------------------------------------------------------------
@pytest.fixture
def creator_video(creator_token, creator_course):
    """Build: module → video, return video_id for bulk TTS tests."""
    headers = {"Authorization": f"Bearer {creator_token}"}

    mod_res = client.post(
        f"/api/courses/{creator_course.id}/modules",
        json={"title": "Bulk TTS Module", "order_index": 10},
        headers=headers,
    )
    assert mod_res.status_code == 201, f"module create failed: {mod_res.text}"
    module_id = mod_res.json()["id"]

    vid_res = client.post(
        f"/api/modules/{module_id}/videos",
        json={"title": "Bulk TTS Video", "order_index": 1, "video_type": "slideshow_narrated"},
        headers=headers,
    )
    assert vid_res.status_code == 201, f"video create failed: {vid_res.text}"
    return vid_res.json()["id"]


# ---------------------------------------------------------------------------
# TTS-02: Bulk audio generation endpoint
# ---------------------------------------------------------------------------
def test_bulk_generate(creator_token, creator_video):
    """
    POST /api/videos/{video_id}/tts/bulk-generate
    Should process all slides with narration scripts and return counts:
    {generated, skipped_no_script, skipped_cached, errors}.
    """
    headers = {"Authorization": f"Bearer {creator_token}"}
    video_id = creator_video

    # Create 2 slides with narration scripts
    for i in range(2):
        slide_res = client.post(
            f"/api/videos/{video_id}/slides",
            json={"title": f"Bulk Slide {i}", "order_index": i + 1},
            headers=headers,
        )
        assert slide_res.status_code == 201
        slide_id = slide_res.json()["id"]
        put_res = client.put(
            f"/api/slides/{slide_id}",
            json={"narration_script": f"Slide {i} narration text."},
            headers=headers,
        )
        assert put_res.status_code in (200, 201)

    with patch("routers.tts.tts_service.api_key", "fake-api-key"), \
         patch("routers.tts.tts_service._call_elevenlabs", new_callable=AsyncMock) as mock_el:
        mock_el.return_value = b"fake_mp3"
        res = client.post(
            f"/api/videos/{video_id}/tts/bulk-generate",
            json={},
            headers=headers,
        )

    assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
    data = res.json()
    assert data["generated"] == 2
    assert data["skipped_no_script"] == 0
    assert data["skipped_cached"] == 0
    assert data["errors"] == 0


# ---------------------------------------------------------------------------
# TTS-03: Semaphore limits concurrent ElevenLabs calls
# ---------------------------------------------------------------------------
def test_semaphore_limits_concurrency():
    """
    asyncio.Semaphore(3) declared at module level in tts_service.py must limit
    concurrent ElevenLabs calls to 3 during bulk generation.
    Verify _bulk_semaphore is an asyncio.Semaphore instance at module level.
    """
    from services.tts_service import _bulk_semaphore
    assert isinstance(_bulk_semaphore, asyncio.Semaphore)

    # Verify it is NOT re-created inside tts.py (should be imported, not defined)
    import routers.tts as tts_router
    import inspect, ast, textwrap
    src = inspect.getsource(tts_router)
    # Should contain import of _bulk_semaphore (from services.tts_service)
    assert "_bulk_semaphore" in src
    # Should NOT contain asyncio.Semaphore( in the module body outside of imports
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            # Check that no module-level assignment creates a new Semaphore
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "_bulk_semaphore":
                    pytest.fail("_bulk_semaphore must not be re-created inside tts.py")


# ---------------------------------------------------------------------------
# TTS-04: Bulk generation skips slides with cached (unchanged) scripts
# ---------------------------------------------------------------------------
def test_bulk_skips_cached_slides(creator_token, creator_video, db):
    """
    Slide with narration_script_hash matching sha256(narration_script) and
    a non-null narration_audio_url must be skipped (skipped_cached += 1).
    ElevenLabs must NOT be called for that slide.
    """
    headers = {"Authorization": f"Bearer {creator_token}"}
    video_id = creator_video
    script = "Hello world. This is a cached narration."

    # Create one slide with narration script
    slide_res = client.post(
        f"/api/videos/{video_id}/slides",
        json={"title": "Cached Slide", "order_index": 1},
        headers=headers,
    )
    assert slide_res.status_code == 201
    slide_id = slide_res.json()["id"]

    put_res = client.put(
        f"/api/slides/{slide_id}",
        json={"narration_script": script},
        headers=headers,
    )
    assert put_res.status_code in (200, 201)

    # Manually set narration_script_hash + narration_audio_url to simulate a cached state
    slide_obj = db.query(Slide).filter(Slide.id == slide_id).first()
    slide_obj.narration_script_hash = hashlib.sha256(script.encode()).hexdigest()
    slide_obj.narration_audio_url = f"/uploads/audio/slide_{slide_id}.mp3"
    db.commit()

    with patch("routers.tts.tts_service.api_key", "fake-api-key"), \
         patch("routers.tts.tts_service._call_elevenlabs", new_callable=AsyncMock) as mock_el:
        mock_el.return_value = b"fake_mp3"
        res = client.post(
            f"/api/videos/{video_id}/tts/bulk-generate",
            json={},
            headers=headers,
        )

    assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
    data = res.json()
    assert data["skipped_cached"] == 1
    assert data["generated"] == 0
    mock_el.assert_not_called()
