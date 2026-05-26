import pytest
from fastapi.testclient import TestClient
from main import app
from models import Course, CourseStatus, Module, Video, Slide, Block, Quiz, Question, Enrollment

client = TestClient(app)


def _published_course_with_content(db, owner_id):
    c = Course(title="Player Course", creator_id=owner_id, status=CourseStatus.PUBLISHED)
    db.add(c); db.flush()
    m = Module(course_id=c.id, title="M1", order_index=0); db.add(m); db.flush()
    v = Video(module_id=m.id, title="V1", order_index=0); db.add(v); db.flush()
    s = Slide(video_id=v.id, order_index=0); db.add(s); db.flush()
    db.add(Block(slide_id=s.id, order_index=0, type="heading", content={"html": "<h1>Hi</h1>"}))
    quiz = Quiz(video_id=v.id, title="Q", pass_rate=50, attempts_allowed=2); db.add(quiz); db.flush()
    db.add(Question(quiz_id=quiz.id, order_index=0, type="mcq_single", prompt="2+2?",
                    options=["3", "4"], correct_answer=1, points=1))
    db.commit()
    return c, v, quiz


def test_player_requires_enrollment(db, trainee_user, trainee_token):
    c, v, quiz = _published_course_with_content(db, trainee_user.id)
    r = client.get(f"/api/learn/courses/{c.id}/player",
                   headers={"Authorization": f"Bearer {trainee_token}"})
    assert r.status_code == 403


def test_player_tree_strips_answers(db, trainee_user, trainee_token):
    c, v, quiz = _published_course_with_content(db, trainee_user.id)
    db.add(Enrollment(user_id=trainee_user.id, course_id=c.id)); db.commit()
    r = client.get(f"/api/learn/courses/{c.id}/player",
                   headers={"Authorization": f"Bearer {trainee_token}"})
    assert r.status_code == 200
    body = r.json()
    q = body["modules"][0]["videos"][0]["quizzes"][0]["questions"][0]
    assert "correct_answer" not in q and "explanation" not in q
    assert q["options"] == ["3", "4"]
    assert body["progress"] == 0


def test_progress_updates_and_completes(db, trainee_user, trainee_token):
    c, v, quiz = _published_course_with_content(db, trainee_user.id)
    db.add(Enrollment(user_id=trainee_user.id, course_id=c.id)); db.commit()
    h = {"Authorization": f"Bearer {trainee_token}"}
    s_id = v.slides[0].id
    r = client.post(f"/api/learn/courses/{c.id}/progress", json={"slide_id": s_id}, headers=h)
    assert r.status_code == 200
    body = r.json()
    assert body["progress"] == 100 and body["completed"] is True  # only 1 slide -> done


def test_quiz_get_hides_answers(db, trainee_user, trainee_token):
    c, v, quiz = _published_course_with_content(db, trainee_user.id)
    db.add(Enrollment(user_id=trainee_user.id, course_id=c.id)); db.commit()
    r = client.get(f"/api/learn/quizzes/{quiz.id}", headers={"Authorization": f"Bearer {trainee_token}"})
    assert r.status_code == 200
    assert "correct_answer" not in r.json()["questions"][0]
    assert r.json()["attempts_remaining"] == 2


def test_quiz_submit_scores_and_limits(db, trainee_user, trainee_token):
    c, v, quiz = _published_course_with_content(db, trainee_user.id)
    db.add(Enrollment(user_id=trainee_user.id, course_id=c.id)); db.commit()
    h = {"Authorization": f"Bearer {trainee_token}"}
    qid = quiz.questions[0].id
    r = client.post(f"/api/learn/quizzes/{quiz.id}/attempt", json={"answers": {str(qid): 1}}, headers=h)
    assert r.status_code == 200
    assert r.json()["score"] == 100 and r.json()["passed"] is True
    # second wrong attempt
    client.post(f"/api/learn/quizzes/{quiz.id}/attempt", json={"answers": {str(qid): 0}}, headers=h)
    # third should 409 (attempts_allowed=2)
    r3 = client.post(f"/api/learn/quizzes/{quiz.id}/attempt", json={"answers": {str(qid): 1}}, headers=h)
    assert r3.status_code == 409
