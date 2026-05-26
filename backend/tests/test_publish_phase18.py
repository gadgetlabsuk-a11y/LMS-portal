"""
Phase 18 publish/preview/preflight backend tests.
Requirements: PREVIEW-01, PREVIEW-02, PUBLISH-02 through PUBLISH-08.
"""
import pytest
from fastapi.testclient import TestClient
from main import app
from models import Course, CourseStatus, Enrollment, Module, Quiz, Question
from models.models import CourseVersion

client = TestClient(app)


# ---------------------------------------------------------------------------
# Local fixture: draft_creator_course (DRAFT status for publish flow tests)
# ---------------------------------------------------------------------------

@pytest.fixture
def draft_creator_course(db, creator_user):
    """A DRAFT course owned by creator_user for publish-flow testing."""
    course = Course(
        title="Draft Course for Publish Tests",
        description="Testing publish flow.",
        status=CourseStatus.DRAFT,
        creator_id=creator_user.id,
    )
    db.add(course)
    db.commit()
    db.refresh(course)
    return course


# ---------------------------------------------------------------------------
# PREVIEW-01: GET /api/courses/{id}/preview returns full tree for creator
# ---------------------------------------------------------------------------

def test_preview_endpoint_returns_draft_course(db, creator_token, draft_creator_course):
    """PREVIEW-01: Preview bypasses PUBLISHED filter — creator sees DRAFT course tree."""
    course_id = draft_creator_course.id
    headers = {"Authorization": f"Bearer {creator_token}"}

    # Add a module so we have content in the tree
    r = client.post(
        f"/api/courses/{course_id}/modules",
        json={"title": "Module One"},
        headers=headers,
    )
    assert r.status_code == 201

    resp = client.get(f"/api/courses/{course_id}/preview", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == course_id
    assert len(data["modules"]) >= 1


# ---------------------------------------------------------------------------
# PREVIEW-02: Preview includes nested content (slides, blocks, etc.)
# ---------------------------------------------------------------------------

def test_preview_includes_slides_and_blocks(db, creator_token, draft_creator_course):
    """PREVIEW-02: Full tree includes modules (and nested structure)."""
    course_id = draft_creator_course.id
    headers = {"Authorization": f"Bearer {creator_token}"}

    # Add module + video + slide + block via API
    mod_r = client.post(
        f"/api/courses/{course_id}/modules",
        json={"title": "Module Alpha"},
        headers=headers,
    )
    assert mod_r.status_code == 201
    module_id = mod_r.json()["id"]

    vid_r = client.post(
        f"/api/modules/{module_id}/videos",
        json={"title": "Video Alpha"},
        headers=headers,
    )
    assert vid_r.status_code == 201
    video_id = vid_r.json()["id"]

    slide_r = client.post(
        f"/api/videos/{video_id}/slides",
        json={"layout_id": "blank"},
        headers=headers,
    )
    assert slide_r.status_code == 201
    slide_id = slide_r.json()["id"]

    client.post(
        f"/api/slides/{slide_id}/blocks",
        json={"type": "text", "content": {"text": "Hello"}},
        headers=headers,
    )

    resp = client.get(f"/api/courses/{course_id}/preview", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    modules = data["modules"]
    assert len(modules) >= 1
    # Videos should be nested
    assert "videos" in modules[0]


# ---------------------------------------------------------------------------
# PREVIEW-03: Preview tree includes VIDEO-level quizzes in player shape,
# without leaking correct_answer.
# ---------------------------------------------------------------------------

def test_preview_includes_video_level_quizzes_without_answers(db, creator_token, draft_creator_course):
    """Preview must serialize video.quizzes (the player reads quizzes there),
    in the learner player shape, and must NOT leak correct_answer."""
    course_id = draft_creator_course.id
    headers = {"Authorization": f"Bearer {creator_token}"}

    # module → video
    mod_r = client.post(f"/api/courses/{course_id}/modules", json={"title": "M"}, headers=headers)
    assert mod_r.status_code == 201
    module_id = mod_r.json()["id"]
    vid_r = client.post(f"/api/modules/{module_id}/videos", json={"title": "V"}, headers=headers)
    assert vid_r.status_code == 201
    video_id = vid_r.json()["id"]

    # Attach a VIDEO-level quiz + a question directly (no module_id).
    quiz = Quiz(video_id=video_id, title="Knowledge Check", pass_rate=80, attempts_allowed=3, order_index=0)
    db.add(quiz)
    db.flush()
    db.add(Question(
        quiz_id=quiz.id, type="mcq_single", prompt="2+2?",
        options=["3", "4"], correct_answer=1, points=1, order_index=0,
    ))
    db.commit()

    resp = client.get(f"/api/courses/{course_id}/preview", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    video = data["modules"][0]["videos"][0]
    assert "quizzes" in video
    assert len(video["quizzes"]) == 1
    q = video["quizzes"][0]
    # Player shape fields present
    assert q["title"] == "Knowledge Check"
    assert q["attempts_used"] == 0
    assert q["attempts_remaining"] == 3
    assert q["passed"] is False
    assert q["last_score"] is None
    assert len(q["questions"]) == 1
    # correct_answer / explanation must NOT leak in preview
    assert "correct_answer" not in q["questions"][0]
    assert "explanation" not in q["questions"][0]


# ---------------------------------------------------------------------------
# PREVIEW-04: Preview tree includes MODULE-level quizzes in player shape,
# without leaking correct_answer (preview now passes for_player=True).
# ---------------------------------------------------------------------------

def test_preview_includes_module_level_quizzes_without_answers(db, creator_token, draft_creator_course):
    """Preview must serialize module.quizzes in the learner player shape and
    must NOT leak correct_answer/explanation."""
    course_id = draft_creator_course.id
    headers = {"Authorization": f"Bearer {creator_token}"}

    mod_r = client.post(f"/api/courses/{course_id}/modules", json={"title": "M"}, headers=headers)
    assert mod_r.status_code == 201
    module_id = mod_r.json()["id"]

    # Attach a MODULE-level quiz + a question directly (no video_id).
    quiz = Quiz(module_id=module_id, title="Module Assessment", pass_rate=80, attempts_allowed=3, order_index=0)
    db.add(quiz)
    db.flush()
    db.add(Question(
        quiz_id=quiz.id, type="mcq_single", prompt="2+2?",
        options=["3", "4"], correct_answer=1, points=1, order_index=0, explanation="maths",
    ))
    db.commit()

    resp = client.get(f"/api/courses/{course_id}/preview", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    module = data["modules"][0]
    assert "quizzes" in module
    assert len(module["quizzes"]) == 1
    mq = module["quizzes"][0]
    # Player shape fields present
    assert mq["title"] == "Module Assessment"
    assert mq["attempts_used"] == 0
    assert mq["attempts_remaining"] == 3
    assert mq["passed"] is False
    assert mq["last_score"] is None
    assert len(mq["questions"]) == 1
    q = mq["questions"][0]
    assert q["prompt"] == "2+2?"
    assert q["options"] == ["3", "4"]
    # correct_answer / explanation must NOT leak in preview
    assert "correct_answer" not in q
    assert "explanation" not in q


def test_publish_snapshot_keeps_module_quiz_answers(db, creator_token, draft_creator_course):
    """The publish snapshot (for_player=False default) must still embed
    correct_answer for module-level quiz questions."""
    from routers.courses import _serialize_course_tree

    course_id = draft_creator_course.id
    headers = {"Authorization": f"Bearer {creator_token}"}

    mod_r = client.post(f"/api/courses/{course_id}/modules", json={"title": "M"}, headers=headers)
    assert mod_r.status_code == 201
    module_id = mod_r.json()["id"]

    quiz = Quiz(module_id=module_id, title="Module Assessment", pass_rate=80, attempts_allowed=3, order_index=0)
    db.add(quiz)
    db.flush()
    db.add(Question(
        quiz_id=quiz.id, type="mcq_single", prompt="2+2?",
        options=["3", "4"], correct_answer=1, points=1, order_index=0,
    ))
    db.commit()

    # Default (for_player=False) — the publish snapshot path — keeps answers.
    tree = _serialize_course_tree(course_id, db)
    mq = tree["modules"][0]["quizzes"][0]
    assert mq["questions"][0]["correct_answer"] == 1


# ---------------------------------------------------------------------------
# PUBLISH-02: GET /api/courses/{id}/preflight returns structured results
# ---------------------------------------------------------------------------

def test_preflight_returns_results(db, creator_token, draft_creator_course):
    """PUBLISH-02: Preflight returns can_publish bool and results list."""
    course_id = draft_creator_course.id
    headers = {"Authorization": f"Bearer {creator_token}"}

    resp = client.get(f"/api/courses/{course_id}/preflight", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "can_publish" in data
    assert "results" in data
    assert isinstance(data["results"], list)
    assert len(data["results"]) > 0


# ---------------------------------------------------------------------------
# PUBLISH-03: Preflight fails when no modules present
# ---------------------------------------------------------------------------

def test_preflight_fails_no_modules(db, creator_token, draft_creator_course):
    """PUBLISH-03: Empty course → has_at_least_one_module rule fails."""
    course_id = draft_creator_course.id
    headers = {"Authorization": f"Bearer {creator_token}"}

    resp = client.get(f"/api/courses/{course_id}/preflight", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["can_publish"] is False

    rule_statuses = {r["rule"]: r["status"] for r in data["results"]}
    assert rule_statuses.get("has_at_least_one_module") == "fail"


# ---------------------------------------------------------------------------
# PUBLISH-04: Preflight fix_url present on fail results
# ---------------------------------------------------------------------------

def test_preflight_fix_urls_present(db, creator_token, draft_creator_course):
    """PUBLISH-04: Every fail result includes a fix_url starting with /creator/courses/."""
    course_id = draft_creator_course.id
    headers = {"Authorization": f"Bearer {creator_token}"}

    resp = client.get(f"/api/courses/{course_id}/preflight", headers=headers)
    assert resp.status_code == 200
    data = resp.json()

    for r in data["results"]:
        if r["status"] == "fail":
            assert r["fix_url"] is not None
            assert r["fix_url"].startswith("/creator/courses/")


# ---------------------------------------------------------------------------
# PUBLISH-05: POST /publish transitions course to PUBLISHED
# ---------------------------------------------------------------------------

def test_publish_transitions_to_published(db, creator_token, draft_creator_course):
    """PUBLISH-05: Course with ≥1 module and quiz with ≥3 questions publishes successfully."""
    course_id = draft_creator_course.id
    headers = {"Authorization": f"Bearer {creator_token}"}

    # Add module
    mod_r = client.post(
        f"/api/courses/{course_id}/modules",
        json={"title": "Module for Publish"},
        headers=headers,
    )
    assert mod_r.status_code == 201
    module_id = mod_r.json()["id"]

    # Add quiz with 3 questions
    quiz_r = client.post(
        f"/api/modules/{module_id}/quizzes",
        json={"title": "Quiz One"},
        headers=headers,
    )
    assert quiz_r.status_code == 201
    quiz_id = quiz_r.json()["id"]

    for i in range(3):
        q_r = client.post(
            f"/api/quizzes/{quiz_id}/questions",
            json={"type": "true_false", "prompt": f"Question {i+1}?", "correct_answer": "True"},
            headers=headers,
        )
        assert q_r.status_code == 201

    resp = client.post(f"/api/courses/{course_id}/publish", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "published"


# ---------------------------------------------------------------------------
# PUBLISH-06: Publish creates a CourseVersion snapshot
# ---------------------------------------------------------------------------

def test_publish_creates_version_snapshot(db, creator_token, draft_creator_course):
    """PUBLISH-06: POST /publish creates a CourseVersion row with correct course_id."""
    course_id = draft_creator_course.id
    headers = {"Authorization": f"Bearer {creator_token}"}

    # Setup: module + quiz with 3 questions
    mod_r = client.post(
        f"/api/courses/{course_id}/modules",
        json={"title": "Snapshot Module"},
        headers=headers,
    )
    assert mod_r.status_code == 201
    module_id = mod_r.json()["id"]

    quiz_r = client.post(
        f"/api/modules/{module_id}/quizzes",
        json={"title": "Snapshot Quiz"},
        headers=headers,
    )
    assert quiz_r.status_code == 201
    quiz_id = quiz_r.json()["id"]

    for i in range(3):
        client.post(
            f"/api/quizzes/{quiz_id}/questions",
            json={"type": "true_false", "prompt": f"Q{i+1}?", "correct_answer": "True"},
            headers=headers,
        )

    resp = client.post(f"/api/courses/{course_id}/publish", headers=headers)
    assert resp.status_code == 200

    # Verify CourseVersion row exists in DB
    version_row = db.query(CourseVersion).filter(CourseVersion.course_id == course_id).first()
    assert version_row is not None
    assert version_row.course_id == course_id
    assert version_row.snapshot is not None


# ---------------------------------------------------------------------------
# PUBLISH-07: Enrolled learner gets their pinned version snapshot
# ---------------------------------------------------------------------------

def test_learner_gets_enrolled_version(db, creator_token, trainee_user, trainee_token, draft_creator_course):
    """PUBLISH-07: Learner with enrollment.course_version pin gets that snapshot title."""
    course_id = draft_creator_course.id
    headers = {"Authorization": f"Bearer {creator_token}"}

    # Setup: module + quiz to pass preflight
    mod_r = client.post(
        f"/api/courses/{course_id}/modules",
        json={"title": "Version Test Module"},
        headers=headers,
    )
    assert mod_r.status_code == 201
    module_id = mod_r.json()["id"]

    quiz_r = client.post(
        f"/api/modules/{module_id}/quizzes",
        json={"title": "Version Test Quiz"},
        headers=headers,
    )
    assert quiz_r.status_code == 201
    quiz_id = quiz_r.json()["id"]

    for i in range(3):
        client.post(
            f"/api/quizzes/{quiz_id}/questions",
            json={"type": "true_false", "prompt": f"Q{i+1}?", "correct_answer": "True"},
            headers=headers,
        )

    # Publish v1 (version_number = 1, stored in DB at version 1)
    pub_resp = client.post(f"/api/courses/{course_id}/publish", headers=headers)
    assert pub_resp.status_code == 200
    v1_title = draft_creator_course.title

    # Get the version_number that was stored (should be 1, which was course.version before bump)
    v1_row = db.query(CourseVersion).filter(
        CourseVersion.course_id == course_id
    ).order_by(CourseVersion.version_number).first()
    assert v1_row is not None
    enrolled_version_number = v1_row.version_number

    # Enroll trainee with that version pinned
    enrollment = Enrollment(
        user_id=trainee_user.id,
        course_id=course_id,
        course_version=enrolled_version_number,
    )
    db.add(enrollment)
    db.commit()

    # Learner GET should return v1 snapshot title
    learner_resp = client.get(
        f"/api/learn/courses/{course_id}",
        headers={"Authorization": f"Bearer {trainee_token}"},
    )
    assert learner_resp.status_code == 200
    assert learner_resp.json()["title"] == v1_title


# ---------------------------------------------------------------------------
# PUBLISH-08: Archive hides course from learner catalogue
# ---------------------------------------------------------------------------

def test_archive_hides_from_catalogue(db, creator_token, trainee_token, draft_creator_course):
    """PUBLISH-08: POST /archive → course not in GET /api/learn/courses."""
    course_id = draft_creator_course.id
    headers = {"Authorization": f"Bearer {creator_token}"}

    # Setup and publish first
    mod_r = client.post(
        f"/api/courses/{course_id}/modules",
        json={"title": "Archive Test Module"},
        headers=headers,
    )
    assert mod_r.status_code == 201
    module_id = mod_r.json()["id"]

    quiz_r = client.post(
        f"/api/modules/{module_id}/quizzes",
        json={"title": "Archive Quiz"},
        headers=headers,
    )
    assert quiz_r.status_code == 201
    quiz_id = quiz_r.json()["id"]

    for i in range(3):
        client.post(
            f"/api/quizzes/{quiz_id}/questions",
            json={"type": "true_false", "prompt": f"Q{i+1}?", "correct_answer": "True"},
            headers=headers,
        )

    pub_resp = client.post(f"/api/courses/{course_id}/publish", headers=headers)
    assert pub_resp.status_code == 200

    # Verify course appears in learner catalogue after publish
    learner_headers = {"Authorization": f"Bearer {trainee_token}"}
    catalogue_resp = client.get("/api/learn/courses", headers=learner_headers)
    assert catalogue_resp.status_code == 200
    catalogue_ids = [c["id"] for c in catalogue_resp.json()["items"]]
    assert course_id in catalogue_ids

    # Archive
    archive_resp = client.post(f"/api/courses/{course_id}/archive", headers=headers)
    assert archive_resp.status_code == 200
    assert archive_resp.json()["status"] == "archived"

    # Course should no longer appear in learner catalogue
    catalogue_resp2 = client.get("/api/learn/courses", headers=learner_headers)
    assert catalogue_resp2.status_code == 200
    catalogue_ids2 = [c["id"] for c in catalogue_resp2.json()["items"]]
    assert course_id not in catalogue_ids2
