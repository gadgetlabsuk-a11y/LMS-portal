"""ILB regulator-grade audit — session records, per-learner hash chain, export pack.

Design (see docs/superpowers/specs/2026-05-21-ilb-design.md §7):
- Each completed BroadcastSession produces an auditable record (completion, score,
  Q&A transcript, time-on-task).
- Records are sealed into a per-learner hash chain (SessionAttestation): each attestation's
  prev_hash points at the learner's previous attestation content_hash.
- The external trust anchor (RFC 3161 timestamp + WORM storage) lives behind AnchorProvider.
  The demo uses StubAnchorProvider; the praxis rebuild swaps in a real RFC 3161 TSA + S3 Object
  Lock implementation WITHOUT changing call sites.
- Export pack = JSON (machine-readable) + HTML (human-readable, printable to PDF). True PDF/A
  rendering is a praxis hardening item, same as the anchor.

`compute_content_hash`, `build_session_record`, `verify_chain`, and `generate_pack` are pure and
unit-testable without a database.
"""

import hashlib
import html
import json
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence

logger = logging.getLogger(__name__)


def compute_content_hash(record: Dict[str, Any]) -> str:
    """Deterministic SHA-256 over a canonical JSON serialisation of the record."""
    canonical = json.dumps(record, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class AnchorProvider(ABC):
    """Seals a content hash with an external, tamper-evident anchor."""

    @abstractmethod
    def seal(self, content_hash: str) -> Dict[str, Optional[str]]:
        """Return {'timestamp_token': ..., 'anchor_ref': ...}."""
        raise NotImplementedError


class StubAnchorProvider(AnchorProvider):
    """Demo stub. Praxis swaps in RFC 3161 TSA + S3 Object Lock (WORM)."""

    def seal(self, content_hash: str) -> Dict[str, Optional[str]]:
        return {
            "timestamp_token": f"STUB-TSA:{content_hash[:16]}",
            "anchor_ref": f"worm-stub://attestations/{content_hash}",
        }


class AuditService:
    def __init__(self, anchor: Optional[AnchorProvider] = None) -> None:
        self.anchor = anchor or StubAnchorProvider()

    # --- pure: record assembly ----------------------------------------------------

    def build_session_record(
        self,
        *,
        session: Any,
        learner: Dict[str, Any],
        course: Dict[str, Any],
        interactions: Sequence[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Assemble the auditable record from a BroadcastSession + its interactions.

        `session` may be the ORM object or any object exposing the same attributes.
        `interactions` is a list of dicts (ts, type, question_text, answer_text, escalated, ...).
        """
        started = getattr(session, "started_at", None)
        completed = getattr(session, "completed_at", None)
        time_on_task_s = None
        if started and completed:
            time_on_task_s = int((completed - started).total_seconds())

        qa = [i for i in interactions if i.get("type") in ("question", "answer")]
        checks = [i for i in interactions if i.get("type") == "check"]
        attention = [i for i in interactions if i.get("type") == "attention"]

        return {
            "session_id": getattr(session, "id", None),
            "mode": getattr(session, "mode", None),
            "learner": {"id": learner.get("id"), "username": learner.get("username")},
            "course": {"id": course.get("id"), "title": course.get("title"),
                       "version": course.get("version")},
            "started_at": started,
            "completed_at": completed,
            "time_on_task_seconds": time_on_task_s,
            "final_score": getattr(session, "final_score", None),
            "completion_status": getattr(session, "completion_status", None),
            "counts": {
                "qa": len(qa),
                "knowledge_checks": len(checks),
                "attention_checks": len(attention),
                "escalations": sum(1 for i in interactions if i.get("escalated")),
            },
            "interactions": list(interactions),
        }

    # --- pure: hash chain verification --------------------------------------------

    @staticmethod
    def verify_chain(attestations: Sequence[Any]) -> bool:
        """Verify a per-learner attestation chain.

        Accepts ORM SessionAttestation objects or any object exposing
        .sequence, .content_hash, .prev_hash. Returns True iff sequences increment from 0
        and each prev_hash matches the previous content_hash.
        """
        ordered = sorted(attestations, key=lambda a: a.sequence)
        prev_hash = None
        for expected_seq, att in enumerate(ordered):
            if att.sequence != expected_seq:
                return False
            if att.prev_hash != prev_hash:
                return False
            prev_hash = att.content_hash
        return True

    # --- db: attestation ----------------------------------------------------------

    def attest(self, db: Any, broadcast_session: Any, record: Optional[Dict[str, Any]] = None) -> Any:
        """Compute + persist a SessionAttestation, linking it into the learner's chain.

        Requires a SQLAlchemy session `db`. `record` defaults to a minimal record built from
        the session if not supplied.
        """
        from models import SessionAttestation  # local import to keep pure helpers import-light

        learner_id = None
        enrollment = getattr(broadcast_session, "enrollment", None)
        if enrollment is not None:
            learner_id = getattr(enrollment, "user_id", None)

        if record is None:
            record = {
                "session_id": getattr(broadcast_session, "id", None),
                "completion_status": getattr(broadcast_session, "completion_status", None),
                "final_score": getattr(broadcast_session, "final_score", None),
                "completed_at": getattr(broadcast_session, "completed_at", None),
            }

        content_hash = compute_content_hash(record)

        prev = (
            db.query(SessionAttestation)
            .filter(SessionAttestation.learner_id == learner_id)
            .order_by(SessionAttestation.sequence.desc())
            .first()
        )
        sequence = (prev.sequence + 1) if prev else 0
        prev_hash = prev.content_hash if prev else None

        sealed = self.anchor.seal(content_hash)
        attestation = SessionAttestation(
            broadcast_session_id=getattr(broadcast_session, "id", None),
            learner_id=learner_id,
            sequence=sequence,
            content_hash=content_hash,
            prev_hash=prev_hash,
            signed_at=datetime.utcnow(),
            timestamp_token=sealed.get("timestamp_token"),
            anchor_ref=sealed.get("anchor_ref"),
        )
        db.add(attestation)
        db.commit()
        db.refresh(attestation)
        return attestation

    # --- pure: export pack --------------------------------------------------------

    def generate_pack(self, record: Dict[str, Any], attestation: Any) -> Dict[str, Any]:
        """Build the regulator export pack: JSON (machine) + HTML (human, printable to PDF)."""
        attestation_block = {
            "sequence": getattr(attestation, "sequence", None),
            "content_hash": getattr(attestation, "content_hash", None),
            "prev_hash": getattr(attestation, "prev_hash", None),
            "signed_at": getattr(attestation, "signed_at", None),
            "timestamp_token": getattr(attestation, "timestamp_token", None),
            "anchor_ref": getattr(attestation, "anchor_ref", None),
        }
        pack = {"record": record, "attestation": attestation_block}
        json_doc = json.dumps(pack, indent=2, default=str)
        return {"json": json_doc, "html": self._render_html(record, attestation_block)}

    @staticmethod
    def _render_html(record: Dict[str, Any], attestation: Dict[str, Any]) -> str:
        def esc(v: Any) -> str:
            return html.escape(str(v))

        learner = record.get("learner", {})
        course = record.get("course", {})
        counts = record.get("counts", {})
        rows = "".join(
            f"<tr><td>{esc(i.get('ts'))}</td><td>{esc(i.get('type'))}</td>"
            f"<td>{esc(i.get('question_text') or '')}</td>"
            f"<td>{esc(i.get('answer_text') or '')}</td>"
            f"<td>{esc(i.get('escalated'))}</td></tr>"
            for i in record.get("interactions", [])
        )
        return f"""<!doctype html><html><head><meta charset="utf-8">
<title>ILB Audit Pack — session {esc(record.get('session_id'))}</title></head><body>
<h1>Interactive Learning Broadcast — Audit Record</h1>
<p><strong>Learner:</strong> {esc(learner.get('username'))} (id {esc(learner.get('id'))})</p>
<p><strong>Course:</strong> {esc(course.get('title'))} (v{esc(course.get('version'))})</p>
<p><strong>Mode:</strong> {esc(record.get('mode'))} &middot;
   <strong>Status:</strong> {esc(record.get('completion_status'))} &middot;
   <strong>Score:</strong> {esc(record.get('final_score'))}</p>
<p><strong>Started:</strong> {esc(record.get('started_at'))} &middot;
   <strong>Completed:</strong> {esc(record.get('completed_at'))} &middot;
   <strong>Time on task:</strong> {esc(record.get('time_on_task_seconds'))}s</p>
<p><strong>Q&amp;A:</strong> {esc(counts.get('qa'))} &middot;
   <strong>Knowledge checks:</strong> {esc(counts.get('knowledge_checks'))} &middot;
   <strong>Escalations:</strong> {esc(counts.get('escalations'))}</p>
<h2>Interaction log</h2>
<table border="1" cellpadding="4" cellspacing="0">
<tr><th>Time</th><th>Type</th><th>Question</th><th>Answer</th><th>Escalated</th></tr>
{rows}
</table>
<h2>Tamper-evidence</h2>
<p><strong>Chain sequence:</strong> {esc(attestation.get('sequence'))}</p>
<p><strong>Content hash:</strong> <code>{esc(attestation.get('content_hash'))}</code></p>
<p><strong>Previous hash:</strong> <code>{esc(attestation.get('prev_hash'))}</code></p>
<p><strong>Timestamp token:</strong> <code>{esc(attestation.get('timestamp_token'))}</code></p>
<p><strong>Anchor ref:</strong> <code>{esc(attestation.get('anchor_ref'))}</code></p>
<p><em>Note: timestamp token + anchor are demo stubs; production uses an RFC 3161 TSA and WORM storage.</em></p>
</body></html>"""
