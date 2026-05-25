"""
Text-to-speech service using ElevenLabs API — per-slide generation.
Replaces the legacy generate_audio_for_course() Course.content approach.
"""
import asyncio
import hashlib
import logging
from pathlib import Path
from typing import Optional
import httpx
from config import settings

logger = logging.getLogger(__name__)

# Module-level semaphore — shared across all bulk requests (STATE.md pitfall #6)
# Declared here so bulk endpoint in tts.py can import it
_bulk_semaphore = asyncio.Semaphore(3)

AVAILABLE_VOICES = [
    {"voice_id": "21m00Tcm4TlvDq8ikWAM", "name": "Rachel", "description": "Calm, American female"},
    {"voice_id": "TxGEqnHWrfWFTfGW9XjX", "name": "Josh", "description": "Deep, American male"},
]


class TTSService:
    API_URL = "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    DEFAULT_VOICE_ID = "21m00Tcm4TlvDq8ikWAM"  # Rachel

    def __init__(self):
        # Do NOT raise here — key absence is checked lazily in generate_for_slide()
        # This prevents startup crash when ELEVENLABS_API_KEY is not set (research pitfall #3)
        # `api_key` is a property resolved from `settings` at point-of-use, so keys
        # entered via the admin Settings page take effect without a restart.
        self._api_key_override = None

    @property
    def api_key(self) -> str:
        if self._api_key_override is not None:
            return self._api_key_override
        return settings.ELEVENLABS_API_KEY or ""

    @api_key.setter
    def api_key(self, value) -> None:
        # Instance-level override (used by tests / explicit configuration).
        self._api_key_override = value

    @api_key.deleter
    def api_key(self) -> None:
        # Clear the override (e.g. unittest.mock.patch teardown delattrs the attr).
        self._api_key_override = None

    async def generate_for_slide(self, slide, voice_id: str, db) -> str:
        """
        Generate MP3 audio for a slide's narration_script.
        Writes to uploads/audio/slide_{id}.mp3.
        Updates slide.narration_audio_url and slide.narration_script_hash.
        Returns the audio URL path.
        """
        if not self.api_key:
            raise ValueError("TTS not configured")

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

    async def synthesize(self, text: str, voice_id: str) -> bytes:
        """Render arbitrary text to MP3 bytes (used by ILB segment narration)."""
        if not self.api_key:
            raise ValueError("TTS not configured")
        return await self._call_elevenlabs(text, voice_id)

    async def list_voices(self) -> list:
        """Live ElevenLabs voice catalogue (gender/accent/age labels), with a curated fallback."""
        if not self.api_key:
            return AVAILABLE_VOICES
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    "https://api.elevenlabs.io/v1/voices",
                    headers={"xi-api-key": self.api_key},
                    timeout=15.0,
                )
            if resp.status_code != 200:
                return AVAILABLE_VOICES
            voices = resp.json().get("voices", [])
            out = []
            for v in voices:
                labels = v.get("labels", {}) or {}
                desc = ", ".join(
                    str(x) for x in (labels.get("gender"), labels.get("accent"), labels.get("age"))
                    if x
                )
                out.append({
                    "voice_id": v.get("voice_id"),
                    "name": v.get("name"),
                    "description": desc or v.get("category", ""),
                })
            return out or AVAILABLE_VOICES
        except Exception:
            return AVAILABLE_VOICES

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
            raise httpx.HTTPStatusError("rate limit", request=None, response=resp)
        if resp.status_code != 200:
            raise Exception(f"ElevenLabs API error: {resp.status_code} {resp.text[:200]}")
        return resp.content
