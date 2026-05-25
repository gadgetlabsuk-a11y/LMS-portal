"""ILB Q&A engine — answers learner questions grounded in course source.

Design (see docs/superpowers/specs/2026-05-21-ilb-design.md §6):
- Grounded in the course source via long-context (source passed in-prompt; NO vector store).
- Mandatory citation of the source passage used.
- Refuse + escalate to a human when the source doesn't cover the question.
- Always carries a disclaimer.
- Q&A is a learning aid, NOT the assessment — comprehension is proven by the quiz, so an
  escalated/declined answer never blocks a learner.

The Claude call is isolated in `_call_claude`; `_parse` and `_apply_guardrails` are pure so the
cite / refuse / escalate behaviour is unit-testable without an API key.
"""

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import httpx

from config import settings

logger = logging.getLogger(__name__)

CLAUDE_API_URL = "https://api.anthropic.com/v1/messages"
CLAUDE_MODEL = "claude-sonnet-4-6"

# Below this model-reported confidence we escalate rather than answer.
CONFIDENCE_THRESHOLD = 0.6

DISCLAIMER = (
    "This is a learning aid — always refer to the official course material for "
    "authoritative guidance."
)
ESCALATION_MESSAGE = (
    "I can't answer that confidently from this course's material, so I've flagged it for a "
    "human to follow up. This won't affect your progress — your understanding is assessed by "
    "the knowledge checks, not by this question."
)


@dataclass
class QAResult:
    """Structured outcome of a grounded Q&A exchange."""
    answer: str
    source_refs: List[str] = field(default_factory=list)
    confidence: float = 0.0
    covered: bool = False
    escalated: bool = False
    disclaimer: str = DISCLAIMER

    def to_dict(self) -> Dict[str, Any]:
        return {
            "answer": self.answer,
            "source_refs": self.source_refs,
            "confidence": self.confidence,
            "covered": self.covered,
            "escalated": self.escalated,
            "disclaimer": self.disclaimer,
        }


class QAService:
    """Grounded, guard-railed question answering for the ILB player."""

    def __init__(self) -> None:
        # `api_key` resolves from `settings` at point-of-use so admin Settings-page
        # updates apply without a restart (see integration_settings_service).
        self._api_key_override = None
        self.model = CLAUDE_MODEL

    @property
    def api_key(self) -> str:
        if self._api_key_override is not None:
            return self._api_key_override
        return settings.CLAUDE_API_KEY

    @api_key.setter
    def api_key(self, value) -> None:
        self._api_key_override = value

    @api_key.deleter
    def api_key(self) -> None:
        self._api_key_override = None

    async def answer(
        self,
        question: str,
        source_text: str,
        history: Optional[List[Dict[str, str]]] = None,
        threshold: float = CONFIDENCE_THRESHOLD,
    ) -> QAResult:
        """Answer a learner question strictly from `source_text`."""
        prompt = self._build_prompt(question, source_text, history)
        raw = await self._call_claude(prompt)
        parsed = self._parse(raw)
        return self._apply_guardrails(parsed, threshold)

    # --- pure helpers (unit-testable, no network) ---------------------------------

    def _build_prompt(
        self,
        question: str,
        source_text: str,
        history: Optional[List[Dict[str, str]]] = None,
    ) -> str:
        history_block = ""
        if history:
            turns = "\n".join(
                f"{t.get('role', 'user').upper()}: {t.get('content', '')}" for t in history
            )
            history_block = f"\nConversation so far:\n{turns}\n"

        return f"""You are a training host answering a learner's question. You may ONLY use the\
 COURSE SOURCE below. Do not use outside knowledge. If the source does not contain the answer,\
 say so honestly — do NOT guess.

Return ONLY a valid JSON object, no markdown, in exactly this shape:
{{
  "answer": "your answer in plain language, or empty string if not covered",
  "citations": ["short verbatim quote(s) from the source that support the answer"],
  "covered": true or false,        // is the question actually answerable from the source?
  "confidence": 0.0 to 1.0          // your confidence the answer is correct AND grounded
}}

COURSE SOURCE:
---
{source_text}
---
{history_block}
LEARNER QUESTION: {question}"""

    def _parse(self, raw_text: str) -> Dict[str, Any]:
        """Extract the JSON object from a (possibly markdown-wrapped) Claude response."""
        try:
            if "```json" in raw_text:
                start = raw_text.find("```json") + 7
                end = raw_text.find("```", start)
                snippet = raw_text[start:end].strip()
            elif "```" in raw_text:
                start = raw_text.find("```") + 3
                end = raw_text.find("```", start)
                snippet = raw_text[start:end].strip()
            else:
                start = raw_text.find("{")
                end = raw_text.rfind("}") + 1
                snippet = raw_text[start:end]
            data = json.loads(snippet)
        except (json.JSONDecodeError, ValueError):
            logger.warning("Q&A: could not parse model JSON; treating as not covered")
            return {"answer": "", "citations": [], "covered": False, "confidence": 0.0}

        return {
            "answer": str(data.get("answer", "") or ""),
            "citations": list(data.get("citations", []) or []),
            "covered": bool(data.get("covered", False)),
            "confidence": _clamp01(data.get("confidence", 0.0)),
        }

    def _apply_guardrails(self, parsed: Dict[str, Any], threshold: float) -> QAResult:
        """Escalate when the source doesn't cover the question or confidence is too low."""
        covered = parsed["covered"]
        confidence = parsed["confidence"]
        citations = parsed["citations"]

        # No grounding citation => can't trust it, regardless of self-reported confidence.
        has_citation = len(citations) > 0

        if (not covered) or (confidence < threshold) or (not has_citation):
            return QAResult(
                answer=ESCALATION_MESSAGE,
                source_refs=citations,
                confidence=confidence,
                covered=covered,
                escalated=True,
            )

        return QAResult(
            answer=parsed["answer"],
            source_refs=citations,
            confidence=confidence,
            covered=True,
            escalated=False,
        )

    # --- network ------------------------------------------------------------------

    async def _call_claude(self, prompt: str) -> str:
        headers = {
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
            "x-api-key": self.api_key,
        }
        payload = {
            "model": self.model,
            "max_tokens": 1024,
            "messages": [{"role": "user", "content": prompt}],
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(
                CLAUDE_API_URL, json=payload, headers=headers, timeout=60.0
            )
        if response.status_code != 200:
            logger.error("Claude API error (Q&A): %s - %s", response.status_code, response.text)
            raise Exception(f"Claude API error: {response.status_code}")
        return response.json().get("content", [{}])[0].get("text", "")


def _clamp01(value: Any) -> float:
    try:
        f = float(value)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(1.0, f))
