"""External integration interfaces for ILB — avatar, STT, live TTS.

Each capability is an ABC with a Stub implementation. The demo runs on the stubs (no external
API keys needed); when HeyGen / Deepgram / ElevenLabs-Turbo credentials arrive, real providers
implement the same interface and slot in via the get_*_provider() factories — no call-site
changes (same pattern as audit_service.AnchorProvider).

See docs/superpowers/specs/2026-05-21-ilb-design.md §3.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

import httpx

from config import settings

DEFAULT_HEYGEN_AVATAR_ID = "Kristin_public_3_20240108"
HEYGEN_API_BASE = "https://api.heygen.com"
HEYGEN_UPLOAD_BASE = "https://upload.heygen.com"


# --- Avatar (HeyGen): hybrid pre-render + live --------------------------------------

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


class StubAvatarProvider(AvatarProvider):
    """Demo stub. Real impl: HeyGen video-generation API (submit_segment/poll) + interactive-streaming
    API over LiveKit (live). The same avatar_id must exist in both — the feasibility spike."""

    async def submit_segment(self, audio: bytes, content_type: str, avatar_id: str) -> str:
        return f"stub-video-{avatar_id}-{len(audio)}"

    async def poll(self, video_id: str) -> tuple[str, Optional[str]]:
        return ("completed", "/api/media/video/stub.mp4")

    def create_live_session(self, avatar_id: str) -> Dict[str, Any]:
        return {
            "provider": "stub",
            "avatar_id": avatar_id,
            "livekit_url": "wss://stub.livekit.local",
            "token": "STUB-LIVEKIT-TOKEN",
            "session_id": f"stub-live-{avatar_id}",
        }


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
            return ("processing", None)
        data = resp.json().get("data") or {}
        status = data.get("status", "processing")
        if status == "completed":
            return ("completed", data.get("video_url"))
        if status == "failed":
            return ("failed", None)
        return ("processing", None)

    def create_live_session(self, avatar_id: str) -> Dict[str, Any]:
        return StubAvatarProvider().create_live_session(avatar_id)


# --- Speech-to-text (Deepgram) ------------------------------------------------------

class STTProvider(ABC):
    @abstractmethod
    async def transcribe(self, audio: bytes, content_type: str = "audio/webm") -> str:
        """Transcribe an utterance of audio to text."""
        raise NotImplementedError


class StubSTTProvider(STTProvider):
    """Demo stub used when no DEEPGRAM_API_KEY is configured."""

    async def transcribe(self, audio: bytes, content_type: str = "audio/webm") -> str:
        return "[stub transcript]"


class DeepgramSTTProvider(STTProvider):
    """Deepgram pre-recorded (push-to-talk) transcription via REST.

    Streaming partials over a websocket are the later upgrade; this transcribes a recorded
    utterance, which is robust for the demo.
    """

    URL = "https://api.deepgram.com/v1/listen"

    def __init__(self, api_key: str) -> None:
        self.api_key = api_key

    async def transcribe(self, audio: bytes, content_type: str = "audio/webm") -> str:
        headers = {"Authorization": f"Token {self.api_key}", "Content-Type": content_type}
        params = {"model": "nova-2", "smart_format": "true", "punctuate": "true"}
        async with httpx.AsyncClient() as client:
            resp = await client.post(self.URL, params=params, headers=headers, content=audio, timeout=30.0)
        if resp.status_code != 200:
            raise Exception(f"Deepgram STT error: {resp.status_code} {resp.text[:200]}")
        data = resp.json()
        try:
            return data["results"]["channels"][0]["alternatives"][0]["transcript"]
        except (KeyError, IndexError):
            return ""


# --- Live text-to-speech (ElevenLabs Turbo) ----------------------------------------

class LiveTTSProvider(ABC):
    @abstractmethod
    def synthesize(self, text: str) -> bytes:
        """Synthesise speech audio for a live answer (low-latency path)."""
        raise NotImplementedError


class StubLiveTTSProvider(LiveTTSProvider):
    """Demo stub. Real impl: ElevenLabs Turbo streaming (distinct from the batch
    narration path in tts_service.py)."""

    def synthesize(self, text: str) -> bytes:
        return b""  # no audio in demo stub


# --- factories (swap stubs for real providers when keys are configured) -------------

def get_avatar_provider(real: Optional[AvatarProvider] = None) -> AvatarProvider:
    if real:
        return real
    if settings.HEYGEN_API_KEY:
        return HeyGenAvatarProvider()
    return StubAvatarProvider()


def get_stt_provider(real: Optional[STTProvider] = None) -> STTProvider:
    if real:
        return real
    if settings.DEEPGRAM_API_KEY:
        return DeepgramSTTProvider(settings.DEEPGRAM_API_KEY)
    return StubSTTProvider()


def get_live_tts_provider(real: Optional[LiveTTSProvider] = None) -> LiveTTSProvider:
    return real or StubLiveTTSProvider()
