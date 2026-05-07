"""
Text-to-speech service using ElevenLabs API.
Generates audio files for course lessons.
"""

import httpx
import logging
from pathlib import Path
from typing import Dict, Any
from config import settings

logger = logging.getLogger(__name__)


class TTSService:
    """Service for ElevenLabs text-to-speech API integration."""

    API_URL = "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    DEFAULT_VOICE_ID = "21m00Tcm4TlvDq8ikWAM"  # Rachel

    def __init__(self):
        """Initialize TTS service with API key."""
        self.api_key = settings.ELEVENLABS_API_KEY
        if not self.api_key:
            raise ValueError("ELEVENLABS_API_KEY not configured")

    async def generate_audio_for_course(
        self, course_content: Dict[str, Any], course_id: int
    ) -> Dict[str, str]:
        """
        Generate MP3 audio for each lesson in the course.

        Args:
            course_content: The course content dict (stored in Course.content)
            course_id: The course ID for organizing audio files

        Returns:
            Dictionary mapping lesson keys to audio URLs
            e.g. {"1_1": "/uploads/audio/course_1/lesson_1_1.mp3"}

        Raises:
            ValueError: If API key is not configured
            Exception: If API call or file operations fail
        """
        if not self.api_key:
            raise ValueError("ELEVENLABS_API_KEY not configured")

        audio_urls = {}
        modules = course_content.get("modules", [])

        # Create audio directory
        audio_dir = Path(settings.UPLOAD_DIR) / "audio" / f"course_{course_id}"
        audio_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Generating audio for course {course_id} with {len(modules)} modules")

        for module in modules:
            module_id = module.get("id", 0)
            lessons = module.get("lessons", [])

            for lesson in lessons:
                lesson_id = lesson.get("id", 0)
                lesson_key = f"{module_id}_{lesson_id}"

                try:
                    # Extract text for TTS
                    text = self._extract_lesson_text(lesson)

                    # Limit to max 2500 characters
                    text = text[:2500]

                    if not text.strip():
                        logger.warning(
                            f"Skipping audio generation for lesson {lesson_key}: empty content"
                        )
                        continue

                    # Generate audio
                    audio_bytes = await self._call_elevenlabs(text)

                    # Save audio file
                    filename = f"lesson_{lesson_key}.mp3"
                    filepath = audio_dir / filename
                    filepath.write_bytes(audio_bytes)

                    # Store relative URL for retrieval
                    relative_url = f"/uploads/audio/course_{course_id}/{filename}"
                    audio_urls[lesson_key] = relative_url

                    logger.info(f"Generated audio for lesson {lesson_key}")

                except Exception as e:
                    logger.error(f"Failed to generate audio for lesson {lesson_key}: {str(e)}")
                    # Continue with other lessons rather than failing entirely
                    raise

        logger.info(f"Audio generation complete for course {course_id}: {len(audio_urls)} files")
        return audio_urls

    async def _call_elevenlabs(self, text: str) -> bytes:
        """
        Call ElevenLabs API to generate audio.

        Args:
            text: Text to convert to speech

        Returns:
            MP3 audio bytes

        Raises:
            Exception: If API call fails
        """
        url = self.API_URL.format(voice_id=self.DEFAULT_VOICE_ID)

        headers = {
            "xi-api-key": self.api_key,
            "Content-Type": "application/json",
            "Accept": "audio/mpeg",
        }

        body = {
            "text": text,
            "model_id": "eleven_monolingual_v1",
            "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    json=body,
                    headers=headers,
                    timeout=30.0,
                )

            if response.status_code != 200:
                logger.error(
                    f"ElevenLabs API error: {response.status_code} - {response.text}"
                )
                raise Exception(f"ElevenLabs API error: {response.status_code}")

            return response.content

        except httpx.HTTPError as e:
            logger.error(f"HTTP error calling ElevenLabs API: {str(e)}")
            raise Exception(f"Failed to connect to ElevenLabs API: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error calling ElevenLabs API: {str(e)}")
            raise

    def _extract_lesson_text(self, lesson: Dict[str, Any]) -> str:
        """
        Extract text content from a lesson for TTS.

        Args:
            lesson: Lesson content dict

        Returns:
            Text to convert to speech
        """
        # Prefer learning_outcomes, fall back to content
        outcomes = lesson.get("learning_outcomes", [])
        if outcomes:
            return " ".join(str(o) for o in outcomes)

        content = lesson.get("content", "")
        return str(content)
