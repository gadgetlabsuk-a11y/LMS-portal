import pytest

@pytest.fixture(autouse=True)
def reset_sse_state():
    from sse_starlette.sse import AppStatus
    AppStatus.should_exit_event = None
    yield


def test_pdf_extraction_pymupdf():
    """AI-04: PyMuPDF extracts text from a real PDF — not raw UTF-8 decode."""
    import fitz
    from services.document_service import DocumentService
    # Create a minimal PDF with known text
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Hello PyMuPDF test content")
    pdf_bytes = doc.tobytes()
    doc.close()
    svc = DocumentService()
    result = svc._extract_pdf(pdf_bytes)
    assert "Hello PyMuPDF test content" in result


def test_docx_extraction_bytesio():
    """AI-04: DOCX extraction uses io.BytesIO, not raw bytes."""
    import io
    from docx import Document as DocxDocument
    from services.document_service import DocumentService
    # Create a minimal DOCX with known text
    docx_doc = DocxDocument()
    docx_doc.add_paragraph("Hello DOCX BytesIO test content")
    buf = io.BytesIO()
    docx_doc.save(buf)
    docx_bytes = buf.getvalue()
    svc = DocumentService()
    result = svc._extract_docx(docx_bytes)
    assert "Hello DOCX BytesIO test content" in result


def test_outline_from_document():
    """AI-03: POST /api/slides/{id}/ai/generate-outline accepts document_url in request body."""
    pytest.fail("Not implemented — AI-03 stub")


def test_sse_stops_on_disconnect():
    """AI-05: SSE generator yields no tokens after is_disconnected returns True (already implemented — verify)."""
    pytest.fail("Not implemented — AI-05 verify stub")


def test_tone_preset_in_prompt():
    """AI-07: ai_tone_preset from course is included in SSE generation prompt."""
    pytest.fail("Not implemented — AI-07 stub")
