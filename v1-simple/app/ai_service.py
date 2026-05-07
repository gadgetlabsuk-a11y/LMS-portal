"""AI course generation using the Anthropic Claude API."""

import json
import logging
from typing import Any

import anthropic

from .config import settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an expert instructional designer. Given the full text of a document, create a structured learning course. Return ONLY valid JSON (no markdown fences) with this exact schema:

{
  "title": "Course title",
  "description": "2-3 sentence course description",
  "modules": [
    {
      "title": "Module title",
      "lessons": [
        {
          "title": "Lesson title",
          "summary": "A concise paragraph summarising the lesson content for the trainee to read before watching the video.",
          "video_script": "A detailed, narration-ready video script (2-4 minutes of spoken content). Write it as if a presenter is speaking to camera — conversational, clear, with natural transitions. Include [VISUAL: description] cues where helpful.",
          "quiz": [
            {
              "question": "Question text",
              "options": ["A) ...", "B) ...", "C) ...", "D) ..."],
              "correct": 0
            }
          ]
        }
      ]
    }
  ]
}

Guidelines:
- Create 2-6 modules depending on document length and topic breadth.
- Each module should have 2-5 lessons.
- Each lesson quiz should have 3-5 multiple choice questions.
- "correct" is the zero-based index of the correct option.
- Video scripts should be engaging, educational, and suitable for screen recording with narration.
- Ensure comprehensive coverage of the source document.
- Maintain logical progression from foundational to advanced concepts."""


async def generate_course(document_text: str, filename: str) -> dict[str, Any]:
    """Send document text to Claude and return structured course JSON."""
    if not settings.anthropic_api_key:
        raise ValueError("ANTHROPIC_API_KEY is not set")

    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

    user_prompt = (
        f"Create a structured learning course from the following document "
        f"(source file: {filename}).\n\n"
        f"--- DOCUMENT START ---\n{document_text[:100_000]}\n--- DOCUMENT END ---"
    )

    logger.info("Requesting course generation from Claude", extra={"filename": filename, "text_length": len(document_text)})

    message = await client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=8192,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )

    raw = message.content[0].text.strip()
    # Strip markdown fences if present
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1]
        if raw.endswith("```"):
            raw = raw[:-3]

    course_data = json.loads(raw)
    logger.info("Course generated", extra={"title": course_data.get("title"), "modules": len(course_data.get("modules", []))})
    return course_data
