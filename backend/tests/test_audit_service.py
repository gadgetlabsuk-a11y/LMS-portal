"""Tests for ILB audit service (pure logic — hash chain, record assembly, pack). No DB needed."""

from datetime import datetime
from types import SimpleNamespace

from services.audit_service import (
    AuditService,
    StubAnchorProvider,
    compute_content_hash,
)


def _att(seq, content_hash, prev_hash):
    return SimpleNamespace(sequence=seq, content_hash=content_hash, prev_hash=prev_hash)


# --- compute_content_hash ------------------------------------------------------

def test_content_hash_is_deterministic_and_order_independent():
    a = {"x": 1, "y": [1, 2], "z": "t"}
    b = {"z": "t", "y": [1, 2], "x": 1}  # same data, different key order
    assert compute_content_hash(a) == compute_content_hash(b)


def test_content_hash_changes_when_record_changes():
    base = {"score": 80}
    tampered = {"score": 81}
    assert compute_content_hash(base) != compute_content_hash(tampered)


# --- verify_chain --------------------------------------------------------------

def test_valid_chain_verifies():
    a0 = _att(0, "h0", None)
    a1 = _att(1, "h1", "h0")
    a2 = _att(2, "h2", "h1")
    assert AuditService.verify_chain([a2, a0, a1]) is True  # order-insensitive input


def test_broken_prev_hash_fails():
    a0 = _att(0, "h0", None)
    a1 = _att(1, "h1", "WRONG")
    assert AuditService.verify_chain([a0, a1]) is False


def test_tampered_first_record_breaks_chain():
    # If a0's content was altered (h0 -> hX) but a1 still points at h0, the chain breaks.
    a0 = _att(0, "hX", None)
    a1 = _att(1, "h1", "h0")
    assert AuditService.verify_chain([a0, a1]) is False


def test_missing_sequence_fails():
    a0 = _att(0, "h0", None)
    a2 = _att(2, "h2", "h0")  # gap: no sequence 1
    assert AuditService.verify_chain([a0, a2]) is False


# --- build_session_record ------------------------------------------------------

def test_build_session_record_computes_time_and_counts():
    svc = AuditService()
    session = SimpleNamespace(
        id=7, mode="interrupt",
        started_at=datetime(2026, 5, 21, 10, 0, 0),
        completed_at=datetime(2026, 5, 21, 10, 9, 0),
        final_score=90.0, completion_status="completed",
    )
    interactions = [
        {"ts": "t1", "type": "answer", "question_text": "Q1", "answer_text": "A1", "escalated": False},
        {"ts": "t2", "type": "answer", "question_text": "Q2", "answer_text": "", "escalated": True},
        {"ts": "t3", "type": "check", "escalated": False},
        {"ts": "t4", "type": "attention", "escalated": False},
    ]
    record = svc.build_session_record(
        session=session,
        learner={"id": 3, "username": "stu"},
        course={"id": 11, "title": "Working at Height", "version": 2},
        interactions=interactions,
    )
    assert record["time_on_task_seconds"] == 540  # 9 minutes
    assert record["counts"]["qa"] == 2
    assert record["counts"]["knowledge_checks"] == 1
    assert record["counts"]["attention_checks"] == 1
    assert record["counts"]["escalations"] == 1
    assert record["learner"]["username"] == "stu"


# --- generate_pack + stub anchor ----------------------------------------------

def test_stub_anchor_seal_is_deterministic():
    anchor = StubAnchorProvider()
    sealed = anchor.seal("abc123")
    assert sealed["timestamp_token"].startswith("STUB-TSA:")
    assert "abc123" in sealed["anchor_ref"]


def test_generate_pack_emits_json_and_html():
    svc = AuditService()
    record = {
        "session_id": 7, "mode": "interrupt", "learner": {"id": 3, "username": "stu"},
        "course": {"id": 11, "title": "Working at Height", "version": 2},
        "counts": {"qa": 1, "knowledge_checks": 1, "escalations": 0},
        "interactions": [{"ts": "t1", "type": "answer", "question_text": "Q1", "answer_text": "A1", "escalated": False}],
    }
    attestation = SimpleNamespace(
        sequence=0, content_hash="deadbeef", prev_hash=None,
        signed_at=datetime(2026, 5, 21), timestamp_token="STUB-TSA:dead", anchor_ref="worm-stub://x",
    )
    pack = svc.generate_pack(record, attestation)
    assert '"content_hash": "deadbeef"' in pack["json"]
    assert "Working at Height" in pack["html"]
    assert "deadbeef" in pack["html"]


def test_pack_html_escapes_user_content():
    """Interaction text is user-supplied; it must be HTML-escaped in the pack."""
    svc = AuditService()
    record = {
        "session_id": 1, "learner": {}, "course": {}, "counts": {},
        "interactions": [{"ts": "t", "type": "answer", "question_text": "<script>x</script>", "answer_text": "", "escalated": False}],
    }
    attestation = SimpleNamespace(sequence=0, content_hash="h", prev_hash=None,
                                  signed_at=None, timestamp_token=None, anchor_ref=None)
    pack = svc.generate_pack(record, attestation)
    assert "<script>x</script>" not in pack["html"]
    assert "&lt;script&gt;" in pack["html"]
