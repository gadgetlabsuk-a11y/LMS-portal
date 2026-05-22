"""Tests for the ILB Q&A grounding + guardrails (pure logic, no API key needed)."""

from services.qa_service import QAService, QAResult, CONFIDENCE_THRESHOLD, ESCALATION_MESSAGE


def _svc():
    # __init__ only reads settings.CLAUDE_API_KEY; no network until answer() is called.
    return QAService()


# --- _apply_guardrails ---------------------------------------------------------

def test_grounded_answer_passes_through():
    """Covered + confident + cited => answer returned, not escalated."""
    svc = _svc()
    parsed = {"answer": "Wear the harness above 2m.", "citations": ["work above 2 metres requires a harness"], "covered": True, "confidence": 0.92}
    result = svc._apply_guardrails(parsed, CONFIDENCE_THRESHOLD)
    assert isinstance(result, QAResult)
    assert result.escalated is False
    assert result.answer == "Wear the harness above 2m."
    assert result.source_refs == ["work above 2 metres requires a harness"]
    assert result.disclaimer  # always present


def test_not_covered_escalates():
    """Source doesn't cover the question => escalate."""
    svc = _svc()
    parsed = {"answer": "", "citations": [], "covered": False, "confidence": 0.1}
    result = svc._apply_guardrails(parsed, CONFIDENCE_THRESHOLD)
    assert result.escalated is True
    assert result.answer == ESCALATION_MESSAGE


def test_low_confidence_escalates():
    """Covered + cited but below threshold => escalate (don't risk a wrong safety answer)."""
    svc = _svc()
    parsed = {"answer": "Maybe 1.8m?", "citations": ["some height rule"], "covered": True, "confidence": 0.4}
    result = svc._apply_guardrails(parsed, CONFIDENCE_THRESHOLD)
    assert result.escalated is True
    assert result.answer == ESCALATION_MESSAGE


def test_no_citation_escalates_even_if_confident():
    """No grounding citation => can't trust it, escalate regardless of confidence."""
    svc = _svc()
    parsed = {"answer": "Confident but ungrounded.", "citations": [], "covered": True, "confidence": 0.99}
    result = svc._apply_guardrails(parsed, CONFIDENCE_THRESHOLD)
    assert result.escalated is True


# --- _parse --------------------------------------------------------------------

def test_parse_plain_json():
    svc = _svc()
    raw = '{"answer": "Yes.", "citations": ["x"], "covered": true, "confidence": 0.8}'
    parsed = svc._parse(raw)
    assert parsed["answer"] == "Yes."
    assert parsed["covered"] is True
    assert parsed["confidence"] == 0.8


def test_parse_markdown_wrapped_json():
    svc = _svc()
    raw = "Here you go:\n```json\n{\"answer\": \"A\", \"citations\": [], \"covered\": false, \"confidence\": 0.2}\n```"
    parsed = svc._parse(raw)
    assert parsed["answer"] == "A"
    assert parsed["covered"] is False


def test_parse_garbage_is_not_covered():
    """Unparseable model output must fail safe to 'not covered' (=> escalate)."""
    svc = _svc()
    parsed = svc._parse("the model rambled without json")
    assert parsed["covered"] is False
    assert parsed["confidence"] == 0.0


def test_confidence_is_clamped():
    svc = _svc()
    assert svc._parse('{"confidence": 5}')["confidence"] == 1.0
    assert svc._parse('{"confidence": -2}')["confidence"] == 0.0
