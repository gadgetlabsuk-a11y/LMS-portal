import json
import uuid
import logging
import anthropic

logger = logging.getLogger(__name__)

QUIZ_PROMPT_TEMPLATE = """\
You are creating quiz questions for an LMS course.

Lesson title: {lesson_title}
Lesson content (summarised):
{lesson_text}

Generate exactly {n} questions. Mix question types:
- mcq_single: most common
- mcq_multi: where multiple facts must be combined
- tf: where a clear truth/falsehood exists

Difficulty: {difficulty}

Return JSON only — an array of question objects:
[
  {{
    "type": "mcq_single",
    "question": "...",
    "options": [{{"id": "a", "text": "...", "correct": true}}, {{"id": "b", "text": "...", "correct": false}}],
    "feedback": "...",
    "points": 1
  }},
  {{
    "type": "mcq_multi",
    "question": "...",
    "options": [{{"id": "a", "text": "...", "correct": true}}, {{"id": "b", "text": "...", "correct": true}}, {{"id": "c", "text": "...", "correct": false}}],
    "feedback": "...",
    "points": 2
  }},
  {{
    "type": "tf",
    "question": "...",
    "correct_answer": true,
    "feedback": "One sentence explaining why.",
    "points": 1
  }}
]

Constraints:
- mcq_single: exactly one option with correct=true
- mcq_multi: at least one, at most three options with correct=true
- tf: correct_answer must be a boolean (not a string)
- Questions must be answerable from the lesson content only
- No trick questions, no ambiguity
- UK English spelling
- Return ONLY the JSON array, no markdown fences
"""


def _validate_questions(questions: list[dict]) -> list[str]:
    """Returns list of error strings. Empty = valid."""
    errors = []
    for i, q in enumerate(questions):
        t = q.get("type")
        if t == "mcq_single":
            correct_count = sum(1 for o in q.get("options", []) if o.get("correct"))
            if correct_count != 1:
                errors.append(f"Q{i}: mcq_single must have exactly 1 correct option, got {correct_count}")
        elif t == "mcq_multi":
            correct_count = sum(1 for o in q.get("options", []) if o.get("correct"))
            if correct_count < 1:
                errors.append(f"Q{i}: mcq_multi must have at least 1 correct option")
            if correct_count > 3:
                errors.append(f"Q{i}: mcq_multi must have at most 3 correct options")
        elif t == "tf":
            if not isinstance(q.get("correct_answer"), bool):
                errors.append(f"Q{i}: tf correct_answer must be a boolean")
        else:
            errors.append(f"Q{i}: unknown type {t!r}")
    return errors


async def generate_quiz_questions(
    lesson_title: str,
    lesson_text: str,
    n: int = 3,
    difficulty: str = "medium",
    max_retries: int = 2,
) -> list[dict]:
    """Call Claude to generate quiz questions. Retries up to max_retries on invalid output."""
    client = anthropic.AsyncAnthropic()
    prompt = QUIZ_PROMPT_TEMPLATE.format(
        lesson_title=lesson_title,
        lesson_text=lesson_text[:4000],  # cap to avoid huge prompts
        n=n,
        difficulty=difficulty,
    )

    for attempt in range(max_retries + 1):
        msg = await client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=2048,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = msg.content[0].text.strip()
        # Strip markdown fences if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        try:
            questions = json.loads(raw)
        except json.JSONDecodeError as e:
            logger.warning("Quiz gen JSON parse error attempt %d: %s", attempt, e)
            if attempt == max_retries:
                raise ValueError(f"AI returned invalid JSON after {max_retries+1} attempts")
            continue

        errors = _validate_questions(questions)
        if not errors:
            return questions
        logger.warning("Quiz gen validation errors attempt %d: %s", attempt, errors)
        if attempt == max_retries:
            raise ValueError(f"AI quiz questions failed validation: {errors}")

    return []


def questions_to_blocks(questions: list[dict]) -> list[dict]:
    """Convert raw question dicts to slide block format with is_ai_draft metadata."""
    blocks = []
    for i, q in enumerate(questions):
        block_id = f"b_{uuid.uuid4().hex[:8]}"
        block = {
            "id": block_id,
            "type": q["type"],
            "props": {},
            "layout": {"col_start": 2, "col_span": 10, "row_start": i + 1, "row_span": 1},
            "metadata": {"is_ai_draft": True},
        }
        if q["type"] in ("mcq_single", "mcq_multi"):
            block["props"] = {
                "question": q.get("question", ""),
                "options": q.get("options", []),
                "feedback": q.get("feedback", ""),
                "points": q.get("points", 1),
            }
        elif q["type"] == "tf":
            block["props"] = {
                "question": q.get("question", ""),
                "correct_answer": q.get("correct_answer", True),
                "feedback": q.get("feedback", ""),
                "points": q.get("points", 1),
            }
        blocks.append(block)
    return blocks
