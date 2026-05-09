---
phase: 15
plan: 02
subsystem: backend
tags: [document-ingestion, ai-generation, pdf, docx, sse, pymupdf]
dependency_graph:
  requires: [15-01]
  provides: [AI-03, AI-04, AI-05]
  affects: [backend/services/document_service.py, backend/routers/slides.py]
tech_stack:
  added: [httpx (already in venv), fitz/PyMuPDF 1.26.0 (installed in 15-01)]
  patterns: [TDD RED-GREEN, PyMuPDF stream extraction, BytesIO DOCX wrapping, SSE document injection]
key_files:
  created: []
  modified:
    - backend/services/document_service.py
    - backend/routers/slides.py
    - backend/tests/test_ai_phase15.py
decisions:
  - "extract_text_from_file_sync(file_bytes, content_type) added to DocumentService — mirrors existing extract_text(file_bytes, filename) but uses MIME type for format detection; avoids filename dependency in the SSE endpoint"
  - "document_service instantiated as module-level singleton in slides.py (same pattern as claude_service) — enables patch('routers.slides.document_service.extract_text_from_file_sync') in tests"
  - "httpx.AsyncClient used for document_url fetch — already present in venv (FastAPI TestClient uses httpx); no new dependency"
  - "pre-existing test_learn_router.py::test_returns_only_published_courses failure confirmed unrelated (documented in 12-02 decisions)"
metrics:
  duration: ~15 min
  completed: "2026-05-09T21:51:28Z"
  tasks: 2/2
  files: 3
---

# Phase 15 Plan 02: Document Ingestion Pipeline Fix Summary

**One-liner:** Fixed broken PDF/DOCX extraction (PyMuPDF stream + BytesIO) and wired document_url parameter into the slide outline generation SSE endpoint.

## What Was Built

- **document_service.py — PDF fix:** Replaced raw UTF-8 decode with `fitz.open(stream=file_bytes, filetype="pdf")` + `page.get_text()` — correctly extracts text from real PDF structures
- **document_service.py — DOCX fix:** Changed `DocxDocument(file_bytes)` to `DocxDocument(io.BytesIO(file_bytes))` — resolves AttributeError: 'bytes' object has no attribute 'seek'
- **document_service.py — new method:** Added `extract_text_from_file_sync(file_bytes, content_type)` for MIME-type-based dispatch from the slides endpoint
- **slides.py — AiOutlineRequest:** Added `document_url: Optional[str] = None` field (AI-03)
- **slides.py — generate_outline endpoint:** Added async document fetch block — fetches document_url via httpx, extracts text, prepends as "Document content:\n..." in source_prompt
- **test_ai_phase15.py:** All 5 stubs turned GREEN with real implementations

## Tests

| Test | Requirement | Result |
|------|-------------|--------|
| test_pdf_extraction_pymupdf | AI-04 | PASSED |
| test_docx_extraction_bytesio | AI-04 | PASSED |
| test_outline_from_document | AI-03 | PASSED |
| test_sse_stops_on_disconnect | AI-05 | PASSED |
| test_tone_preset_in_prompt | AI-07 | PASSED |

Full suite: 57 passed, 1 pre-existing failure (test_learn_router — documented in 12-02 decisions, unrelated).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing functionality] Added extract_text_from_file_sync method to DocumentService**
- **Found during:** Task 2 — plan referenced `document_service.extract_text_from_file_sync(file_bytes, content_type)` but method did not exist
- **Fix:** Added `extract_text_from_file_sync(file_bytes, content_type)` to DocumentService with MIME-type dispatch (pdf/docx/pptx), falling back to PDF then DOCX for unknown types
- **Files modified:** backend/services/document_service.py
- **Commit:** 63a8698

**2. [Rule 3 - Blocking issue] Stale test_lms_tmp.db caused OperationalError on first test run**
- **Found during:** Task 1 verification
- **Fix:** Deleted stale `backend/test_lms_tmp.db` before running tests (documented pattern from 14-02 decisions)
- **Files modified:** none (file deleted)

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1 | 7ca1086 | feat(15-02): fix document_service.py — PyMuPDF PDF + BytesIO DOCX |
| 2 | 63a8698 | feat(15-02): wire document_url into generate-outline + turn all stubs GREEN |

## Self-Check: PASSED
