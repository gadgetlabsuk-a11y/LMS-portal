"""
Document extraction service for various file formats.
Handles extraction of text from docx, pptx, and pdf files.
"""

import logging
from typing import Optional
from docx import Document as DocxDocument
from pptx import Presentation

logger = logging.getLogger(__name__)


class DocumentService:
    """Service for extracting text from documents."""

    @staticmethod
    def extract_text(file_bytes: bytes, filename: str) -> str:
        """
        Extract text from document file bytes.

        Args:
            file_bytes: Raw file bytes
            filename: Original filename (used to determine file type)

        Returns:
            Extracted text content

        Raises:
            ValueError: If file type is not supported
        """
        filename_lower = filename.lower()

        if filename_lower.endswith(".docx"):
            return DocumentService._extract_docx(file_bytes)
        elif filename_lower.endswith(".pptx"):
            return DocumentService._extract_pptx(file_bytes)
        elif filename_lower.endswith(".pdf"):
            return DocumentService._extract_pdf(file_bytes)
        else:
            raise ValueError(
                f"Unsupported file type: {filename}. "
                "Supported types: .docx, .pptx, .pdf"
            )

    @staticmethod
    def _extract_docx(file_bytes: bytes) -> str:
        """
        Extract text from DOCX file.

        Args:
            file_bytes: Raw file bytes

        Returns:
            Extracted text with structure preserved
        """
        try:
            doc = DocxDocument(file_bytes)
            content_parts = []

            for para in doc.paragraphs:
                if para.text.strip():
                    content_parts.append(para.text)

            # Extract text from tables if present
            for table in doc.tables:
                table_text = []
                for row in table.rows:
                    row_text = [cell.text for cell in row.cells]
                    table_text.append(" | ".join(row_text))
                if table_text:
                    content_parts.append("\n".join(table_text))

            extracted_text = "\n".join(content_parts)
            logger.info(f"Extracted text from DOCX: {len(extracted_text)} characters")
            return extracted_text

        except Exception as e:
            logger.error(f"Error extracting DOCX: {str(e)}")
            raise ValueError(f"Failed to extract text from DOCX file: {str(e)}")

    @staticmethod
    def _extract_pptx(file_bytes: bytes) -> str:
        """
        Extract text from PPTX file (slide by slide, including notes).

        Args:
            file_bytes: Raw file bytes

        Returns:
            Extracted text organized by slide
        """
        try:
            presentation = Presentation(file_bytes)
            content_parts = []

            for slide_idx, slide in enumerate(presentation.slides, 1):
                content_parts.append(f"--- Slide {slide_idx} ---")

                # Extract text from shapes
                for shape in slide.shapes:
                    if hasattr(shape, "text") and shape.text.strip():
                        content_parts.append(shape.text)

                # Extract speaker notes if available
                if slide.has_notes_slide:
                    notes_text = slide.notes_slide.notes_text_frame.text.strip()
                    if notes_text:
                        content_parts.append(f"Notes: {notes_text}")

            extracted_text = "\n".join(content_parts)
            logger.info(f"Extracted text from PPTX: {len(extracted_text)} characters")
            return extracted_text

        except Exception as e:
            logger.error(f"Error extracting PPTX: {str(e)}")
            raise ValueError(f"Failed to extract text from PPTX file: {str(e)}")

    @staticmethod
    def _extract_pdf(file_bytes: bytes) -> str:
        """
        Extract text from PDF file using basic text decoding.

        Args:
            file_bytes: Raw file bytes

        Returns:
            Extracted text (best effort)

        Note:
            This is a simple implementation that works for text-based PDFs.
            For complex PDFs with images or scanned content, a more
            sophisticated approach would be needed.
        """
        try:
            # Attempt to decode PDF bytes as UTF-8
            text = file_bytes.decode("utf-8", errors="ignore")

            # Remove non-printable characters but keep line breaks and spaces
            cleaned_lines = []
            for line in text.split("\n"):
                # Keep only printable ASCII and common unicode characters
                cleaned = "".join(
                    c for c in line
                    if c.isprintable() or c.isspace()
                )
                if cleaned.strip():
                    cleaned_lines.append(cleaned)

            extracted_text = "\n".join(cleaned_lines)

            # If we got very little text, the PDF might be scanned/binary
            if len(extracted_text.strip()) < 100:
                logger.warning(
                    "PDF extraction produced minimal text - may be scanned or binary format"
                )

            logger.info(f"Extracted text from PDF: {len(extracted_text)} characters")
            return extracted_text

        except Exception as e:
            logger.error(f"Error extracting PDF: {str(e)}")
            raise ValueError(f"Failed to extract text from PDF file: {str(e)}")
