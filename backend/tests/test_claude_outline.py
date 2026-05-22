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


import json
from unittest.mock import patch


def _valid_outline_json(n_modules=2, vpm=2, spv=3):
    modules = []
    for m in range(n_modules):
        videos = []
        for v in range(vpm):
            slides = [{"title": f"S{s}", "brief": "b"} for s in range(spv)]
            videos.append({"title": f"V{v}", "description": "", "slides": slides})
        modules.append({"title": f"M{m}", "description": "", "videos": videos})
    return json.dumps({"title": "Course", "description": "D", "modules": modules})


@pytest.mark.asyncio
async def test_generate_course_outline_returns_validated_dict():
    svc = ClaudeService()
    with patch.object(svc, "_complete", return_value=_valid_outline_json()):
        result = await svc.generate_course_outline(
            corpus="some source text", n_modules=2, videos_per_module=2,
            slides_per_video=3, tone="formal", difficulty="intermediate",
        )
    assert result["title"] == "Course"
    assert len(result["modules"]) == 2
    assert len(result["modules"][0]["videos"]) == 2
    assert len(result["modules"][0]["videos"][0]["slides"]) == 3


@pytest.mark.asyncio
async def test_generate_course_outline_retries_once_on_bad_json():
    svc = ClaudeService()
    calls = {"n": 0}

    async def fake_complete(prompt, max_tokens=8192):
        calls["n"] += 1
        return "garbage" if calls["n"] == 1 else _valid_outline_json()

    with patch.object(svc, "_complete", side_effect=fake_complete):
        result = await svc.generate_course_outline(
            corpus="x", n_modules=2, videos_per_module=2, slides_per_video=3,
        )
    assert calls["n"] == 2
    assert result["title"] == "Course"


@pytest.mark.asyncio
async def test_generate_course_outline_raises_after_second_failure():
    svc = ClaudeService()
    with patch.object(svc, "_complete", return_value="still garbage"):
        with pytest.raises(ValueError):
            await svc.generate_course_outline(
                corpus="x", n_modules=1, videos_per_module=1, slides_per_video=1,
            )
