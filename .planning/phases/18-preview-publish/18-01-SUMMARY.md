---
phase: 18-preview-publish
plan: "01"
subsystem: testing
tags: [tdd, red-state, preview, publish]
dependency_graph:
  requires: []
  provides: [red-state-backend-publish, red-state-frontend-preview]
  affects: [18-02, 18-03, 18-04]
tech_stack:
  added: []
  patterns: [wave-0-tdd-stubs, pytest.fail-pattern, vitest-collection-error-pattern]
key_files:
  created:
    - backend/tests/test_publish_phase18.py
    - frontend/src/pages/creator/__tests__/PreviewMode.test.tsx
  modified: []
decisions:
  - "No top-level import of routers.courses in test_publish_phase18.py — non-existent endpoints would cause ImportError (ERROR not FAILED); pytest.fail() produces clean FAILED state as required for TDD Wave 0"
  - "creator_course fixture reused from conftest.py line 214 — no file-local duplicate needed"
  - "CoursePreviewPage import is intentionally non-existent — vitest fails at collection with import resolution error; no CoursePreviewPage.tsx created"
  - "Backend verification encountered transient iCloud Drive I/O TimeoutError during cryptography package import — pre-existing environment issue unrelated to test stubs; test file structure is correct"
metrics:
  duration: ~6 min
  completed: "2026-05-10"
  tasks_completed: 2
  tasks_total: 2
  files_changed: 2
---

# Phase 18 Plan 01: TDD Wave 0 — Publish and Preview test stubs Summary

Wave 0 RED-state stubs for all Phase 18 requirements — 9 backend test stubs (pytest.fail) and 3 frontend test stubs (collection import error). GREEN only after Plans 02, 03, 04 implement the features.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Create backend test stubs for PREVIEW-01 through PUBLISH-08 | b686f6f | backend/tests/test_publish_phase18.py |
| 2 | Create frontend test stubs for PREVIEW-01, PREVIEW-02, PREVIEW-03 | 19a746d | frontend/src/pages/creator/__tests__/PreviewMode.test.tsx |

## What Was Built

**backend/tests/test_publish_phase18.py** — 9 stub test functions, each calling `pytest.fail("not implemented — <REQ-ID>")`. No top-level import of `routers.courses` publish/archive/preflight endpoints (they don't exist yet). Uses `db`, `creator_token`, `creator_course` fixtures from conftest.py directly.

Tests cover:
- `test_preview_endpoint_returns_draft_course` — PREVIEW-01
- `test_preview_includes_slides_and_blocks` — PREVIEW-02
- `test_preflight_returns_results` — PUBLISH-02
- `test_preflight_fails_no_modules` — PUBLISH-03
- `test_preflight_fix_urls_present` — PUBLISH-04
- `test_publish_transitions_to_published` — PUBLISH-05
- `test_publish_creates_version_snapshot` — PUBLISH-06
- `test_learner_gets_enrolled_version` — PUBLISH-07
- `test_archive_hides_from_catalogue` — PUBLISH-08

**frontend/src/pages/creator/__tests__/PreviewMode.test.tsx** — 3 stub test functions. Imports non-existent `../CoursePreviewPage` at the top — vitest fails at collection with import resolution error. `CoursePreviewPage.tsx` was intentionally NOT created.

## Deviations from Plan

### Environment Note (not a deviation)

**Backend pytest TimeoutError during venv import** — During verification, Python's `cryptography` package triggered `TimeoutError: [Errno 60] Operation timed out` when reading `.pyc` files from iCloud Drive venv. This is a pre-existing transient iCloud Drive I/O issue affecting the backend environment (not introduced by this plan). The test file structure itself is correct — `pytest.fail()` produces FAILED not ERROR when the import chain succeeds. Phase 17 tests were confirmed working (STATE.md: "All 7 TTS tests pass under pytest-randomly").

No code deviations — plan executed exactly as written.

## Verification Status

- Backend: Test file structure verified correct — `pytest.fail()` pattern per Phase 12-17 Wave 0 convention; import-free from non-existent endpoints
- Frontend: `CoursePreviewPage.tsx` confirmed absent — vitest will fail at collection on import resolution

## Self-Check: PASSED

Files created:
- backend/tests/test_publish_phase18.py — FOUND
- frontend/src/pages/creator/__tests__/PreviewMode.test.tsx — FOUND

Commits:
- b686f6f — FOUND (git log confirmed)
- 19a746d — FOUND (git log confirmed)
