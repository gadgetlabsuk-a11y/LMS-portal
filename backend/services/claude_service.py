"""
Claude API integration service for course content generation.
Handles communication with Anthropic Claude API for AI-powered content creation.
"""

import httpx
import json
import logging
from typing import Dict, Any, Optional, AsyncGenerator
from pydantic import BaseModel
from config import settings

logger = logging.getLogger(__name__)

CLAUDE_API_URL = "https://api.anthropic.com/v1/messages"
CLAUDE_MODEL = "claude-sonnet-4-6"


class SlideOutline(BaseModel):
    title: str
    brief: str = ""


class VideoOutline(BaseModel):
    title: str
    description: str = ""
    slides: list[SlideOutline]


class ModuleOutline(BaseModel):
    title: str
    description: str = ""
    videos: list[VideoOutline]


class CourseOutline(BaseModel):
    title: str
    description: str = ""
    modules: list[ModuleOutline]


class GeneratedBlock(BaseModel):
    type: str
    content: dict


class SlideContent(BaseModel):
    blocks: list[GeneratedBlock]
    narration_script: str = ""


def _extract_json_obj(content: str) -> dict:
    """Parse a JSON object from a model response, tolerating code fences/prose."""
    import json as _json
    text = content.strip()
    if "```" in text:
        fenced = text.split("```")
        for chunk in fenced:
            chunk = chunk.strip()
            if chunk.startswith("json"):
                chunk = chunk[4:].strip()
            if chunk.startswith("{"):
                text = chunk
                break
    if not text.lstrip().startswith("{"):
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise ValueError("No JSON object found in model response")
        text = text[start:end + 1]
    try:
        return _json.loads(text)
    except _json.JSONDecodeError as e:
        raise ValueError(f"Malformed JSON in model response: {e}")


class ClaudeService:
    """Service for Claude API interactions."""

    def __init__(self):
        """Initialize Claude service with API key."""
        self.api_key = settings.CLAUDE_API_KEY
        self.model = CLAUDE_MODEL

    async def generate_course(
        self,
        topic: str,
        num_modules: int = 3,
        difficulty: str = "intermediate",
        additional_instructions: Optional[str] = None,
        videos_per_module: int = 1,
        video_duration: str = "medium",
        tone: str = "formal",
        target_audience: str = "general",
        include_assessment: bool = True,
    ) -> Dict[str, Any]:
        """
        Generate course content using Claude API.

        Args:
            topic: Course topic/subject
            num_modules: Number of modules to generate
            difficulty: Difficulty level (beginner, intermediate, advanced)
            additional_instructions: Custom instructions for generation
            videos_per_module: Number of video segments per module
            video_duration: Target video duration (short, medium, long)
            tone: Presentation tone (formal, conversational, technical)
            target_audience: Target audience (new_starters, experienced, management, general)
            include_assessment: Whether to include final quiz assessment

        Returns:
            Dictionary with generated content and metadata

        Raises:
            Exception: If API call fails
        """
        prompt = self._build_course_prompt(
            topic=topic,
            num_modules=num_modules,
            difficulty=difficulty,
            additional_instructions=additional_instructions,
            videos_per_module=videos_per_module,
            video_duration=video_duration,
            tone=tone,
            target_audience=target_audience,
            include_assessment=include_assessment,
        )

        try:
            headers = {
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
                "x-api-key": self.api_key,
            }

            payload = {
                "model": self.model,
                "max_tokens": 8192,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    CLAUDE_API_URL,
                    json=payload,
                    headers=headers,
                    timeout=180.0,
                )

            if response.status_code != 200:
                logger.error(
                    f"Claude API error: {response.status_code} - {response.text}"
                )
                raise Exception(f"Claude API error: {response.status_code}")

            response_data = response.json()

            # Extract content
            content = response_data.get("content", [{}])[0].get("text", "")

            # Parse JSON from response
            course_content = self._parse_course_content(content)

            # Extract token usage
            usage = response_data.get("usage", {})
            tokens_used = usage.get("output_tokens", 0) + usage.get("input_tokens", 0)

            # Estimate cost (pricing varies, this is approximate)
            cost_estimate = (tokens_used / 1000000) * 3.0  # Rough estimate

            logger.info(
                f"Course generated successfully: {topic}, tokens={tokens_used}"
            )

            return {
                "course": course_content,
                "tokens_used": tokens_used,
                "cost_estimate": cost_estimate,
                "model": self.model,
            }

        except httpx.HTTPError as e:
            logger.error(f"HTTP error during course generation: {str(e)}")
            raise Exception(f"Failed to connect to Claude API: {str(e)}")
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Claude response: {str(e)}")
            raise Exception("Failed to parse API response")
        except Exception as e:
            logger.error(f"Unexpected error in course generation: {str(e)}")
            raise

    def _build_course_prompt(
        self,
        topic: str,
        num_modules: int,
        difficulty: str,
        additional_instructions: Optional[str],
        videos_per_module: int = 1,
        video_duration: str = "medium",
        tone: str = "formal",
        target_audience: str = "general",
        include_assessment: bool = True,
    ) -> str:
        """
        Build the prompt for course generation.

        Args:
            topic: Course topic
            num_modules: Number of modules
            difficulty: Difficulty level
            additional_instructions: Custom instructions
            videos_per_module: Number of video segments per module
            video_duration: Target video duration (short, medium, long)
            tone: Presentation tone (formal, conversational, technical)
            target_audience: Target audience (new_starters, experienced, management, general)
            include_assessment: Whether to include final quiz assessment

        Returns:
            Formatted prompt string
        """
        # Map video duration to description
        video_duration_map = {
            "short": "3-5 minutes",
            "medium": "10-15 minutes",
            "long": "20-30 minutes",
        }
        duration_desc = video_duration_map.get(video_duration, "10-15 minutes")

        # Map target audience to description
        audience_map = {
            "new_starters": "New starters / people new to the railway",
            "experienced": "Experienced railway staff",
            "management": "Management / supervisory staff",
            "general": "General audience",
        }
        audience_label = audience_map.get(target_audience, "General audience")

        # Build assessment requirement
        assessment_text = "Include a final quiz assessment" if include_assessment else "No final assessment needed"

        prompt = f"""Generate a training course structure for the following topic. Return ONLY valid JSON — no markdown, no explanation, just the JSON object.

Topic: {topic}
Number of Modules: {num_modules}
Difficulty: {difficulty}

Course Configuration:
- Videos per module: {videos_per_module} (structure content into this many distinct video segments per module)
- Target video duration: {video_duration} ({duration_desc})
- Tone: {tone}
- Target audience: {audience_label}
- Assessment: {assessment_text}

Required JSON structure:
{{
  "title": "Course Title",
  "description": "One sentence description",
  "difficulty": "{difficulty}",
  "objectives": ["objective 1", "objective 2", "objective 3"],
  "duration_hours": 4,
  "modules": [
    {{
      "id": 1,
      "title": "Module Title",
      "description": "One sentence module description",
      "lessons": [
        {{
          "id": 1,
          "title": "Lesson Title",
          "content": "2-3 sentence lesson summary covering key points",
          "learning_outcomes": ["outcome 1", "outcome 2"],
          "estimated_duration_minutes": 20
        }}
      ],
      "quiz": {{
        "questions": [
          {{
            "id": 1,
            "question": "Question text?",
            "options": ["A) ...", "B) ...", "C) ...", "D) ..."],
            "correct_answer": "A",
            "explanation": "Brief explanation"
          }}
        ]
      }}
    }}
  ],
  "assessment": {{
    "type": "quiz",
    "description": "Brief assessment description"
  }},
  "resources": ["Resource 1", "Resource 2"]
}}

Keep lesson content concise (2-3 sentences max per lesson). Include {num_modules} modules with 3-4 lessons each."""

        if additional_instructions:
            prompt += f"\n\nAdditional Instructions:\n{additional_instructions}"

        return prompt

    def _parse_course_content(self, response_text: str) -> Dict[str, Any]:
        """
        Parse course content from Claude response.

        Args:
            response_text: Raw response from Claude

        Returns:
            Parsed course content dictionary

        Raises:
            Exception: If parsing fails
        """
        try:
            # Try to extract JSON from response
            # Claude might wrap JSON in markdown code blocks
            if "```json" in response_text:
                json_start = response_text.find("```json") + 7
                json_end = response_text.find("```", json_start)
                json_str = response_text[json_start:json_end].strip()
            elif "```" in response_text:
                json_start = response_text.find("```") + 3
                json_end = response_text.find("```", json_start)
                json_str = response_text[json_start:json_end].strip()
            else:
                # Try to find JSON object directly
                json_start = response_text.find("{")
                json_end = response_text.rfind("}") + 1
                json_str = response_text[json_start:json_end]

            course_content = json.loads(json_str)
            return course_content

        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"Failed to parse JSON, returning raw content: {str(e)}")
            # Return a structured response with the text content
            return {
                "title": "Generated Course",
                "description": response_text,
                "modules": [
                    {
                        "id": 1,
                        "title": "Content",
                        "lessons": [
                            {
                                "id": 1,
                                "title": "Introduction",
                                "content": response_text,
                            }
                        ],
                    }
                ],
            }

    async def generate_course_from_document(
        self,
        document_text: str,
        filename: str,
        difficulty: str = "intermediate",
        additional_instructions: Optional[str] = None,
        videos_per_module: int = 1,
        video_duration: str = "medium",
        tone: str = "formal",
        target_audience: str = "general",
        include_assessment: bool = True,
    ) -> Dict[str, Any]:
        """
        Generate course content from extracted document text.

        Args:
            document_text: Extracted text from document
            filename: Original filename of the document
            difficulty: Difficulty level (beginner, intermediate, advanced)
            additional_instructions: Custom instructions for generation
            videos_per_module: Number of video segments per module
            video_duration: Target video duration (short, medium, long)
            tone: Presentation tone (formal, conversational, technical)
            target_audience: Target audience (new_starters, experienced, management, general)
            include_assessment: Whether to include final quiz assessment

        Returns:
            Dictionary with generated content and metadata

        Raises:
            Exception: If API call fails
        """
        prompt = self._build_document_course_prompt(
            document_text=document_text,
            filename=filename,
            difficulty=difficulty,
            additional_instructions=additional_instructions,
            videos_per_module=videos_per_module,
            video_duration=video_duration,
            tone=tone,
            target_audience=target_audience,
            include_assessment=include_assessment,
        )

        try:
            headers = {
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
                "x-api-key": self.api_key,
            }

            payload = {
                "model": self.model,
                "max_tokens": 8192,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    CLAUDE_API_URL,
                    json=payload,
                    headers=headers,
                    timeout=180.0,
                )

            if response.status_code != 200:
                logger.error(
                    f"Claude API error: {response.status_code} - {response.text}"
                )
                raise Exception(f"Claude API error: {response.status_code}")

            response_data = response.json()

            # Extract content
            content = response_data.get("content", [{}])[0].get("text", "")

            # Parse JSON from response
            course_content = self._parse_course_content(content)

            # Extract token usage
            usage = response_data.get("usage", {})
            tokens_used = usage.get("output_tokens", 0) + usage.get("input_tokens", 0)

            # Estimate cost (pricing varies, this is approximate)
            cost_estimate = (tokens_used / 1000000) * 3.0  # Rough estimate

            logger.info(
                f"Course generated from document: {filename}, tokens={tokens_used}"
            )

            return {
                "course": course_content,
                "tokens_used": tokens_used,
                "cost_estimate": cost_estimate,
                "model": self.model,
            }

        except httpx.HTTPError as e:
            logger.error(f"HTTP error during course generation: {str(e)}")
            raise Exception(f"Failed to connect to Claude API: {str(e)}")
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Claude response: {str(e)}")
            raise Exception("Failed to parse API response")
        except Exception as e:
            logger.error(f"Unexpected error in course generation: {str(e)}")
            raise

    def _build_document_course_prompt(
        self,
        document_text: str,
        filename: str,
        difficulty: str,
        additional_instructions: Optional[str],
        videos_per_module: int = 1,
        video_duration: str = "medium",
        tone: str = "formal",
        target_audience: str = "general",
        include_assessment: bool = True,
    ) -> str:
        """
        Build the prompt for course generation from document.

        Args:
            document_text: Extracted document text
            filename: Original filename
            difficulty: Difficulty level
            additional_instructions: Custom instructions
            videos_per_module: Number of video segments per module
            video_duration: Target video duration (short, medium, long)
            tone: Presentation tone (formal, conversational, technical)
            target_audience: Target audience (new_starters, experienced, management, general)
            include_assessment: Whether to include final quiz assessment

        Returns:
            Formatted prompt string
        """
        # Map video duration to description
        video_duration_map = {
            "short": "3-5 minutes",
            "medium": "10-15 minutes",
            "long": "20-30 minutes",
        }
        duration_desc = video_duration_map.get(video_duration, "10-15 minutes")

        # Map target audience to description
        audience_map = {
            "new_starters": "New starters / people new to the railway",
            "experienced": "Experienced railway staff",
            "management": "Management / supervisory staff",
            "general": "General audience",
        }
        audience_label = audience_map.get(target_audience, "General audience")

        # Build assessment requirement
        assessment_text = "Include a final quiz assessment" if include_assessment else "No final assessment needed"

        prompt = f"""Here is the content of a document called '{filename}'. Convert this into a structured training course suitable for {difficulty}-level learners.

Course Configuration:
- Videos per module: {videos_per_module} (structure content into this many distinct video segments per module)
- Target video duration: {video_duration} ({duration_desc})
- Tone: {tone}
- Target audience: {audience_label}
- Assessment: {assessment_text}

Document Content:
---
{document_text}
---

Based on this document, generate a comprehensive course structure as a JSON object with the following format:
{{
  "title": "Course Title (derived from document)",
  "description": "Course description based on document content",
  "difficulty": "{difficulty}",
  "objectives": ["objective 1", "objective 2", ...],
  "duration_hours": estimated_duration,
  "modules": [
    {{
      "id": 1,
      "title": "Module Title",
      "description": "Module description",
      "lessons": [
        {{
          "id": 1,
          "title": "Lesson Title",
          "content": "Detailed lesson content extracted/derived from the document",
          "learning_outcomes": ["outcome 1", "outcome 2"],
          "estimated_duration_minutes": 30
        }}
      ],
      "quiz": {{
        "questions": [
          {{
            "id": 1,
            "question": "Question text based on document content",
            "options": ["A", "B", "C", "D"],
            "correct_answer": "A",
            "explanation": "Explanation of the answer"
          }}
        ]
      }}
    }}
  ],
  "assessment": {{
    "type": "quiz or project",
    "description": "Final assessment based on document content"
  }},
  "resources": ["resource 1", "resource 2"]
}}

Create a course that:
- Organizes the document content into logical modules and lessons
- Maintains accuracy and fidelity to the original document
- Includes practical examples from the document
- Creates assessment questions based on key document concepts
- Is appropriate for the {difficulty} difficulty level"""

        if additional_instructions:
            prompt += f"\n\nAdditional Instructions:\n{additional_instructions}"

        return prompt

    async def stream_course_description(
        self, topic: str, tone_preset: Optional[str] = "professional"
    ) -> AsyncGenerator[str, None]:
        """Stream a course description for the given topic and tone."""
        tone_instruction = f"Use a {tone_preset} tone." if tone_preset else ""
        prompt = (
            f"Write a compelling course description (2-3 sentences) for a course about: {topic}. "
            f"{tone_instruction} Be concise and focus on what learners will gain."
        )
        async for token in self._stream_text(prompt):
            yield token

    async def stream_learning_objectives(
        self,
        course_title: str,
        description: Optional[str] = None,
        tone_preset: Optional[str] = "professional",
    ) -> AsyncGenerator[str, None]:
        """Stream learning objectives (one per line) for a course."""
        tone_instruction = f"Use a {tone_preset} tone." if tone_preset else ""
        context = f"\nCourse description: {description}" if description else ""
        prompt = (
            f"Generate 5 clear, measurable learning objectives for a course titled: {course_title}.{context} "
            f"{tone_instruction} Output each objective on its own line starting with a dash (- )."
        )
        async for token in self._stream_text(prompt):
            yield token

    async def _stream_text(self, prompt: str) -> AsyncGenerator[str, None]:
        """Core streaming method: calls Anthropic API with stream=True and yields text deltas."""
        import json as _json

        headers = {
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
            "x-api-key": self.api_key,
        }
        payload = {
            "model": self.model,
            "max_tokens": 1024,
            "stream": True,
            "messages": [{"role": "user", "content": prompt}],
        }
        async with httpx.AsyncClient() as client:
            async with client.stream(
                "POST",
                "https://api.anthropic.com/v1/messages",
                json=payload,
                headers=headers,
                timeout=60.0,
            ) as response:
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        try:
                            data = _json.loads(line[6:])
                            if data.get("type") == "content_block_delta":
                                token = data.get("delta", {}).get("text", "")
                                if token:
                                    yield token
                        except _json.JSONDecodeError:
                            continue

    async def _complete(self, prompt: str, max_tokens: int = 8192) -> str:
        """Non-streaming completion: returns the model's text content."""
        headers = {
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
            "x-api-key": self.api_key,
        }
        payload = {
            "model": self.model,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(
                CLAUDE_API_URL, json=payload, headers=headers, timeout=180.0,
            )
        if response.status_code != 200:
            logger.error(f"Claude API error: {response.status_code} - {response.text}")
            raise Exception(f"Claude API error: {response.status_code}")
        data = response.json()
        return data.get("content", [{}])[0].get("text", "")

    async def generate_podcast_script(
        self,
        source_text: str,
        host_persona: str = "a warm, clear, professional training host",
        target_minutes: int = 10,
        title: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Generate a continuous, podcast-style narration script grounded in the source.

        Unlike per-slide narration, this produces one flowing script paced for listening
        retention, in a consistent host persona. Used for ILB video_type='podcast'.
        Stays faithful to the source material — no invented facts.
        """
        title_line = f"Course title: {title}\n" if title else ""
        # ~140 spoken words/minute is a reasonable retention pace.
        target_words = target_minutes * 140
        prompt = f"""You are {host_persona}. Write a spoken-word podcast narration script that\
 teaches the material in the SOURCE below. Pace it for listening (around {target_words} words,\
 ~{target_minutes} minutes). Be faithful to the source — do NOT invent facts beyond it.

Guidelines:
- Conversational and clear, as if speaking directly to one learner.
- Open with a short hook, then teach in logical segments, then a brief recap.
- Mark natural segment breaks with a line "[SEGMENT BREAK]" so the player can insert
  knowledge checks.
- Output ONLY the narration script text (no headings, no stage directions other than the
  [SEGMENT BREAK] markers).

{title_line}SOURCE:
---
{source_text}
---"""

        headers = {
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
            "x-api-key": self.api_key,
        }
        payload = {
            "model": self.model,
            "max_tokens": 8192,
            "messages": [{"role": "user", "content": prompt}],
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(
                CLAUDE_API_URL, json=payload, headers=headers, timeout=180.0
            )
        if response.status_code != 200:
            logger.error("Claude API error (podcast script): %s - %s", response.status_code, response.text)
            raise Exception(f"Claude API error: {response.status_code}")

        data = response.json()
        script_text = data.get("content", [{}])[0].get("text", "")
        usage = data.get("usage", {})
        tokens_used = usage.get("output_tokens", 0) + usage.get("input_tokens", 0)
        segments = [s.strip() for s in script_text.split("[SEGMENT BREAK]") if s.strip()]
        return {
            "script": script_text,
            "segments": segments,
            "tokens_used": tokens_used,
            "model": self.model,
        }

    async def validate_api_key(self) -> bool:
        """
        Validate Claude API key by making a test request.

        Returns:
            True if key is valid, False otherwise
        """
        try:
            headers = {
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
                "x-api-key": self.api_key,
            }

            payload = {
                "model": self.model,
                "max_tokens": 100,
                "messages": [
                    {
                        "role": "user",
                        "content": "Say 'API key is valid' if you can read this.",
                    }
                ],
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    CLAUDE_API_URL,
                    json=payload,
                    headers=headers,
                    timeout=10.0,
                )

            return response.status_code == 200

        except Exception as e:
            logger.error(f"API key validation failed: {str(e)}")
            return False
