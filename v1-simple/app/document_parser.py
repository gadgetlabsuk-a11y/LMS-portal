"""Extract text content from uploaded PDF and DOCX files."""

import logging
import tempfile
import os

logger = logging.getLogger(__name__)


async def extract_text(file_bytes: bytes, filename: str) -> str:
    """Extract plain text from a PDF or DOCX file."""
    ext = os.path.splitext(filename)[1].lower()

    if ext == ".pdf":
        return _extract_pdf(file_bytes)
    elif ext in (".docx", ".doc"):
        return _extract_docx(file_bytes)
    else:
        raise ValueError(f"Unsupported file type: {ext}. Please upload a PDF or DOCX file.")


def _extract_pdf(file_bytes: bytes) -> str:
    import fitz  # PyMuPDF

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name

    try:
        doc = fitz.open(tmp_path)
        pages = []
        for page in doc:
            pages.append(page.get_text())
        doc.close()
        text = "\n\n".join(pages)
        logger.info("PDF extracted", extra={"pages": len(pages), "chars": len(text)})
        return text
    finally:
        os.unlink(tmp_path)


def _extract_docx(file_bytes: bytes) -> str:
    from docx import Document
    import io

    doc = Document(io.BytesIO(file_bytes))
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    text = "\n\n".join(paragraphs)
    logger.info("DOCX extracted", extra={"paragraphs": len(paragraphs), "chars": len(text)})
    return text
