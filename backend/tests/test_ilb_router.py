"""Integration tests for the ILB router (session lifecycle, Q&A, audit pack).

The Claude call in qa_service is mocked so these run offline.
"""

import pytest
from unittest.mock import AsyncMock

import routers.ilb as ilb_router
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
