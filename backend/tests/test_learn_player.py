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
