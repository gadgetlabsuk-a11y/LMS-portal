import pytest

@pytest.fixture(autouse=True)
def reset_sse_state():
    from sse_starlette.sse import AppStatus
    AppStatus.should_exit_event = None
    yield


def test_pdf_extraction_pymupdf():
    """AI-04: PyMuPDF extracts text from PDF bytes (not raw UTF-8 decode)."""
    pytest.fail("Not implemented — AI-04 stub")


def test_docx_extraction_bytesio():
    """AI-04: DOCX extraction uses io.BytesIO(file_bytes), not raw bytes."""
    pytest.fail("Not implemented — AI-04 stub")


def test_outline_from_document():
    """AI-03: POST /api/slides/{id}/ai/generate-outline accepts document_url in request body."""
    pytest.fail("Not implemented — AI-03 stub")


def test_sse_stops_on_disconnect():
    """AI-05: SSE generator yields no tokens after is_disconnected returns True (already implemented — verify)."""
    pytest.fail("Not implemented — AI-05 verify stub")


def test_tone_preset_in_prompt():
    """AI-07: ai_tone_preset from course is included in SSE generation prompt."""
    pytest.fail("Not implemented — AI-07 stub")
