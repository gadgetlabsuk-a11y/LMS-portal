"""External integration interfaces for ILB — avatar, STT, live TTS.

Each capability is an ABC with a Stub implementation. The demo runs on the stubs (no external
API keys needed); when HeyGen / Deepgram / ElevenLabs-Turbo credentials arrive, real providers
implement the same interface and slot in via the get_*_provider() factories — no call-site
changes (same pattern as audit_service.AnchorProvider).

See docs/superpowers/specs/2026-05-21-ilb-design.md §3.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


# --- Avatar (HeyGen): hybrid pre-render + live --------------------------------------

class AvatarProvider(ABC):
    @abstractmethod
    def prerender(self, script: str, avatar_id: str) -> str:
        """Render the scripted podcast to an avatar video; return a stored video URL."""
        raise NotImplementedError

    @abstractmethod
    def create_live_session(self, avatar_id: str) -> Dict[str, Any]:
        """Open a live interactive-avatar session; return transport details for the client."""
        raise NotImplementedError


class StubAvatarProvider(AvatarProvider):
    """Demo stub. Real impl: HeyGen video-generation API (prerender) + interactive-streaming
    API over LiveKit (live). The same avatar_id must exist in both — the feasibility spike."""

    def prerender(self, script: str, avatar_id: str) -> str:
        return f"avatar-stub://prerendered/{avatar_id}?words={len(script.split())}"

    def create_live_session(self, avatar_id: str) -> Dict[str, Any]:
        return {
            "provider": "stub",
            "avatar_id": avatar_id,
            "livekit_url": "wss://stub.livekit.local",
            "token": "STUB-LIVEKIT-TOKEN",
            "session_id": f"stub-live-{avatar_id}",
        }


# --- Speech-to-text (Deepgram) ------------------------------------------------------

class STTProvider(ABC):
    @abstractmethod
    def transcribe(self, audio: bytes) -> str:
        """Transcribe a chunk/utterance of audio to text."""
        raise NotImplementedError


class StubSTTProvider(STTProvider):
    """Demo stub. Real impl: Deepgram streaming STT over a websocket relay."""

    def transcribe(self, audio: bytes) -> str:
        return "[stub transcript]"


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
    return real or StubAvatarProvider()


def get_stt_provider(real: Optional[STTProvider] = None) -> STTProvider:
    return real or StubSTTProvider()


def get_live_tts_provider(real: Optional[LiveTTSProvider] = None) -> LiveTTSProvider:
    return real or StubLiveTTSProvider()
