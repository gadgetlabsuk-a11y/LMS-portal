"""Unit tests for block validation."""
import pytest
from app.services.block_service import validate_block, validate_blocks, VALID_BLOCK_TYPES


def make_block(type_, props, col_start=1, col_span=12, row_start=1):
    return {
        "id": f"b_{type_}",
        "type": type_,
        "props": props,
        "layout": {"col_start": col_start, "col_span": col_span, "row_start": row_start, "row_span": 1},
    }


def test_valid_mcq_single():
    b = make_block("mcq_single", {
        "question": "Q?",
        "options": [{"id": "a", "text": "A", "correct": True}, {"id": "b", "text": "B", "correct": False}],
        "feedback": "", "points": 1,
    })
    validate_block(b)  # no exception


def test_invalid_mcq_single_two_correct():
    b = make_block("mcq_single", {
        "question": "Q?",
        "options": [{"id": "a", "text": "A", "correct": True}, {"id": "b", "text": "B", "correct": True}],
        "feedback": "", "points": 1,
    })
    with pytest.raises(ValueError, match="exactly 1"):
        validate_block(b)


def test_valid_mcq_multi():
    b = make_block("mcq_multi", {
        "question": "Q?",
        "options": [
            {"id": "a", "text": "A", "correct": True},
            {"id": "b", "text": "B", "correct": True},
            {"id": "c", "text": "C", "correct": False},
        ],
        "feedback": "", "points": 2,
    })
    validate_block(b)


def test_invalid_mcq_multi_no_correct():
    b = make_block("mcq_multi", {
        "question": "Q?",
        "options": [{"id": "a", "text": "A", "correct": False}],
        "feedback": "", "points": 1,
    })
    with pytest.raises(ValueError):
        validate_block(b)


def test_image_requires_alt():
    b = make_block("image", {"alt": "", "media_id": 1})
    with pytest.raises(ValueError, match="alt"):
        validate_block(b)


def test_image_valid_with_alt():
    b = make_block("image", {"alt": "A cat", "media_id": 1})
    validate_block(b)


def test_audio_requires_transcript():
    b = make_block("audio", {"transcript": "", "controls": True})
    with pytest.raises(ValueError, match="transcript"):
        validate_block(b)


def test_tf_requires_boolean():
    b = make_block("tf", {"question": "Q?", "correct_answer": "true", "feedback": ""})
    with pytest.raises(ValueError):
        validate_block(b)


def test_tf_valid():
    b = make_block("tf", {"question": "Q?", "correct_answer": True, "feedback": ""})
    validate_block(b)


def test_unknown_block_type():
    b = make_block("unknown_type", {})
    with pytest.raises(ValueError, match="Unknown"):
        validate_block(b)


def test_layout_overlap_detected():
    b1 = make_block("heading", {"text": "H", "level": 2}, col_start=1, col_span=6, row_start=1)
    b2 = make_block("paragraph", {"text": "P"}, col_start=4, col_span=6, row_start=1)
    b1["id"] = "b_1"
    b2["id"] = "b_2"
    with pytest.raises(ValueError, match="overlap"):
        validate_blocks([b1, b2])


def test_no_overlap():
    b1 = make_block("heading", {"text": "H", "level": 2}, col_start=1, col_span=6, row_start=1)
    b2 = make_block("paragraph", {"text": "P"}, col_start=7, col_span=6, row_start=1)
    b1["id"] = "b_1"
    b2["id"] = "b_2"
    validate_blocks([b1, b2])  # no exception
