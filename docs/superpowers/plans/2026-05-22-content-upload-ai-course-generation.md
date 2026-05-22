# Generate Course from Uploaded Content — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let a creator upload multiple `.pptx/.docx/.pdf` files and have AI generate a full relational course (Module → Video → Slide → Block) via an outline-first, review-then-fill wizard.

**Architecture:** Two AI phases. Phase 1 extracts+merges file text into a capped corpus and asks Claude for a reviewable outline (validated JSON, one retry). After the creator edits/confirms, Phase 2a persists the Draft course + per-file source text + Module/Video/Slide stubs. Phase 2b fills each video's slides (Blocks + narration) from the stored corpus, streamed per-slide. All endpoints are creator-only and reuse existing `DocumentService`, `ClaudeService`, `useSSEStream`, and the slide/block model.

**Tech Stack:** FastAPI, SQLAlchemy, Alembic (SQLite), `sse-starlette`, `python-pptx`/`python-docx`/`pymupdf`, Anthropic `claude-sonnet-4-6` via httpx; React 18 + TypeScript + Vite + Tailwind + zustand; pytest + vitest/RTL.

**Spec:** `docs/superpowers/specs/2026-05-22-content-upload-ai-course-generation-design.md`

---

## File Structure

**Backend (create):**
- `backend/alembic/versions/007_course_source_documents.py` — migration for the new table.
- `backend/routers/content_generation.py` — the 3 endpoints (no router prefix; full `/api/...` paths, mirroring `routers/slides.py`).
- `backend/tests/test_content_generation.py` — endpoint + persistence tests.
- `backend/tests/test_document_corpus.py` — `DocumentService.build_corpus` tests.
- `backend/tests/test_claude_outline.py` — `ClaudeService` outline/blocks tests (Claude mocked).

**Backend (modify):**
- `backend/models/models.py` — add `CourseSourceDocument` model.
- `backend/models/__init__.py` — export `CourseSourceDocument`.
- `backend/services/document_service.py` — add `build_corpus(...)` static method.
- `backend/services/claude_service.py` — add outline/blocks Pydantic schemas, `_complete(...)`, `_extract_json(...)`, `generate_course_outline(...)`, `generate_slide_blocks(...)`.
- `backend/routers/courses.py` — remove legacy `generate` + `generate-from-document` endpoints and `CourseGenerateRequest`.
- `backend/main.py` — include the new router.

**Frontend (create):**
- `frontend/src/store/generateFromContentStore.ts` — wizard zustand store.
- `frontend/src/components/generate/OutlineReviewEditor.tsx` — editable outline tree.
- `frontend/src/components/generate/GenerateFromContentWizard.tsx` — the wizard.
- `frontend/src/components/generate/__tests__/OutlineReviewEditor.test.tsx`
- `frontend/src/components/generate/__tests__/GenerateFromContentWizard.test.tsx`

**Frontend (modify):**
- `frontend/src/services/api.ts` — add `postForm(path, formData)`.
- `frontend/src/pages/creator/CreatorCourseListPage.tsx` — add "Generate from content" button + mount wizard.

---

## Conventions for this plan

- Backend tests: from `backend/`, `source venv/bin/activate` then run the named file. **iCloud makes imports/pytest slow (3–6 min) — not hung.** Run the single target file, not the whole suite.
- Frontend tests: from `frontend/`, `npm run test -- <file>` (vitest).
- Claude is always mocked in tests; never hit the real API.
- Commit after each task.

---

## Task 1: `CourseSourceDocument` model

**Files:**
- Modify: `backend/models/models.py` (add class after `Block`, ~line 367)
- Modify: `backend/models/__init__.py`
- Test: `backend/tests/test_content_generation.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_content_generation.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && source venv/bin/activate && python -m pytest tests/test_content_generation.py::test_course_source_document_model_persists -v`
Expected: FAIL — `ImportError: cannot import name 'CourseSourceDocument'`

- [ ] **Step 3: Add the model**

In `backend/models/models.py`, immediately after the `Block` class (after its `__table_args__` line), add:

```python
class CourseSourceDocument(Base):
    """Extracted text from a file uploaded for AI course generation.

    Stores per-file source text used (a) as provenance ("generated from these
    files") and (b) as the grounding corpus for per-video slide-content generation.
    """
    __tablename__ = "course_source_documents"

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    filename = Column(String(500), nullable=False)
    content_type = Column(String(200), nullable=True)
    char_count = Column(Integer, nullable=False, server_default="0")
    extracted_text = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    course = relationship("Course")

    __table_args__ = (Index("idx_source_doc_course", "course_id"),)
```

- [ ] **Step 4: Export the model**

In `backend/models/__init__.py`, add `CourseSourceDocument` to BOTH the `from .models import (...)` tuple and the `__all__` list (place it next to `Block`).

- [ ] **Step 5: Run test to verify it passes**

Run: `cd backend && source venv/bin/activate && python -m pytest tests/test_content_generation.py::test_course_source_document_model_persists -v`
Expected: PASS (test schema is built via `Base.metadata.create_all`, so no migration needed for tests).

- [ ] **Step 6: Commit**

```bash
git add backend/models/models.py backend/models/__init__.py backend/tests/test_content_generation.py
git commit -m "feat(backend): add CourseSourceDocument model"
```

---

## Task 2: Alembic migration `007`

**Files:**
- Create: `backend/alembic/versions/007_course_source_documents.py`

> No automated test (migrations run against the real SQLite DB, which is slow on iCloud and wiped on redeploy). Verified by `alembic upgrade head` succeeding.

- [ ] **Step 1: Create the migration**

Create `backend/alembic/versions/007_course_source_documents.py`:

```python
"""Create course_source_documents table for AI content generation.

Revision ID: 007
Revises: 006
Create Date: 2026-05-22
"""
from alembic import op
import sqlalchemy as sa

revision = '007'
down_revision = '006'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'course_source_documents',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('course_id', sa.Integer(), sa.ForeignKey('courses.id', ondelete='CASCADE'), nullable=False),
        sa.Column('filename', sa.String(length=500), nullable=False),
        sa.Column('content_type', sa.String(length=200), nullable=True),
        sa.Column('char_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('extracted_text', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_source_doc_course', 'course_source_documents', ['course_id'])


def downgrade() -> None:
    op.drop_index('idx_source_doc_course', table_name='course_source_documents')
    op.drop_table('course_source_documents')
```

- [ ] **Step 2: Verify it applies (optional locally; required before deploy)**

Run: `cd backend && source venv/bin/activate && alembic upgrade head`
Expected: completes without error; `007` becomes head. (Slow on iCloud.)

- [ ] **Step 3: Commit**

```bash
git add backend/alembic/versions/007_course_source_documents.py
git commit -m "feat(backend): migration 007 course_source_documents"
```

---

## Task 3: `DocumentService.build_corpus`

**Files:**
- Modify: `backend/services/document_service.py`
- Test: `backend/tests/test_document_corpus.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_document_corpus.py`:

```python
from services.document_service import DocumentService


def test_build_corpus_joins_files_with_separator():
    corpus = DocumentService.build_corpus(["alpha", "beta"], max_chars=1000)
    assert "alpha" in corpus
    assert "beta" in corpus
    assert "---" in corpus  # separator between files


def test_build_corpus_truncates_to_max_chars():
    big = "x" * 100_000
    corpus = DocumentService.build_corpus([big, big], max_chars=1000)
    assert len(corpus) <= 1000


def test_build_corpus_allocates_share_per_file():
    a = "a" * 10_000
    b = "b" * 10_000
    corpus = DocumentService.build_corpus([a, b], max_chars=1000)
    # Both files represented (proportional share, neither dominates)
    assert "a" in corpus and "b" in corpus


def test_build_corpus_handles_empty_list():
    assert DocumentService.build_corpus([], max_chars=1000) == ""
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && source venv/bin/activate && python -m pytest tests/test_document_corpus.py -v`
Expected: FAIL — `AttributeError: ... has no attribute 'build_corpus'`

- [ ] **Step 3: Implement**

In `backend/services/document_service.py`, add this static method to the `DocumentService` class (after `extract_text`):

```python
    @staticmethod
    def build_corpus(texts: list[str], max_chars: int = 60000) -> str:
        """Merge per-file extracted texts into a single capped corpus.

        Each file gets an equal share of the budget so one large file can't
        crowd out the others; the joined result is hard-capped at max_chars.
        """
        non_empty = [t for t in texts if t and t.strip()]
        if not non_empty:
            return ""
        per_file = max(1, max_chars // len(non_empty))
        parts = [t[:per_file] for t in non_empty]
        corpus = "\n\n---\n\n".join(parts)
        return corpus[:max_chars]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && source venv/bin/activate && python -m pytest tests/test_document_corpus.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/services/document_service.py backend/tests/test_document_corpus.py
git commit -m "feat(backend): DocumentService.build_corpus (multi-file merge + cap)"
```

---

## Task 4: Outline schemas + `_complete` + `_extract_json` helpers

**Files:**
- Modify: `backend/services/claude_service.py`
- Test: `backend/tests/test_claude_outline.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_claude_outline.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && source venv/bin/activate && python -m pytest tests/test_claude_outline.py -v`
Expected: FAIL — `ImportError: cannot import name 'CourseOutline'`

- [ ] **Step 3: Implement schemas + helpers**

In `backend/services/claude_service.py`, add to the imports near the top:

```python
from pydantic import BaseModel
```

Add the module-level schemas and `_extract_json_obj` helper (after the `CLAUDE_MODEL = ...` constants, before `class ClaudeService`):

```python
class SlideOutline(BaseModel):
    title: str
    brief: str = ""


class VideoOutline(BaseModel):
    title: str
    description: str = ""
    slides: list[SlideOutline]


class ModuleOutline(BaseModel):
    title: str
    description: str = ""
    videos: list[VideoOutline]


class CourseOutline(BaseModel):
    title: str
    description: str = ""
    modules: list[ModuleOutline]


class GeneratedBlock(BaseModel):
    type: str
    content: dict


class SlideContent(BaseModel):
    blocks: list[GeneratedBlock]
    narration_script: str = ""


def _extract_json_obj(content: str) -> dict:
    """Parse a JSON object from a model response, tolerating code fences/prose."""
    import json as _json
    text = content.strip()
    if "```" in text:
        # take content between the first fence pair
        fenced = text.split("```")
        for chunk in fenced:
            chunk = chunk.strip()
            if chunk.startswith("json"):
                chunk = chunk[4:].strip()
            if chunk.startswith("{"):
                text = chunk
                break
    if not text.lstrip().startswith("{"):
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise ValueError("No JSON object found in model response")
        text = text[start:end + 1]
    try:
        return _json.loads(text)
    except _json.JSONDecodeError as e:
        raise ValueError(f"Malformed JSON in model response: {e}")
```

Add a non-streaming completion helper as a method on `ClaudeService` (after `_stream_text`):

```python
    async def _complete(self, prompt: str, max_tokens: int = 8192) -> str:
        """Non-streaming completion: returns the model's text content."""
        headers = {
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
            "x-api-key": self.api_key,
        }
        payload = {
            "model": self.model,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(
                CLAUDE_API_URL, json=payload, headers=headers, timeout=180.0,
            )
        if response.status_code != 200:
            logger.error(f"Claude API error: {response.status_code} - {response.text}")
            raise Exception(f"Claude API error: {response.status_code}")
        data = response.json()
        return data.get("content", [{}])[0].get("text", "")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && source venv/bin/activate && python -m pytest tests/test_claude_outline.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/services/claude_service.py backend/tests/test_claude_outline.py
git commit -m "feat(backend): outline/slide-content schemas + JSON + completion helpers"
```

---

## Task 5: `ClaudeService.generate_course_outline`

**Files:**
- Modify: `backend/services/claude_service.py`
- Test: `backend/tests/test_claude_outline.py`

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_claude_outline.py`:

```python
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
```

> Note: `@pytest.mark.asyncio` requires `pytest-asyncio` (already used by existing async tests). If a test is not collected, confirm `asyncio_mode = auto` in `backend/pytest.ini`/`pyproject.toml`; existing async ClaudeService tests rely on it.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && source venv/bin/activate && python -m pytest tests/test_claude_outline.py -k generate_course_outline -v`
Expected: FAIL — `AttributeError: 'ClaudeService' object has no attribute 'generate_course_outline'`

- [ ] **Step 3: Implement**

In `backend/services/claude_service.py`, add to `ClaudeService` (after `_complete`):

```python
    def _build_outline_prompt(
        self, corpus: str, n_modules: int, videos_per_module: int,
        slides_per_video: int, tone: str, difficulty: str,
    ) -> str:
        return (
            "You are designing an online course STRICTLY from the source material below. "
            "Use ONLY information present in the source; do not invent unrelated topics.\n\n"
            f"Produce EXACTLY {n_modules} modules. Each module has EXACTLY "
            f"{videos_per_module} videos. Each video has EXACTLY {slides_per_video} slides.\n"
            f"Difficulty: {difficulty}. Tone: {tone}.\n\n"
            "Return ONLY a JSON object (no markdown, no code fences) with this exact shape:\n"
            '{"title": str, "description": str, "modules": [{"title": str, '
            '"description": str, "videos": [{"title": str, "description": str, '
            '"slides": [{"title": str, "brief": str}]}]}]}\n'
            'Each slide "brief" is a one-sentence description of what the slide covers.\n\n'
            f"SOURCE MATERIAL:\n{corpus}"
        )

    async def generate_course_outline(
        self, corpus: str, n_modules: int, videos_per_module: int,
        slides_per_video: int, tone: str = "formal", difficulty: str = "intermediate",
    ) -> dict:
        """Generate a validated course outline from source corpus. Retries once on bad JSON."""
        prompt = self._build_outline_prompt(
            corpus, n_modules, videos_per_module, slides_per_video, tone, difficulty
        )
        last_err: Exception | None = None
        for attempt in range(2):
            raw = await self._complete(prompt, max_tokens=8192)
            try:
                obj = _extract_json_obj(raw)
                return CourseOutline.model_validate(obj).model_dump()
            except Exception as e:  # ValueError (parse) or ValidationError
                last_err = e
                logger.warning(f"Outline parse failed (attempt {attempt + 1}): {e}")
        raise ValueError(f"Could not produce a valid outline: {last_err}")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && source venv/bin/activate && python -m pytest tests/test_claude_outline.py -k generate_course_outline -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/services/claude_service.py backend/tests/test_claude_outline.py
git commit -m "feat(backend): ClaudeService.generate_course_outline (validated, retry-once)"
```

---

## Task 6: `ClaudeService.generate_slide_blocks`

**Files:**
- Modify: `backend/services/claude_service.py`
- Test: `backend/tests/test_claude_outline.py`

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_claude_outline.py`:

```python
@pytest.mark.asyncio
async def test_generate_slide_blocks_returns_validated_content():
    svc = ClaudeService()
    payload = json.dumps({
        "blocks": [
            {"type": "heading", "content": {"text": "Title"}},
            {"type": "text", "content": {"text": "Body"}},
        ],
        "narration_script": "Spoken words.",
    })
    with patch.object(svc, "_complete", return_value=payload):
        result = await svc.generate_slide_blocks(
            corpus="src", module_title="M", video_title="V",
            slide_title="S", brief="cover X",
        )
    assert result["narration_script"] == "Spoken words."
    assert result["blocks"][0]["type"] == "heading"
    # Only text-bearing block types allowed
    assert all(b["type"] in {"heading", "text", "quote", "code"} for b in result["blocks"])


@pytest.mark.asyncio
async def test_generate_slide_blocks_drops_unsupported_block_types():
    svc = ClaudeService()
    payload = json.dumps({
        "blocks": [
            {"type": "text", "content": {"text": "ok"}},
            {"type": "image", "content": {"url": "x"}},
        ],
        "narration_script": "n",
    })
    with patch.object(svc, "_complete", return_value=payload):
        result = await svc.generate_slide_blocks(
            corpus="src", module_title="M", video_title="V", slide_title="S", brief="b",
        )
    types = [b["type"] for b in result["blocks"]]
    assert "image" not in types
    assert "text" in types
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && source venv/bin/activate && python -m pytest tests/test_claude_outline.py -k generate_slide_blocks -v`
Expected: FAIL — `AttributeError: ... 'generate_slide_blocks'`

- [ ] **Step 3: Implement**

In `backend/services/claude_service.py`, add to `ClaudeService` (after `generate_course_outline`):

```python
    SUPPORTED_BLOCK_TYPES = {"heading", "text", "quote", "code"}

    async def generate_slide_blocks(
        self, corpus: str, module_title: str, video_title: str,
        slide_title: str, brief: str = "",
    ) -> dict:
        """Generate content blocks + narration for one slide, grounded in the corpus."""
        prompt = (
            "Generate the content of ONE course slide, STRICTLY from the source material. "
            "Use ONLY supported block types: heading, text, quote, code.\n"
            f"Module: {module_title}\nVideo: {video_title}\nSlide title: {slide_title}\n"
            f"What this slide should cover: {brief}\n\n"
            "Return ONLY a JSON object (no markdown) with this exact shape:\n"
            '{"blocks": [{"type": str, "content": {"text": str}}], "narration_script": str}\n'
            'Use 2-5 blocks. The narration_script is 2-4 spoken sentences.\n\n'
            f"SOURCE MATERIAL:\n{corpus}"
        )
        last_err: Exception | None = None
        for attempt in range(2):
            raw = await self._complete(prompt, max_tokens=2048)
            try:
                obj = _extract_json_obj(raw)
                content = SlideContent.model_validate(obj).model_dump()
                content["blocks"] = [
                    b for b in content["blocks"] if b["type"] in self.SUPPORTED_BLOCK_TYPES
                ]
                return content
            except Exception as e:
                last_err = e
                logger.warning(f"Slide-content parse failed (attempt {attempt + 1}): {e}")
        raise ValueError(f"Could not produce valid slide content: {last_err}")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && source venv/bin/activate && python -m pytest tests/test_claude_outline.py -k generate_slide_blocks -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/services/claude_service.py backend/tests/test_claude_outline.py
git commit -m "feat(backend): ClaudeService.generate_slide_blocks (corpus-grounded, filtered)"
```

---

## Task 7: New router + `outline-from-content` endpoint

**Files:**
- Create: `backend/routers/content_generation.py`
- Modify: `backend/main.py`
- Test: `backend/tests/test_content_generation.py`

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_content_generation.py`:

```python
import io
from unittest.mock import patch
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def _docx_like_bytes():
    # Minimal bytes; extraction is mocked, so content doesn't matter.
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && source venv/bin/activate && python -m pytest tests/test_content_generation.py -k outline_from_content -v`
Expected: FAIL — 404 (route not registered)

- [ ] **Step 3: Create the router with the endpoint**

Create `backend/routers/content_generation.py`:

```python
"""AI generation of a full relational course from uploaded documents.

No router prefix — full /api/... paths are declared per route (mirrors routers/slides.py).
"""
import logging
from typing import List

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from database import get_db
from models import User
from middleware.auth_middleware import require_creator
from services.claude_service import ClaudeService
from services.document_service import DocumentService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["content-generation"])

claude_service = ClaudeService()
document_service = DocumentService()

# Guardrails
MAX_FILES = 10
MAX_MODULES = 8
MAX_VIDEOS_PER_MODULE = 6
MAX_SLIDES_PER_VIDEO = 8
CORPUS_MAX_CHARS = 60000
ALLOWED_EXTS = (".pptx", ".docx", ".pdf")


def _clamp(value: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, value))


async def _extract_corpus(files: List[UploadFile]) -> str:
    """Extract + merge text from uploaded files into a capped corpus. Skips unreadable files."""
    texts: list[str] = []
    for f in files:
        name = (f.filename or "").lower()
        if not name.endswith(ALLOWED_EXTS):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported file type: {f.filename}. Allowed: .pptx, .docx, .pdf",
            )
        data = await f.read()
        try:
            texts.append(document_service.extract_text(data, f.filename))
        except Exception as e:
            logger.warning(f"Skipping unreadable file {f.filename}: {e}")
    corpus = DocumentService.build_corpus(texts, max_chars=CORPUS_MAX_CHARS)
    if not corpus.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No readable text could be extracted from the uploaded files.",
        )
    return corpus


@router.post("/api/courses/ai/outline-from-content")
async def outline_from_content(
    files: List[UploadFile] = File(...),
    modules: int = Form(...),
    videos_per_module: int = Form(...),
    slides_per_video: int = Form(...),
    tone: str = Form("formal"),
    difficulty: str = Form("intermediate"),
    current_user: User = Depends(require_creator),
):
    """Phase 1: extract corpus + return a validated, reviewable course outline (no persistence)."""
    if len(files) > MAX_FILES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Too many files. Maximum {MAX_FILES}.",
        )
    n_modules = _clamp(modules, 1, MAX_MODULES)
    vpm = _clamp(videos_per_module, 1, MAX_VIDEOS_PER_MODULE)
    spv = _clamp(slides_per_video, 1, MAX_SLIDES_PER_VIDEO)

    corpus = await _extract_corpus(files)
    try:
        outline = await claude_service.generate_course_outline(
            corpus=corpus, n_modules=n_modules, videos_per_module=vpm,
            slides_per_video=spv, tone=tone, difficulty=difficulty,
        )
    except Exception as e:
        logger.error(f"Outline generation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI could not generate an outline from this content. Try different files or settings.",
        )
    return outline
```

- [ ] **Step 4: Register the router**

In `backend/main.py`, find where routers are imported and included (e.g. `from routers import ... slides ...` and `app.include_router(slides.router)`). Add `content_generation` to the import and add:

```python
app.include_router(content_generation.router)
```

(Place it next to the other `app.include_router(...)` calls.)

- [ ] **Step 5: Run test to verify it passes**

Run: `cd backend && source venv/bin/activate && python -m pytest tests/test_content_generation.py -k outline_from_content -v`
Expected: PASS (3 tests)

- [ ] **Step 6: Commit**

```bash
git add backend/routers/content_generation.py backend/main.py backend/tests/test_content_generation.py
git commit -m "feat(backend): outline-from-content endpoint (Phase 1)"
```

---

## Task 8: `from-outline` endpoint (persist)

**Files:**
- Modify: `backend/routers/content_generation.py`
- Test: `backend/tests/test_content_generation.py`

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_content_generation.py`:

```python
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

    # response maps videos -> slide ids for the fill phase
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && source venv/bin/activate && python -m pytest tests/test_content_generation.py -k from_outline -v`
Expected: FAIL — 404 (route not registered)

- [ ] **Step 3: Implement**

In `backend/routers/content_generation.py`, add these imports to the existing import block:

```python
import json
from models import Course, CourseStatus, Module, Video, Slide, CourseSourceDocument
from services.claude_service import CourseOutline
```

Add the endpoint:

```python
@router.post("/api/courses/from-outline", status_code=status.HTTP_201_CREATED)
async def create_from_outline(
    outline: str = Form(...),
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_creator),
):
    """Phase 2a: persist the (edited) outline as a Draft course + stored source text."""
    try:
        parsed = CourseOutline.model_validate(json.loads(outline))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid outline: {e}",
        )

    course = Course(
        title=parsed.title or "Generated Course",
        description=parsed.description or "",
        creator_id=current_user.id,
        status=CourseStatus.DRAFT,
    )
    db.add(course)
    db.flush()  # assign course.id

    # Store source documents (re-extract from re-sent files; stateless server)
    for f in files:
        data = await f.read()
        try:
            text = document_service.extract_text(data, f.filename)
        except Exception as e:
            logger.warning(f"Skipping unreadable source file {f.filename}: {e}")
            text = ""
        db.add(CourseSourceDocument(
            course_id=course.id,
            filename=f.filename or "upload",
            content_type=f.content_type,
            char_count=len(text),
            extracted_text=text,
        ))

    video_map = []
    for mi, m in enumerate(parsed.modules):
        module = Module(course_id=course.id, order_index=mi, title=m.title,
                        description=m.description, status="draft")
        db.add(module)
        db.flush()
        for vi, v in enumerate(m.videos):
            video = Video(module_id=module.id, order_index=vi, title=v.title,
                          description=v.description, status="draft")
            db.add(video)
            db.flush()
            slide_ids = []
            for si, s in enumerate(v.slides):
                slide = Slide(video_id=video.id, order_index=si,
                              narration_script=s.brief or "", status="draft")
                db.add(slide)
                db.flush()
                slide_ids.append(slide.id)
            video_map.append({"video_id": video.id, "slide_ids": slide_ids})

    db.commit()
    db.refresh(course)
    return {"course_id": course.id, "videos": video_map}
```

> Note: `Slide` has no `title` column (titles live in the outline/blocks); the brief is stored in `narration_script` as a seed. Confirm against `models.py` Slide definition — it has `narration_script`, `order_index`, `status`, no `title`.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && source venv/bin/activate && python -m pytest tests/test_content_generation.py -k from_outline -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/routers/content_generation.py backend/tests/test_content_generation.py
git commit -m "feat(backend): from-outline endpoint persists relational course (Phase 2a)"
```

---

## Task 9: `generate-content` endpoint (Phase 2b, streamed per-slide)

**Files:**
- Modify: `backend/routers/content_generation.py`
- Test: `backend/tests/test_content_generation.py`

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_content_generation.py`:

```python
from models import Block


def _seed_video_with_slides(db, creator_user, n_slides=2):
    course = Course(title="C", creator_id=creator_user.id, status=CourseStatus.DRAFT)
    db.add(course); db.flush()
    db.add(CourseSourceDocument(course_id=course.id, filename="s.pdf",
           content_type="application/pdf", char_count=5, extracted_text="corpus"))
    module = Module(course_id=course.id, order_index=0, title="M", status="draft")
    db.add(module); db.flush()
    video = Video(module_id=module.id, order_index=0, title="V", status="draft")
    db.add(video); db.flush()
    for i in range(n_slides):
        db.add(Slide(video_id=video.id, order_index=i, narration_script=f"brief{i}", status="draft"))
    db.commit(); db.refresh(video)
    return course, video


def test_generate_content_fills_blocks_and_streams(creator_token, creator_user, db):
    course, video = _seed_video_with_slides(db, creator_user, n_slides=2)
    content = {"blocks": [{"type": "text", "content": {"text": "Body"}}], "narration_script": "n"}
    with patch("routers.content_generation.claude_service.generate_slide_blocks", return_value=content):
        res = client.post(
            f"/api/videos/{video.id}/ai/generate-content",
            headers={"Authorization": f"Bearer {creator_token}"},
        )
    assert res.status_code == 200
    assert "data:" in res.text  # one SSE event per slide

    blocks = db.query(Block).join(Slide, Block.slide_id == Slide.id).filter(
        Slide.video_id == video.id).all()
    assert len(blocks) == 2  # one text block per slide
    slides = db.query(Slide).filter(Slide.video_id == video.id).all()
    assert all(s.narration_script == "n" for s in slides)


def test_generate_content_404_for_missing_video(creator_token):
    res = client.post(
        "/api/videos/999999/ai/generate-content",
        headers={"Authorization": f"Bearer {creator_token}"},
    )
    assert res.status_code == 404
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && source venv/bin/activate && python -m pytest tests/test_content_generation.py -k generate_content -v`
Expected: FAIL — 404 (route not registered)

- [ ] **Step 3: Implement**

In `backend/routers/content_generation.py`, add imports:

```python
from fastapi import Request
from sse_starlette.sse import EventSourceResponse
```

Add a helper to load a video with ownership + its course corpus, then the endpoint:

```python
def _get_video_or_404(video_id: int, db: Session, current_user: User) -> Video:
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video not found")
    module = db.query(Module).filter(Module.id == video.module_id).first()
    course = db.query(Course).filter(Course.id == module.course_id).first() if module else None
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")
    if current_user.role.value != "admin" and course.creator_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return video


def _course_corpus(course_id: int, db: Session) -> str:
    docs = db.query(CourseSourceDocument).filter(
        CourseSourceDocument.course_id == course_id).all()
    return DocumentService.build_corpus([d.extracted_text or "" for d in docs],
                                        max_chars=CORPUS_MAX_CHARS)


@router.post("/api/videos/{video_id}/ai/generate-content")
async def generate_video_content(
    video_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_creator),
):
    """Phase 2b: fill each slide of a video with blocks + narration, streaming per-slide progress."""
    video = _get_video_or_404(video_id, db, current_user)
    module = db.query(Module).filter(Module.id == video.module_id).first()
    course = db.query(Course).filter(Course.id == module.course_id).first()
    corpus = _course_corpus(course.id, db)
    slides = db.query(Slide).filter(Slide.video_id == video.id).order_by(Slide.order_index).all()
    slide_ids = [s.id for s in slides]

    async def event_generator():
        for sid in slide_ids:
            if await request.is_disconnected():
                break
            slide = db.query(Slide).filter(Slide.id == sid).first()
            try:
                content = await claude_service.generate_slide_blocks(
                    corpus=corpus, module_title=module.title, video_title=video.title,
                    slide_title=slide.narration_script or "", brief=slide.narration_script or "",
                )
                for bi, b in enumerate(content["blocks"]):
                    db.add(Block(
                        slide_id=slide.id, order_index=bi, type=b["type"],
                        content=b.get("content") or {},
                        grid_position={"x": 0, "y": bi * 4, "w": 12, "h": 4},
                    ))
                if content.get("narration_script"):
                    slide.narration_script = content["narration_script"]
                slide.status = "draft"
                db.commit()
                yield {"data": "slide"}
            except Exception as e:
                db.rollback()
                logger.warning(f"Slide {sid} content generation failed: {e}")
                yield {"data": "error"}

    return EventSourceResponse(event_generator())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && source venv/bin/activate && python -m pytest tests/test_content_generation.py -k generate_content -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/routers/content_generation.py backend/tests/test_content_generation.py
git commit -m "feat(backend): generate-content endpoint fills video slides (Phase 2b, SSE)"
```

---

## Task 10: Remove broken legacy course-generation endpoints

**Files:**
- Modify: `backend/routers/courses.py`
- Test: `backend/tests/test_content_generation.py`

> These two endpoints write to the dropped `Course.content` column and are dead. No frontend uses them. Removing them prevents confusion and 500s.

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_content_generation.py`:

```python
def test_legacy_generate_endpoints_removed(creator_token):
    r1 = client.post("/api/courses/generate", json={"topic": "x"},
                     headers={"Authorization": f"Bearer {creator_token}"})
    r2 = client.post("/api/courses/generate-from-document",
                     files=[("file", ("a.pdf", io.BytesIO(b"x"), "application/pdf"))],
                     headers={"Authorization": f"Bearer {creator_token}"})
    assert r1.status_code == 404
    assert r2.status_code == 404
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && source venv/bin/activate && python -m pytest tests/test_content_generation.py -k legacy_generate -v`
Expected: FAIL — endpoints still return 200/400/500, not 404.

- [ ] **Step 3: Remove the endpoints + model**

In `backend/routers/courses.py`:
1. Delete the `@router.post("/generate-from-document")` function `generate_course_from_document` (the multipart one, ~line 742) in full.
2. Delete the `@router.post("/generate")` function `generate_course` (~line 874) in full.
3. Delete the `class CourseGenerateRequest(BaseModel):` block (~lines 59-70).

Then check for stragglers:

Run: `cd backend && grep -n "CourseGenerateRequest\|generate_course_from_document\|generate_from_document" routers/courses.py`
Expected: no matches. (If `File`/`Form`/`UploadFile` imports are now unused, leave them — `upload_video_clip` still uses `UploadFile`/`File`.)

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && source venv/bin/activate && python -m pytest tests/test_content_generation.py -k legacy_generate -v`
Expected: PASS

Also confirm no other test referenced these endpoints:

Run: `cd backend && grep -rn "generate-from-document\|/courses/generate\b\|CourseGenerateRequest" tests/`
Expected: only matches are in `test_content_generation.py`. If another test file references them, update/remove those assertions.

- [ ] **Step 5: Commit**

```bash
git add backend/routers/courses.py backend/tests/test_content_generation.py
git commit -m "refactor(backend): remove dead Course.content course-generation endpoints"
```

---

## Task 11: Frontend `api.postForm` (multipart helper)

**Files:**
- Modify: `frontend/src/services/api.ts`
- Test: `frontend/src/services/__tests__/api.postForm.test.ts`

- [ ] **Step 1: Write the failing test**

Create `frontend/src/services/__tests__/api.postForm.test.ts`:

```typescript
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { api } from '../api'

describe('api.postForm', () => {
  beforeEach(() => {
    localStorage.setItem('token', 'tok123')
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, status: 200 }))
  })
  afterEach(() => {
    vi.unstubAllGlobals()
    localStorage.clear()
  })

  it('posts FormData with auth header and no JSON content-type', async () => {
    const fd = new FormData()
    fd.append('x', 'y')
    await api.postForm('/courses/from-outline', fd)
    const [url, init] = (fetch as unknown as ReturnType<typeof vi.fn>).mock.calls[0]
    expect(url).toContain('/api/courses/from-outline')
    expect(init.method).toBe('POST')
    expect(init.body).toBe(fd)
    expect(init.headers.Authorization).toBe('Bearer tok123')
    // Must NOT set Content-Type (browser sets multipart boundary)
    expect(init.headers['Content-Type']).toBeUndefined()
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npm run test -- src/services/__tests__/api.postForm.test.ts`
Expected: FAIL — `api.postForm is not a function`

- [ ] **Step 3: Implement**

In `frontend/src/services/api.ts`, add a `postForm` method inside the `api` object (after `post`):

```typescript
  postForm: async (path: string, formData: FormData, options: RequestInit = {}): Promise<Response> => {
    const token = localStorage.getItem('token')
    const res = await fetch(`${API_BASE}/api${path}`, {
      method: 'POST',
      ...options,
      headers: {
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...((options.headers as Record<string, string>) ?? {}),
      },
      body: formData,
    })
    if (res.status === 401) handle401()
    return res
  },
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npm run test -- src/services/__tests__/api.postForm.test.ts`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/services/api.ts frontend/src/services/__tests__/api.postForm.test.ts
git commit -m "feat(frontend): api.postForm multipart helper"
```

---

## Task 12: Wizard zustand store

**Files:**
- Create: `frontend/src/store/generateFromContentStore.ts`
- Test: `frontend/src/store/__tests__/generateFromContentStore.test.ts`

- [ ] **Step 1: Write the failing test**

Create `frontend/src/store/__tests__/generateFromContentStore.test.ts`:

```typescript
import { describe, it, expect, beforeEach } from 'vitest'
import { useGenerateStore, type OutlineModule } from '../generateFromContentStore'

const sampleOutline: OutlineModule[] = [
  { title: 'M1', description: '', videos: [
    { title: 'V1', description: '', slides: [{ title: 'S1', brief: 'b' }] },
  ]},
]

describe('generateFromContentStore', () => {
  beforeEach(() => {
    useGenerateStore.getState().reset()
  })

  it('starts at step "upload" with no files', () => {
    const s = useGenerateStore.getState()
    expect(s.step).toBe('upload')
    expect(s.files).toEqual([])
  })

  it('setFiles + setSettings update state', () => {
    const f = new File(['x'], 'a.pdf', { type: 'application/pdf' })
    useGenerateStore.getState().setFiles([f])
    useGenerateStore.getState().setSettings({ modules: 3 })
    expect(useGenerateStore.getState().files).toHaveLength(1)
    expect(useGenerateStore.getState().settings.modules).toBe(3)
  })

  it('removeModule/removeVideo/removeSlide edit the outline', () => {
    const st = useGenerateStore.getState()
    st.setOutline(JSON.parse(JSON.stringify(sampleOutline)))
    st.removeSlide(0, 0, 0)
    expect(useGenerateStore.getState().outline[0].videos[0].slides).toHaveLength(0)
    st.removeVideo(0, 0)
    expect(useGenerateStore.getState().outline[0].videos).toHaveLength(0)
    st.removeModule(0)
    expect(useGenerateStore.getState().outline).toHaveLength(0)
  })

  it('renameSlide updates a slide title', () => {
    const st = useGenerateStore.getState()
    st.setOutline(JSON.parse(JSON.stringify(sampleOutline)))
    st.renameSlide(0, 0, 0, 'New Title')
    expect(useGenerateStore.getState().outline[0].videos[0].slides[0].title).toBe('New Title')
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npm run test -- src/store/__tests__/generateFromContentStore.test.ts`
Expected: FAIL — cannot resolve `../generateFromContentStore`

- [ ] **Step 3: Implement**

Create `frontend/src/store/generateFromContentStore.ts`:

```typescript
import { create } from 'zustand'

export interface OutlineSlide { title: string; brief: string }
export interface OutlineVideo { title: string; description: string; slides: OutlineSlide[] }
export interface OutlineModule { title: string; description: string; videos: OutlineVideo[] }

export type WizardStep = 'upload' | 'settings' | 'generating' | 'review' | 'creating' | 'filling' | 'done'

export interface GenSettings {
  modules: number
  videos_per_module: number
  slides_per_video: number
  tone: string
  difficulty: string
}

interface GenerateState {
  step: WizardStep
  files: File[]
  settings: GenSettings
  outline: OutlineModule[]
  courseTitle: string
  courseDescription: string
  error: string | null
  setStep: (s: WizardStep) => void
  setFiles: (f: File[]) => void
  setSettings: (patch: Partial<GenSettings>) => void
  setOutline: (o: OutlineModule[]) => void
  setCourseMeta: (title: string, description: string) => void
  setError: (e: string | null) => void
  removeModule: (mi: number) => void
  removeVideo: (mi: number, vi: number) => void
  removeSlide: (mi: number, vi: number, si: number) => void
  renameModule: (mi: number, title: string) => void
  renameVideo: (mi: number, vi: number, title: string) => void
  renameSlide: (mi: number, vi: number, si: number, title: string) => void
  reset: () => void
}

const DEFAULT_SETTINGS: GenSettings = {
  modules: 3, videos_per_module: 2, slides_per_video: 4,
  tone: 'formal', difficulty: 'intermediate',
}

export const useGenerateStore = create<GenerateState>((set) => ({
  step: 'upload',
  files: [],
  settings: { ...DEFAULT_SETTINGS },
  outline: [],
  courseTitle: '',
  courseDescription: '',
  error: null,
  setStep: (step) => set({ step }),
  setFiles: (files) => set({ files }),
  setSettings: (patch) => set((s) => ({ settings: { ...s.settings, ...patch } })),
  setOutline: (outline) => set({ outline }),
  setCourseMeta: (courseTitle, courseDescription) => set({ courseTitle, courseDescription }),
  setError: (error) => set({ error }),
  removeModule: (mi) => set((s) => ({ outline: s.outline.filter((_, i) => i !== mi) })),
  removeVideo: (mi, vi) => set((s) => ({
    outline: s.outline.map((m, i) =>
      i === mi ? { ...m, videos: m.videos.filter((_, j) => j !== vi) } : m),
  })),
  removeSlide: (mi, vi, si) => set((s) => ({
    outline: s.outline.map((m, i) => i === mi ? {
      ...m, videos: m.videos.map((v, j) => j === vi ?
        { ...v, slides: v.slides.filter((_, k) => k !== si) } : v),
    } : m),
  })),
  renameModule: (mi, title) => set((s) => ({
    outline: s.outline.map((m, i) => i === mi ? { ...m, title } : m),
  })),
  renameVideo: (mi, vi, title) => set((s) => ({
    outline: s.outline.map((m, i) => i === mi ? {
      ...m, videos: m.videos.map((v, j) => j === vi ? { ...v, title } : v),
    } : m),
  })),
  renameSlide: (mi, vi, si, title) => set((s) => ({
    outline: s.outline.map((m, i) => i === mi ? {
      ...m, videos: m.videos.map((v, j) => j === vi ? {
        ...v, slides: v.slides.map((sl, k) => k === si ? { ...sl, title } : sl),
      } : v),
    } : m),
  })),
  reset: () => set({
    step: 'upload', files: [], settings: { ...DEFAULT_SETTINGS },
    outline: [], courseTitle: '', courseDescription: '', error: null,
  }),
}))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npm run test -- src/store/__tests__/generateFromContentStore.test.ts`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add frontend/src/store/generateFromContentStore.ts frontend/src/store/__tests__/generateFromContentStore.test.ts
git commit -m "feat(frontend): generateFromContentStore wizard state"
```

---

## Task 13: `OutlineReviewEditor` component

**Files:**
- Create: `frontend/src/components/generate/OutlineReviewEditor.tsx`
- Test: `frontend/src/components/generate/__tests__/OutlineReviewEditor.test.tsx`

- [ ] **Step 1: Write the failing test**

Create `frontend/src/components/generate/__tests__/OutlineReviewEditor.test.tsx`:

```tsx
import { describe, it, expect, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { OutlineReviewEditor } from '../OutlineReviewEditor'
import { useGenerateStore, type OutlineModule } from '@/store/generateFromContentStore'

const outline: OutlineModule[] = [
  { title: 'Module One', description: '', videos: [
    { title: 'Video One', description: '', slides: [
      { title: 'Slide A', brief: 'b' }, { title: 'Slide B', brief: 'b' },
    ]},
  ]},
]

describe('OutlineReviewEditor', () => {
  beforeEach(() => {
    useGenerateStore.getState().reset()
    useGenerateStore.getState().setOutline(JSON.parse(JSON.stringify(outline)))
  })

  it('renders modules, videos and slides', () => {
    render(<OutlineReviewEditor />)
    expect(screen.getByDisplayValue('Module One')).toBeInTheDocument()
    expect(screen.getByDisplayValue('Video One')).toBeInTheDocument()
    expect(screen.getByDisplayValue('Slide A')).toBeInTheDocument()
  })

  it('removing a slide updates the store', async () => {
    render(<OutlineReviewEditor />)
    await userEvent.click(screen.getByTestId('remove-slide-0-0-0'))
    expect(useGenerateStore.getState().outline[0].videos[0].slides).toHaveLength(1)
  })

  it('editing a module title updates the store', async () => {
    render(<OutlineReviewEditor />)
    const input = screen.getByDisplayValue('Module One')
    await userEvent.clear(input)
    await userEvent.type(input, 'Renamed')
    expect(useGenerateStore.getState().outline[0].title).toBe('Renamed')
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npm run test -- src/components/generate/__tests__/OutlineReviewEditor.test.tsx`
Expected: FAIL — cannot resolve `../OutlineReviewEditor`

- [ ] **Step 3: Implement**

Create `frontend/src/components/generate/OutlineReviewEditor.tsx`:

```tsx
import { useGenerateStore } from '@/store/generateFromContentStore'

export function OutlineReviewEditor() {
  const outline = useGenerateStore((s) => s.outline)
  const { removeModule, removeVideo, removeSlide, renameModule, renameVideo, renameSlide } =
    useGenerateStore.getState()

  return (
    <div data-testid="outline-review-editor" className="flex flex-col gap-4">
      {outline.map((m, mi) => (
        <div key={mi} className="border border-gray-200 rounded-lg p-3">
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold text-brand">Module {mi + 1}</span>
            <input
              value={m.title}
              onChange={(e) => renameModule(mi, e.target.value)}
              className="flex-1 border rounded px-2 py-1 text-sm font-medium"
            />
            <button
              data-testid={`remove-module-${mi}`}
              onClick={() => removeModule(mi)}
              className="text-gray-400 hover:text-red-500 text-sm"
              aria-label={`Remove module ${mi + 1}`}
            >&#x2715;</button>
          </div>
          <div className="mt-2 ml-4 flex flex-col gap-2">
            {m.videos.map((v, vi) => (
              <div key={vi} className="border-l-2 border-gray-100 pl-3">
                <div className="flex items-center gap-2">
                  <span className="text-[11px] text-gray-500">Video {vi + 1}</span>
                  <input
                    value={v.title}
                    onChange={(e) => renameVideo(mi, vi, e.target.value)}
                    className="flex-1 border rounded px-2 py-1 text-sm"
                  />
                  <button
                    data-testid={`remove-video-${mi}-${vi}`}
                    onClick={() => removeVideo(mi, vi)}
                    className="text-gray-400 hover:text-red-500 text-sm"
                    aria-label={`Remove video ${vi + 1}`}
                  >&#x2715;</button>
                </div>
                <ul className="mt-1 ml-4 flex flex-col gap-1">
                  {v.slides.map((s, si) => (
                    <li key={si} className="flex items-center gap-2">
                      <span className="text-[11px] text-gray-400 w-5 text-right">{si + 1}.</span>
                      <input
                        value={s.title}
                        onChange={(e) => renameSlide(mi, vi, si, e.target.value)}
                        className="flex-1 border rounded px-2 py-1 text-xs"
                      />
                      <button
                        data-testid={`remove-slide-${mi}-${vi}-${si}`}
                        onClick={() => removeSlide(mi, vi, si)}
                        className="text-gray-400 hover:text-red-500 text-xs"
                        aria-label={`Remove slide ${si + 1}`}
                      >&#x2715;</button>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  )
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npm run test -- src/components/generate/__tests__/OutlineReviewEditor.test.tsx`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/generate/OutlineReviewEditor.tsx frontend/src/components/generate/__tests__/OutlineReviewEditor.test.tsx
git commit -m "feat(frontend): OutlineReviewEditor editable tree"
```

---

## Task 14: `GenerateFromContentWizard` component

**Files:**
- Create: `frontend/src/components/generate/GenerateFromContentWizard.tsx`
- Test: `frontend/src/components/generate/__tests__/GenerateFromContentWizard.test.tsx`

- [ ] **Step 1: Write the failing test**

Create `frontend/src/components/generate/__tests__/GenerateFromContentWizard.test.tsx`:

```tsx
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { GenerateFromContentWizard } from '../GenerateFromContentWizard'
import { useGenerateStore } from '@/store/generateFromContentStore'

vi.mock('@/services/api', () => ({
  api: {
    postForm: vi.fn(),
  },
  API_BASE: '',
}))

describe('GenerateFromContentWizard', () => {
  beforeEach(() => {
    useGenerateStore.getState().reset()
    vi.clearAllMocks()
  })

  it('does not render when closed', () => {
    render(<GenerateFromContentWizard open={false} onClose={() => {}} onCreated={() => {}} />)
    expect(screen.queryByTestId('generate-content-wizard')).not.toBeInTheDocument()
  })

  it('renders the upload step when open', () => {
    render(<GenerateFromContentWizard open onClose={() => {}} onCreated={() => {}} />)
    expect(screen.getByTestId('generate-content-wizard')).toBeInTheDocument()
    expect(screen.getByTestId('content-file-input')).toBeInTheDocument()
  })

  it('rejects an unsupported file type with a message', async () => {
    render(<GenerateFromContentWizard open onClose={() => {}} onCreated={() => {}} />)
    const input = screen.getByTestId('content-file-input') as HTMLInputElement
    const bad = new File(['x'], 'notes.txt', { type: 'text/plain' })
    await userEvent.upload(input, bad)
    expect(screen.getByTestId('upload-error')).toBeInTheDocument()
    expect(useGenerateStore.getState().files).toHaveLength(0)
  })

  it('accepts a .pdf and advances to settings', async () => {
    render(<GenerateFromContentWizard open onClose={() => {}} onCreated={() => {}} />)
    const input = screen.getByTestId('content-file-input') as HTMLInputElement
    const good = new File(['x'], 'deck.pdf', { type: 'application/pdf' })
    await userEvent.upload(input, good)
    expect(useGenerateStore.getState().files).toHaveLength(1)
    await userEvent.click(screen.getByTestId('to-settings-btn'))
    expect(useGenerateStore.getState().step).toBe('settings')
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npm run test -- src/components/generate/__tests__/GenerateFromContentWizard.test.tsx`
Expected: FAIL — cannot resolve `../GenerateFromContentWizard`

- [ ] **Step 3: Implement**

Create `frontend/src/components/generate/GenerateFromContentWizard.tsx`:

```tsx
import { useState } from 'react'
import { api, API_BASE } from '@/services/api'
import { useGenerateStore } from '@/store/generateFromContentStore'
import { OutlineReviewEditor } from './OutlineReviewEditor'

const ALLOWED = ['.pptx', '.docx', '.pdf']
const MAX_FILES = 10

interface Props {
  open: boolean
  onClose: () => void
  onCreated: (courseId: number) => void
}

export function GenerateFromContentWizard({ open, onClose, onCreated }: Props) {
  const s = useGenerateStore()
  const [uploadError, setUploadError] = useState<string | null>(null)
  const [progress, setProgress] = useState({ done: 0, total: 0 })

  if (!open) return null

  const handleFiles = (fileList: FileList | null) => {
    setUploadError(null)
    if (!fileList) return
    const incoming = Array.from(fileList)
    const bad = incoming.find(f => !ALLOWED.some(ext => f.name.toLowerCase().endsWith(ext)))
    if (bad) {
      setUploadError(`Unsupported file: ${bad.name}. Allowed: .pptx, .docx, .pdf`)
      return
    }
    const combined = [...s.files, ...incoming].slice(0, MAX_FILES)
    s.setFiles(combined)
  }

  const buildSettingsForm = (): FormData => {
    const fd = new FormData()
    s.files.forEach(f => fd.append('files', f))
    fd.append('modules', String(s.settings.modules))
    fd.append('videos_per_module', String(s.settings.videos_per_module))
    fd.append('slides_per_video', String(s.settings.slides_per_video))
    fd.append('tone', s.settings.tone)
    fd.append('difficulty', s.settings.difficulty)
    return fd
  }

  const handleGenerateOutline = async () => {
    s.setError(null)
    s.setStep('generating')
    try {
      const res = await api.postForm('/courses/ai/outline-from-content', buildSettingsForm())
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const outline = await res.json()
      s.setCourseMeta(outline.title || '', outline.description || '')
      s.setOutline(outline.modules || [])
      s.setStep('review')
    } catch {
      s.setError('Could not generate an outline. Try different files or settings.')
      s.setStep('settings')
    }
  }

  const fillVideoContent = async (videoId: number, slideCount: number) => {
    const token = localStorage.getItem('token')
    const res = await fetch(`${API_BASE}/api/videos/${videoId}/ai/generate-content`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
      body: JSON.stringify({}),
    })
    if (!res.body) { setProgress(p => ({ ...p, done: p.done + slideCount })); return }
    const reader = res.body.getReader()
    const decoder = new TextDecoder()
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      const chunk = decoder.decode(value)
      for (const line of chunk.split('\n')) {
        if (line.startsWith('data: ')) setProgress(p => ({ ...p, done: p.done + 1 }))
      }
    }
  }

  const handleCreate = async () => {
    s.setStep('creating')
    try {
      const fd = new FormData()
      s.files.forEach(f => fd.append('files', f))
      fd.append('outline', JSON.stringify({
        title: s.courseTitle, description: s.courseDescription, modules: s.outline,
      }))
      const res = await api.postForm('/courses/from-outline', fd)
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = await res.json()
      const totalSlides = data.videos.reduce(
        (n: number, v: { slide_ids: number[] }) => n + v.slide_ids.length, 0)
      setProgress({ done: 0, total: totalSlides })
      s.setStep('filling')
      for (const v of data.videos as { video_id: number; slide_ids: number[] }[]) {
        await fillVideoContent(v.video_id, v.slide_ids.length)
      }
      s.setStep('done')
      onCreated(data.course_id)
      s.reset()
    } catch {
      s.setError('Could not create the course. Please try again.')
      s.setStep('review')
    }
  }

  return (
    <div
      data-testid="generate-content-wizard"
      className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <div className="bg-white rounded-xl shadow-2xl w-[680px] max-h-[85vh] flex flex-col overflow-hidden">
        <div className="flex items-center justify-between px-6 py-4 border-b">
          <h2 className="text-lg font-semibold">Generate course from content</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-700 text-xl">&#x2715;</button>
        </div>

        <div className="flex-1 overflow-y-auto p-6">
          {s.error && <p data-testid="wizard-error" className="text-sm text-red-500 mb-3">{s.error}</p>}

          {s.step === 'upload' && (
            <div className="flex flex-col gap-3">
              <label className="block text-sm font-medium">Upload source files (.pptx, .docx, .pdf)</label>
              <input
                data-testid="content-file-input"
                type="file"
                multiple
                accept=".pptx,.docx,.pdf"
                onChange={(e) => handleFiles(e.target.files)}
                className="text-sm"
              />
              {uploadError && <p data-testid="upload-error" className="text-sm text-red-500">{uploadError}</p>}
              <ul className="text-sm text-gray-600 list-disc ml-5">
                {s.files.map((f, i) => <li key={i}>{f.name}</li>)}
              </ul>
              <p className="text-xs text-gray-400">This uses AI credits. Max {MAX_FILES} files.</p>
            </div>
          )}

          {s.step === 'settings' && (
            <div className="flex flex-col gap-3">
              <NumberField label="Modules" value={s.settings.modules} max={8}
                onChange={(v) => s.setSettings({ modules: v })} testid="set-modules" />
              <NumberField label="Videos per module" value={s.settings.videos_per_module} max={6}
                onChange={(v) => s.setSettings({ videos_per_module: v })} testid="set-videos" />
              <NumberField label="Slides per video" value={s.settings.slides_per_video} max={8}
                onChange={(v) => s.setSettings({ slides_per_video: v })} testid="set-slides" />
              <label className="text-sm font-medium">Tone</label>
              <select value={s.settings.tone} onChange={(e) => s.setSettings({ tone: e.target.value })}
                className="border rounded px-3 py-2 text-sm">
                <option value="formal">Formal</option>
                <option value="professional">Professional</option>
                <option value="casual">Casual</option>
              </select>
            </div>
          )}

          {s.step === 'generating' && (
            <div className="flex flex-col items-center gap-2 py-10">
              <div className="animate-spin w-8 h-8 border-4 border-brand border-t-transparent rounded-full" />
              <p className="text-sm text-gray-500">Generating outline…</p>
            </div>
          )}

          {s.step === 'review' && (
            <div className="flex flex-col gap-3">
              <p className="text-sm text-gray-600">Review and edit the proposed structure, then create.</p>
              <OutlineReviewEditor />
            </div>
          )}

          {(s.step === 'creating' || s.step === 'filling') && (
            <div className="flex flex-col items-center gap-3 py-10">
              <div className="animate-spin w-8 h-8 border-4 border-brand border-t-transparent rounded-full" />
              <p className="text-sm text-gray-500">
                {s.step === 'creating' ? 'Creating course…' : `Filling content… ${progress.done}/${progress.total} slides`}
              </p>
            </div>
          )}
        </div>

        <div className="flex items-center justify-between px-6 py-4 border-t bg-gray-50">
          <button onClick={onClose} className="px-4 py-2 text-sm border rounded text-gray-600">Cancel</button>
          <div className="flex gap-2">
            {s.step === 'upload' && (
              <button
                data-testid="to-settings-btn"
                disabled={s.files.length === 0}
                onClick={() => s.setStep('settings')}
                className="px-4 py-2 text-sm bg-brand text-white rounded disabled:opacity-40"
              >Next</button>
            )}
            {s.step === 'settings' && (
              <>
                <button onClick={() => s.setStep('upload')} className="px-4 py-2 text-sm border rounded">Back</button>
                <button
                  data-testid="generate-outline-btn"
                  onClick={handleGenerateOutline}
                  className="px-4 py-2 text-sm bg-brand text-white rounded"
                >Generate outline</button>
              </>
            )}
            {s.step === 'review' && (
              <button
                data-testid="create-course-btn"
                onClick={handleCreate}
                disabled={s.outline.length === 0}
                className="px-4 py-2 text-sm bg-green-600 text-white rounded disabled:opacity-40"
              >Create course</button>
            )}
            {s.step === 'done' && (
              <button onClick={onClose} className="px-4 py-2 text-sm bg-brand text-white rounded">Done</button>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

function NumberField({ label, value, max, onChange, testid }: {
  label: string; value: number; max: number; onChange: (v: number) => void; testid: string
}) {
  return (
    <div>
      <label className="block text-sm font-medium mb-1">{label} (max {max})</label>
      <input
        data-testid={testid}
        type="number" min={1} max={max} value={value}
        onChange={(e) => onChange(Math.min(max, Math.max(1, parseInt(e.target.value) || 1)))}
        className="border rounded px-3 py-2 text-sm w-32"
      />
    </div>
  )
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npm run test -- src/components/generate/__tests__/GenerateFromContentWizard.test.tsx`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/generate/GenerateFromContentWizard.tsx frontend/src/components/generate/__tests__/GenerateFromContentWizard.test.tsx
git commit -m "feat(frontend): GenerateFromContentWizard (upload→settings→outline→review→create→fill)"
```

---

## Task 15: Wire wizard into the creator course list

**Files:**
- Modify: `frontend/src/pages/creator/CreatorCourseListPage.tsx`
- Test: `frontend/src/pages/creator/__tests__/CreatorCourseListPage.generate.test.tsx`

- [ ] **Step 1: Write the failing test**

Create `frontend/src/pages/creator/__tests__/CreatorCourseListPage.generate.test.tsx`:

```tsx
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { CreatorCourseListPage } from '../CreatorCourseListPage'

vi.mock('@/context/AuthContext', () => ({ useAuth: () => ({ token: 't' }) }))
vi.mock('@/services/api', () => ({
  api: {
    get: vi.fn().mockResolvedValue({ json: async () => [] }),
    post: vi.fn().mockResolvedValue({ ok: true, json: async () => ({ id: 1 }) }),
    postForm: vi.fn(),
  },
  API_BASE: '',
}))

describe('CreatorCourseListPage — generate from content', () => {
  beforeEach(() => vi.clearAllMocks())

  it('opens the generate-from-content wizard from the toolbar', async () => {
    render(<MemoryRouter><CreatorCourseListPage /></MemoryRouter>)
    await userEvent.click(screen.getByTestId('generate-from-content-btn'))
    expect(screen.getByTestId('generate-content-wizard')).toBeInTheDocument()
  })
})
```

> If `CreatorCourseListPage` is a default export, adjust the import to `import CreatorCourseListPage from '../CreatorCourseListPage'`. Confirm against the file.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npm run test -- src/pages/creator/__tests__/CreatorCourseListPage.generate.test.tsx`
Expected: FAIL — no `generate-from-content-btn`

- [ ] **Step 3: Implement**

In `frontend/src/pages/creator/CreatorCourseListPage.tsx`:

1. Add the import at the top:
```tsx
import { GenerateFromContentWizard } from '@/components/generate/GenerateFromContentWizard'
```
2. Add wizard state alongside the existing modal state (`showIdentityModal`, etc.):
```tsx
const [showGenerateWizard, setShowGenerateWizard] = useState(false)
```
3. Next to the existing `<Button variant="primary" onClick={() => setShowIdentityModal(true)}>+ New Course</Button>`, add a second button:
```tsx
<Button
  variant="secondary"
  data-testid="generate-from-content-btn"
  onClick={() => setShowGenerateWizard(true)}
>
  Generate from content
</Button>
```
4. Where the other modals are mounted (near `<CourseIdentityModal ... />`), mount the wizard:
```tsx
<GenerateFromContentWizard
  open={showGenerateWizard}
  onClose={() => setShowGenerateWizard(false)}
  onCreated={(courseId) => {
    setShowGenerateWizard(false)
    navigate(`/creator/courses/${courseId}/builder`)
  }}
/>
```

> `navigate` already exists in this component (used by `handleStructureConfirmed`). If `Button` has no `secondary` variant, use `variant="primary"` or the existing outline/ghost variant — check `@/components/common/Button`.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npm run test -- src/pages/creator/__tests__/CreatorCourseListPage.generate.test.tsx`
Expected: PASS

- [ ] **Step 5: Verify the whole frontend still builds**

Run: `cd frontend && npm run build`
Expected: `tsc -b && vite build` succeed (no type errors).

- [ ] **Step 6: Commit**

```bash
git add frontend/src/pages/creator/CreatorCourseListPage.tsx frontend/src/pages/creator/__tests__/CreatorCourseListPage.generate.test.tsx
git commit -m "feat(frontend): add 'Generate from content' entry to creator course list"
```

---

## Task 16: Full verification + deploy notes

**Files:** none (verification only)

- [ ] **Step 1: Run the new backend tests together**

Run: `cd backend && source venv/bin/activate && python -m pytest tests/test_content_generation.py tests/test_document_corpus.py tests/test_claude_outline.py -v`
Expected: all PASS. (Slow on iCloud — be patient.)

- [ ] **Step 2: Run the new frontend tests together**

Run: `cd frontend && npm run test -- src/components/generate src/store/__tests__/generateFromContentStore.test.ts src/services/__tests__/api.postForm.test.ts src/pages/creator/__tests__/CreatorCourseListPage.generate.test.tsx`
Expected: all PASS.

- [ ] **Step 3: Frontend build**

Run: `cd frontend && npm run build`
Expected: success.

- [ ] **Step 4: Deploy checklist (manual — see memory `coolify-frontend-deploy`)**

- Push `main`.
- Run migration `alembic upgrade head` against the backend (the new table). Note: a backend Coolify redeploy **wipes SQLite** (no volume) — fresh DB will get the table from the migration on startup if migrations run at boot, otherwise run it in the backend container terminal.
- Redeploy backend AND frontend in Coolify (manual Redeploy; webhook is unreliable).
- Recreate the seeded admin if needed after the wipe.
- Smoke test: log in as creator → course list → "Generate from content" → upload a small `.pptx` → confirm outline → create → watch fill progress → land in the builder with populated slides.

- [ ] **Step 5: Commit (if any verification fixups were needed)**

```bash
git add -A
git commit -m "chore: verification fixups for content-to-course generation"
```

---

## Self-Review

**Spec coverage:**
- Multi-file upload merged corpus → Tasks 3, 7 (`build_corpus`, `_extract_corpus`). ✅
- Creator-set counts (modules/videos/slides) + caps → Tasks 7 (`_clamp`, MAX_*), 12, 14 (`NumberField`). ✅
- Outline-first validated JSON + one retry → Tasks 4, 5, 7. ✅
- Review & confirm gate → Tasks 13, 14 (`review` step). ✅
- Persist relational structure + source text, narration seeded from brief → Task 8. ✅
- Per-video streamed fill, per-video isolation, cancellable/skip → Task 9 (SSE, per-slide try/except) + Task 14 (`fillVideoContent`, progress). Cancel = closing wizard (AbortController not added — see note below). 
- New `course_source_documents` table + migration → Tasks 1, 2. ✅
- Three endpoints (validated outline / stateless persist via re-sent files / streamed fill) → Tasks 7, 8, 9. ✅
- `ClaudeService` additions (outline, slide blocks) using only text block types → Tasks 5, 6. ✅
- Remove legacy `generate-from-document`/`generate` → Task 10. ✅
- Frontend wizard, entry point, `api.postForm`, store → Tasks 11–15. ✅
- Error handling (unsupported/unreadable files, malformed outline, fill isolation) → Tasks 7, 8, 9, 14. ✅
- Tests for all of the above → every task is TDD. ✅
- Non-goals (no images/quiz/OCR/background-jobs) → respected; none implemented.

**Gap fix (cancel during fill):** the spec calls for a cancellable fill. Task 14's `fillVideoContent` uses a bare `fetch` without an `AbortController`. **During execution, add** an `AbortController` ref to the wizard, pass `signal` to the `fetch` in `fillVideoContent`, and abort it in `onClose`; closing the wizard mid-fill then stops further videos. This is a small addition to Task 14 — implement it there. (Backend already persists per-slide and tolerates client disconnect via `request.is_disconnected()`.)

**Placeholder scan:** no TBD/TODO; all code blocks complete; no "similar to Task N".

**Type consistency:** `OutlineModule/Video/Slide` shapes match between store (Task 12), editor (Task 13), wizard payload (Task 14), and backend `CourseOutline` (Task 4). Backend `SlideContent.blocks[].content` is a `dict`; frontend sends `outline` with `slides[].title`+`brief` — backend `from-outline` reads `s.brief` into `narration_script` and ignores slide `title` (titles are not persisted on `Slide`; they live only in the outline/review UI). This is intentional and consistent.
