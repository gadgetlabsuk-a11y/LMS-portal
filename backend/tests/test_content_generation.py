"""Tests for the AI 'generate course from uploaded content' feature."""
from models import CourseSourceDocument, Course, CourseStatus


def test_course_source_document_model_persists(db, creator_user):
    course = Course(title="Src Test", creator_id=creator_user.id, status=CourseStatus.DRAFT)
    db.add(course)
    db.commit()
    db.refresh(course)

    doc = CourseSourceDocument(
        course_id=course.id,
        filename="deck.pptx",
        content_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        char_count=42,
        extracted_text="hello world",
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    assert doc.id is not None
    assert doc.course_id == course.id
    assert doc.filename == "deck.pptx"
    assert doc.extracted_text == "hello world"


import io
from unittest.mock import patch
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def _docx_like_bytes():
    return b"PK\x03\x04 fake docx"


def test_outline_from_content_returns_validated_outline(creator_token):
    outline = {
        "title": "Generated", "description": "D",
        "modules": [{"title": "M1", "description": "", "videos": [
            {"title": "V1", "description": "", "slides": [{"title": "S1", "brief": "b"}]}
        ]}],
    }
    with patch("routers.content_generation.document_service.extract_text", return_value="source text"), \
         patch("routers.content_generation.claude_service.generate_course_outline", return_value=outline):
        res = client.post(
            "/api/courses/ai/outline-from-content",
            data={"modules": 1, "videos_per_module": 1, "slides_per_video": 1,
                  "tone": "formal", "difficulty": "intermediate"},
            files=[("files", ("a.docx", io.BytesIO(_docx_like_bytes()),
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"))],
            headers={"Authorization": f"Bearer {creator_token}"},
        )
    assert res.status_code == 200
    body = res.json()
    assert body["title"] == "Generated"
    assert body["modules"][0]["videos"][0]["slides"][0]["title"] == "S1"


def test_outline_from_content_rejects_unsupported_file(creator_token):
    res = client.post(
        "/api/courses/ai/outline-from-content",
        data={"modules": 1, "videos_per_module": 1, "slides_per_video": 1},
        files=[("files", ("a.txt", io.BytesIO(b"hello"), "text/plain"))],
        headers={"Authorization": f"Bearer {creator_token}"},
    )
    assert res.status_code == 400


def test_outline_from_content_requires_creator():
    res = client.post(
        "/api/courses/ai/outline-from-content",
        data={"modules": 1, "videos_per_module": 1, "slides_per_video": 1},
        files=[("files", ("a.pdf", io.BytesIO(b"x"), "application/pdf"))],
    )
    assert res.status_code in (401, 403)


import json as _json
from models import Course, Module, Video, Slide, CourseSourceDocument


def test_from_outline_persists_relational_structure(creator_token, db):
    outline = {
        "title": "Built Course", "description": "Desc",
        "modules": [
            {"title": "M1", "description": "m1", "videos": [
                {"title": "V1", "description": "v1", "slides": [
                    {"title": "S1", "brief": "brief1"},
                    {"title": "S2", "brief": "brief2"},
                ]},
            ]},
        ],
    }
    with patch("routers.content_generation.document_service.extract_text", return_value="src text"):
        res = client.post(
            "/api/courses/from-outline",
            data={"outline": _json.dumps(outline)},
            files=[("files", ("a.pdf", io.BytesIO(b"x"), "application/pdf"))],
            headers={"Authorization": f"Bearer {creator_token}"},
        )
    assert res.status_code == 201, res.text
    body = res.json()
    course_id = body["course_id"]

    course = db.query(Course).filter(Course.id == course_id).first()
    assert course is not None and course.title == "Built Course"
    assert course.status.value == "draft"

    modules = db.query(Module).filter(Module.course_id == course_id).all()
    assert len(modules) == 1
    videos = db.query(Video).filter(Video.module_id == modules[0].id).all()
    assert len(videos) == 1
    slides = db.query(Slide).filter(Slide.video_id == videos[0].id).order_by(Slide.order_index).all()
    assert len(slides) == 2
    assert slides[0].narration_script == "brief1"  # brief seeds narration

    srcs = db.query(CourseSourceDocument).filter(CourseSourceDocument.course_id == course_id).all()
    assert len(srcs) == 1 and srcs[0].extracted_text == "src text"

    assert body["videos"][0]["video_id"] == videos[0].id
    assert body["videos"][0]["slide_ids"] == [s.id for s in slides]


def test_from_outline_rejects_malformed_outline(creator_token):
    res = client.post(
        "/api/courses/from-outline",
        data={"outline": "{not json"},
        files=[("files", ("a.pdf", io.BytesIO(b"x"), "application/pdf"))],
        headers={"Authorization": f"Bearer {creator_token}"},
    )
    assert res.status_code == 400
