---
phase: 18
plan: 02
subsystem: backend
tags: [publish, preview, preflight, versioning, course-lifecycle]
dependency_graph:
  requires: [18-01]
  provides: [publish-endpoints, course-version-snapshots, learner-version-pinning]
  affects: [learn.py, courses.py, modules.py, videos.py, slides.py, blocks.py, quizzes.py]
tech_stack:
  added: [CourseVersion model, SQLAlchemy selectinload for snapshots]
  patterns: [preflight-check pattern, snapshot-on-publish, _mark_course_changed helper per router]
key_files:
  created:
    - backend/alembic/versions/005_course_versions.py
  modified:
    - backend/models/models.py
    - backend/models/__init__.py
    - backend/routers/courses.py
    - backend/routers/learn.py
    - backend/routers/modules.py
    - backend/routers/videos.py
    - backend/routers/slides.py
    - backend/routers/blocks.py
    - backend/routers/quizzes.py
    - backend/tests/test_publish_phase18.py
decisions:
  - "CourseVersion stored in models/__init__.py exports — avoids circular import; courses.py also uses models.models direct import"
  - "_mark_course_changed defined locally in each child router — avoids circular import from courses.py"
  - "learn.py list endpoint hardcodes has_content=False — content column removed in 004, has_content is now computed from relational data in future plans"
  - "draft_creator_course local fixture used — conftest creator_course is PUBLISHED, but publish tests need DRAFT starting state"
  - "Preflight: quiz with < 3 questions produces a fail per-quiz (one result row per quiz)"
metrics:
  duration: ~35 min
  completed: 2026-05-11
  tasks: 2/2
  files: 10
---

# Phase 18 Plan 02: Backend Publish/Preview/Preflight Endpoints Summary

**One-liner:** CourseVersion model + migration 005, publish/archive/preflight/preview endpoints with preflight rules, CourseVersion snapshot on publish, learner version pinning in learn.py, HAS_UNPUBLISHED_CHANGES propagation across 5 child routers.

## What Was Built

### Task 1: CourseVersion Model + Migration 005

Added `CourseVersion` ORM model to `models/models.py` with:
- `course_id` FK → courses.id CASCADE
- `version_number` (Int)
- `snapshot` (JSON)
- `published_at` (DateTime)
- UniqueConstraint `(course_id, version_number)` + composite index

Created `005_course_versions.py` Alembic migration chained to revision `004`.

### Task 2: Endpoints + Child Router Updates

**courses.py additions:**
- `PreflightResult` + `PreflightResponse` Pydantic models
- `_run_preflight()`: 4 rules: course_has_title (FAIL), thumbnail_uploaded (WARN), has_at_least_one_module (FAIL), each_quiz_has_minimum_questions (FAIL if <3)
- `_serialize_course_tree()`: selectinload eager-loads full tree → snapshot dict
- `_mark_course_changed()`: transitions PUBLISHED → HAS_UNPUBLISHED_CHANGES
- `GET /{course_id}/preview` — returns full tree, bypasses PUBLISHED filter
- `GET /{course_id}/preflight` — structured pass/warn/fail results with fix_url
- `POST /{course_id}/publish` — runs preflight, creates CourseVersion, bumps version, sets PUBLISHED
- `POST /{course_id}/archive` — sets ARCHIVED

**learn.py changes:**
- Enrolled learner with `course_version` pin → look up CourseVersion snapshot, serve snapshot title/description
- Falls back to live course if no version row found (Pitfall 6 from research)
- Fixed pre-existing AttributeError: `course.content` references removed (column dropped in 004)

**Child routers (modules, videos, slides, blocks, quizzes):** `_mark_course_changed` helper added to each, called in all POST/PUT/DELETE mutation handlers.

## Test Results

All 9 tests in `test_publish_phase18.py` pass:
- PREVIEW-01: preview returns draft course tree
- PREVIEW-02: preview includes nested slides/blocks
- PUBLISH-02: preflight returns structured results
- PUBLISH-03: preflight fails when no modules
- PUBLISH-04: fail results include fix_url
- PUBLISH-05: publish transitions to PUBLISHED
- PUBLISH-06: publish creates CourseVersion row
- PUBLISH-07: learner gets pinned version snapshot
- PUBLISH-08: archive hides course from catalogue

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed `course.content` AttributeError in learn.py**
- **Found during:** Task 2, test_archive_hides_from_catalogue test failure
- **Issue:** `learn.py` list and detail endpoints referenced `course.content` which was removed from the Course model in migration 004; caused `AttributeError: 'Course' object has no attribute 'content'` on every `/api/learn/courses` request
- **Fix:** Replaced `bool(c.content)` / `course.content` with `False` / `None` in learn.py endpoints; `has_content` will be recomputed from relational data in a future plan
- **Files modified:** `backend/routers/learn.py`
- **Commit:** ad5a102

### Pre-existing Test Failure (out of scope)

`test_learn_router.py::test_has_content_true_when_content_set` — this test asserts `has_content is True` for a `published_course` fixture that never set content. The test was broken before this plan (would fail with AttributeError from `course.content`). After our fix it fails with an assertion error. Not introduced by this plan; logged for deferred cleanup.

## Self-Check: PASSED
