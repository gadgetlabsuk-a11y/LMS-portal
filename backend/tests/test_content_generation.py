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
