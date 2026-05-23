"""Integration tests for the ILB router (session lifecycle, Q&A, audit pack).

The Claude call in qa_service is mocked so these run offline.
"""

import pytest
from types import SimpleNamespace
from unittest.mock import AsyncMock

import routers.ilb as ilb_router
from config import settings
from models import Enrollment, Interaction, User, UserRole
from services.qa_service import QAResult
from services.auth_service import AuthService


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def enrollment(db, trainee_user, published_course):
    e = Enrollment(user_id=trainee_user.id, course_id=published_course.id, course_version=1)
    db.add(e)
    db.commit()
    db.refresh(e)
    return e


def test_session_lifecycle(client, db, trainee_token, published_course, enrollment, monkeypatch):
    # start (enrolment pre-exists via fixture -> find path)
    r = client.post(
        "/api/ilb/sessions",
        json={"course_id": published_course.id, "mode": "interrupt"},
        headers=_auth(trainee_token),
    )
    assert r.status_code == 201, r.text
    sid = r.json()["session"]["id"]
    assert r.json()["live"]["provider"] == "stub"

    # get
    r = client.get(f"/api/ilb/sessions/{sid}", headers=_auth(trainee_token))
    assert r.status_code == 200
    assert r.json()["completion_status"] == "in_progress"

    # ask (mock the grounded Q&A so no network)
    monkeypatch.setattr(
        ilb_router._qa,
        "answer",
        AsyncMock(return_value=QAResult(
            answer="Grounded answer.", source_refs=["a passage"], confidence=0.9,
            covered=True, escalated=False,
        )),
    )
    r = client.post(
        f"/api/ilb/sessions/{sid}/ask",
        json={"question": "What is X?", "input_mode": "text"},
        headers=_auth(trainee_token),
    )
    assert r.status_code == 200, r.text
    assert r.json()["answer"] == "Grounded answer."
    assert r.json()["escalated"] is False
    assert db.query(Interaction).filter(Interaction.broadcast_session_id == sid).count() == 1

    # complete -> seals into the learner hash chain
    r = client.post(
        f"/api/ilb/sessions/{sid}/complete",
        json={"final_score": 88.0},
        headers=_auth(trainee_token),
    )
    assert r.status_code == 200, r.text
    assert r.json()["session"]["completion_status"] == "completed"
    assert r.json()["attestation"]["sequence"] == 0
    assert r.json()["attestation"]["content_hash"]

    # audit pack
    r = client.get(f"/api/ilb/sessions/{sid}/audit-pack", headers=_auth(trainee_token))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["record"]["completion_status"] == "completed"
    assert body["attestation"]["sequence"] == 0
    assert "Audit Record" in body["html"]


def test_invalid_mode_rejected(client, trainee_token, published_course):
    r = client.post(
        "/api/ilb/sessions",
        json={"course_id": published_course.id, "mode": "bogus"},
        headers=_auth(trainee_token),
    )
    assert r.status_code == 422


def test_start_autocreates_enrollment(client, db, trainee_user, trainee_token, published_course):
    """Enrolment management isn't built yet — starting a broadcast find-or-creates one."""
    before = db.query(Enrollment).filter(
        Enrollment.user_id == trainee_user.id, Enrollment.course_id == published_course.id
    ).count()
    assert before == 0
    r = client.post(
        "/api/ilb/sessions",
        json={"course_id": published_course.id},
        headers=_auth(trainee_token),
    )
    assert r.status_code == 201, r.text
    after = db.query(Enrollment).filter(
        Enrollment.user_id == trainee_user.id, Enrollment.course_id == published_course.id
    ).count()
    assert after == 1


def test_ownership_enforced(client, db, trainee_token, published_course):
    r = client.post(
        "/api/ilb/sessions",
        json={"course_id": published_course.id},
        headers=_auth(trainee_token),
    )
    sid = r.json()["session"]["id"]

    other = User(
        username="other_trainee", email="other_t@example.com",
        hashed_password=AuthService.hash_password("pass123"), role=UserRole.TRAINEE, is_active=True,
    )
    db.add(other)
    db.commit()
    db.refresh(other)
    other_token = AuthService.create_access_token(
        user_id=other.id, username=other.username, role=other.role.value,
    )
    r = client.get(f"/api/ilb/sessions/{sid}", headers=_auth(other_token))
    assert r.status_code == 403


# --- podcast-script authoring route -------------------------------------------

def test_podcast_script_creator(client, db, creator_token, creator_course, monkeypatch):
    monkeypatch.setattr(ilb_router, "_assemble_course_source", lambda db, cid: "Some course content.")
    monkeypatch.setattr(
        ilb_router._claude,
        "generate_podcast_script",
        AsyncMock(return_value={"script": "Hello listeners.", "segments": ["Hello listeners."]}),
    )
    r = client.post(
        f"/api/ilb/courses/{creator_course.id}/podcast-script",
        json={"host_persona": "a friendly host", "target_minutes": 5},
        headers=_auth(creator_token),
    )
    assert r.status_code == 200, r.text
    assert r.json()["script"] == "Hello listeners."
    assert r.json()["segments"] == ["Hello listeners."]


def test_podcast_script_trainee_forbidden(client, trainee_token, published_course):
    r = client.post(
        f"/api/ilb/courses/{published_course.id}/podcast-script",
        json={},
        headers=_auth(trainee_token),
    )
    assert r.status_code == 403


def test_podcast_script_empty_source_rejected(client, creator_token, creator_course, monkeypatch):
    monkeypatch.setattr(ilb_router, "_assemble_course_source", lambda db, cid: "")
    r = client.post(
        f"/api/ilb/courses/{creator_course.id}/podcast-script",
        json={},
        headers=_auth(creator_token),
    )
    assert r.status_code == 422


# --- persist / publish --------------------------------------------------------

def test_save_and_get_podcast_config(client, db, creator_token, creator_course):
    r = client.put(
        f"/api/ilb/courses/{creator_course.id}/podcast",
        json={"script": "Intro.[SEGMENT BREAK]Body.", "host_persona": "host", "avatar_id": "av1"},
        headers=_auth(creator_token),
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["segments"] == ["Intro.", "Body."]
    assert body["published"] is False
    # creator can read the draft back
    r = client.get(f"/api/ilb/courses/{creator_course.id}/podcast", headers=_auth(creator_token))
    assert r.status_code == 200
    assert r.json()["avatar_id"] == "av1"


def test_learner_cannot_see_unpublished(client, db, trainee_token, creator_course):
    r = client.get(f"/api/ilb/courses/{creator_course.id}/podcast", headers=_auth(trainee_token))
    assert r.status_code == 404


def test_publish_then_learner_sees(client, db, creator_token, trainee_token, creator_course):
    client.put(
        f"/api/ilb/courses/{creator_course.id}/podcast",
        json={"script": "Hello."},
        headers=_auth(creator_token),
    )
    r = client.post(
        f"/api/ilb/courses/{creator_course.id}/podcast/publish",
        json={"published": True},
        headers=_auth(creator_token),
    )
    assert r.status_code == 200, r.text
    assert r.json()["published"] is True
    r = client.get(f"/api/ilb/courses/{creator_course.id}/podcast", headers=_auth(trainee_token))
    assert r.status_code == 200
    assert r.json()["published"] is True


def test_publish_without_script_rejected(client, db, creator_token, creator_course):
    r = client.post(
        f"/api/ilb/courses/{creator_course.id}/podcast/publish",
        json={"published": True},
        headers=_auth(creator_token),
    )
    assert r.status_code == 422


def test_save_podcast_trainee_forbidden(client, db, trainee_token, creator_course):
    r = client.put(
        f"/api/ilb/courses/{creator_course.id}/podcast",
        json={"script": "x"},
        headers=_auth(trainee_token),
    )
    assert r.status_code == 403


# --- voice + narration audio --------------------------------------------------

def test_list_voices(client, trainee_token, monkeypatch):
    monkeypatch.setattr(
        ilb_router._tts,
        "list_voices",
        AsyncMock(return_value=[{"voice_id": "v1", "name": "Rachel", "description": "American female"}]),
    )
    r = client.get("/api/ilb/voices", headers=_auth(trainee_token))
    assert r.status_code == 200, r.text
    assert r.json()[0]["voice_id"] == "v1"


def test_save_sets_voice_and_clears_audio(client, db, creator_token, creator_course):
    r = client.put(
        f"/api/ilb/courses/{creator_course.id}/podcast",
        json={"script": "Hello.", "voice_id": "voiceX"},
        headers=_auth(creator_token),
    )
    assert r.status_code == 200, r.text
    assert r.json()["voice_id"] == "voiceX"
    assert r.json()["segment_audio"] is None


def test_render_audio_happy(client, db, creator_token, creator_course, monkeypatch):
    client.put(
        f"/api/ilb/courses/{creator_course.id}/podcast",
        json={"script": "Intro.[SEGMENT BREAK]Body.", "voice_id": "voiceX"},
        headers=_auth(creator_token),
    )
    monkeypatch.setattr(ilb_router._tts, "api_key", "test-key")
    monkeypatch.setattr(ilb_router._tts, "synthesize", AsyncMock(return_value=b"audio-bytes"))
    r = client.post(
        f"/api/ilb/courses/{creator_course.id}/podcast/render-audio",
        json={},
        headers=_auth(creator_token),
    )
    assert r.status_code == 200, r.text
    assert len(r.json()["segment_audio"]) == 2


def test_render_audio_no_script_rejected(client, db, creator_token, creator_course, monkeypatch):
    monkeypatch.setattr(ilb_router._tts, "api_key", "test-key")
    r = client.post(
        f"/api/ilb/courses/{creator_course.id}/podcast/render-audio",
        json={},
        headers=_auth(creator_token),
    )
    assert r.status_code == 422


def test_render_audio_no_key(client, db, creator_token, creator_course, monkeypatch):
    client.put(
        f"/api/ilb/courses/{creator_course.id}/podcast",
        json={"script": "Hello."},
        headers=_auth(creator_token),
    )
    monkeypatch.setattr(ilb_router._tts, "api_key", "")
    r = client.post(
        f"/api/ilb/courses/{creator_course.id}/podcast/render-audio",
        json={},
        headers=_auth(creator_token),
    )
    assert r.status_code == 503


def test_render_audio_trainee_forbidden(client, db, trainee_token, creator_course):
    r = client.post(
        f"/api/ilb/courses/{creator_course.id}/podcast/render-audio",
        json={},
        headers=_auth(trainee_token),
    )
    assert r.status_code == 403


# --- voice Q&A (Deepgram STT + spoken answers) --------------------------------

def test_stt_no_key(client, trainee_token, monkeypatch):
    monkeypatch.setattr(settings, "DEEPGRAM_API_KEY", "")
    r = client.post(
        "/api/ilb/stt",
        files={"file": ("speech.webm", b"audio-bytes", "audio/webm")},
        headers=_auth(trainee_token),
    )
    assert r.status_code == 503


def test_stt_transcribes(client, trainee_token, monkeypatch):
    monkeypatch.setattr(settings, "DEEPGRAM_API_KEY", "test-key")
    fake = SimpleNamespace(transcribe=AsyncMock(return_value="what is lockout tagout"))
    monkeypatch.setattr(ilb_router, "get_stt_provider", lambda: fake)
    r = client.post(
        "/api/ilb/stt",
        files={"file": ("speech.webm", b"audio-bytes", "audio/webm")},
        headers=_auth(trainee_token),
    )
    assert r.status_code == 200, r.text
    assert r.json()["transcript"] == "what is lockout tagout"


def test_ask_returns_answer_audio(client, db, trainee_token, published_course, monkeypatch):
    r = client.post(
        "/api/ilb/sessions",
        json={"course_id": published_course.id},
        headers=_auth(trainee_token),
    )
    sid = r.json()["session"]["id"]
    published_course.ilb_voice_id = "voiceX"
    db.commit()
    monkeypatch.setattr(
        ilb_router._qa,
        "answer",
        AsyncMock(return_value=QAResult(answer="An answer.", source_refs=["s"], confidence=0.9, covered=True, escalated=False)),
    )
    monkeypatch.setattr(ilb_router._tts, "api_key", "test-key")
    monkeypatch.setattr(ilb_router._tts, "synthesize", AsyncMock(return_value=b"answer-audio"))
    r = client.post(
        f"/api/ilb/sessions/{sid}/ask",
        json={"question": "What is X?", "input_mode": "voice"},
        headers=_auth(trainee_token),
    )
    assert r.status_code == 200, r.text
    assert r.json()["answer_audio_url"] is not None


# --- standalone broadcasts ----------------------------------------------------

def _make_broadcast(client, creator_token, title="Team Brief"):
    r = client.post(
        "/api/ilb/broadcasts",
        json={"title": title, "source_text": "Company news content."},
        headers=_auth(creator_token),
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


def test_create_broadcast_creator_and_trainee(client, db, creator_token, trainee_token):
    r = client.post("/api/ilb/broadcasts", json={"title": "Team Brief"}, headers=_auth(creator_token))
    assert r.status_code == 201, r.text
    assert r.json()["title"] == "Team Brief"
    assert client.post("/api/ilb/broadcasts", json={"title": "X"}, headers=_auth(trainee_token)).status_code == 403


def test_list_broadcasts_learner_sees_published_only(client, db, creator_token, trainee_token):
    bid = _make_broadcast(client, creator_token, "Published Brief")
    client.put(f"/api/ilb/broadcasts/{bid}", json={"script": "Hello."}, headers=_auth(creator_token))
    client.post(f"/api/ilb/broadcasts/{bid}/publish", json={"published": True}, headers=_auth(creator_token))
    _make_broadcast(client, creator_token, "Draft Brief")
    titles = [b["title"] for b in client.get("/api/ilb/broadcasts", headers=_auth(trainee_token)).json()]
    assert "Published Brief" in titles and "Draft Brief" not in titles


def test_update_broadcast_computes_segments_clears_audio(client, db, creator_token):
    bid = _make_broadcast(client, creator_token)
    r = client.put(
        f"/api/ilb/broadcasts/{bid}",
        json={"script": "A.[SEGMENT BREAK]B.", "voice_id": "v1"},
        headers=_auth(creator_token),
    )
    assert r.status_code == 200, r.text
    assert r.json()["segments"] == ["A.", "B."]
    assert r.json()["segment_audio"] is None
    assert r.json()["voice_id"] == "v1"


def test_broadcast_generate_script(client, db, creator_token, monkeypatch):
    bid = _make_broadcast(client, creator_token)
    monkeypatch.setattr(
        ilb_router._claude, "generate_podcast_script",
        AsyncMock(return_value={"script": "Welcome.", "segments": ["Welcome."]}),
    )
    r = client.post(f"/api/ilb/broadcasts/{bid}/generate-script", json={"target_minutes": 3}, headers=_auth(creator_token))
    assert r.status_code == 200, r.text
    assert r.json()["script"] == "Welcome."


def test_broadcast_publish_requires_script(client, db, creator_token, trainee_token):
    bid = _make_broadcast(client, creator_token)
    assert client.post(f"/api/ilb/broadcasts/{bid}/publish", json={"published": True}, headers=_auth(creator_token)).status_code == 422
    client.put(f"/api/ilb/broadcasts/{bid}", json={"script": "Hello."}, headers=_auth(creator_token))
    r = client.post(f"/api/ilb/broadcasts/{bid}/publish", json={"published": True}, headers=_auth(creator_token))
    assert r.status_code == 200 and r.json()["published"] is True
    assert client.get(f"/api/ilb/broadcasts/{bid}", headers=_auth(trainee_token)).status_code == 200


def test_standalone_session_lifecycle(client, db, creator_token, trainee_token, monkeypatch):
    bid = _make_broadcast(client, creator_token, "Safety Brief")
    client.put(f"/api/ilb/broadcasts/{bid}", json={"script": "Wear your harness."}, headers=_auth(creator_token))
    client.post(f"/api/ilb/broadcasts/{bid}/publish", json={"published": True}, headers=_auth(creator_token))

    r = client.post("/api/ilb/sessions", json={"broadcast_id": bid}, headers=_auth(trainee_token))
    assert r.status_code == 201, r.text
    sid = r.json()["session"]["id"]
    assert r.json()["session"]["broadcast_id"] == bid

    monkeypatch.setattr(
        ilb_router._qa, "answer",
        AsyncMock(return_value=QAResult(answer="A.", source_refs=["s"], confidence=0.9, covered=True, escalated=False)),
    )
    assert client.post(f"/api/ilb/sessions/{sid}/ask", json={"question": "Q?"}, headers=_auth(trainee_token)).status_code == 200

    r = client.post(f"/api/ilb/sessions/{sid}/complete", json={}, headers=_auth(trainee_token))
    assert r.status_code == 200, r.text
    assert r.json()["attestation"]["sequence"] == 0

    r = client.get(f"/api/ilb/sessions/{sid}/audit-pack", headers=_auth(trainee_token))
    assert r.status_code == 200, r.text
    assert r.json()["record"]["course"]["title"] == "Safety Brief"


def test_start_session_requires_exactly_one_target(client, db, trainee_token):
    # neither course_id nor broadcast_id -> 422
    assert client.post("/api/ilb/sessions", json={}, headers=_auth(trainee_token)).status_code == 422


def test_learner_cannot_start_unpublished_broadcast(client, db, creator_token, trainee_token):
    bid = _make_broadcast(client, creator_token)
    r = client.post("/api/ilb/sessions", json={"broadcast_id": bid}, headers=_auth(trainee_token))
    assert r.status_code == 404
