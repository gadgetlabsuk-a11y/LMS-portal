import pytest
from services.claude_service import (
    ClaudeService, CourseOutline, SlideContent, _extract_json_obj,
)


def test_extract_json_strips_code_fences():
    raw = '```json\n{"a": 1}\n```'
    assert _extract_json_obj(raw) == {"a": 1}


def test_extract_json_slices_when_unfenced():
    raw = 'Here is the JSON: {"a": 2} thanks!'
    assert _extract_json_obj(raw) == {"a": 2}


def test_extract_json_raises_on_garbage():
    with pytest.raises(ValueError):
        _extract_json_obj("no json here")


def test_course_outline_schema_validates():
    obj = {
        "title": "T", "description": "D",
        "modules": [
            {"title": "M1", "description": "", "videos": [
                {"title": "V1", "description": "", "slides": [
                    {"title": "S1", "brief": "b"}
                ]}
            ]}
        ],
    }
    parsed = CourseOutline.model_validate(obj)
    assert parsed.modules[0].videos[0].slides[0].title == "S1"


def test_slide_content_schema_validates():
    obj = {"blocks": [{"type": "text", "content": {"text": "hi"}}], "narration_script": "n"}
    parsed = SlideContent.model_validate(obj)
    assert parsed.blocks[0].type == "text"
