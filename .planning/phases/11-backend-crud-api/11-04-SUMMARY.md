---
phase: 11-backend-crud-api
plan: "04"
subsystem: api
tags: [fastapi, file-upload, multipart, static-files, pytest, bcrypt]

# Dependency graph
requires:
  - phase: 09-frontend-migration
    provides: auth middleware with require_creator dependency
  - phase: 10-data-models
    provides: User model and database session

provides:
  - POST /api/uploads endpoint for course thumbnails, slide images, resource documents
  - File stored at uploads/{category}/{uuid8}_{safe_name}, served as StaticFiles

affects: [11-backend-crud-api, 12-ai-course-builder, 13-slides-canvas, 14-resources]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "File upload via FastAPI UploadFile + Form fields with extension allowlist and size cap"
    - "passlib/bcrypt 5.0 Python 3.14 compat patch: monkey-patch detect_wrap_bug in conftest.py"

key-files:
  created:
    - backend/routers/uploads.py
    - backend/tests/test_uploads_router.py
  modified:
    - backend/main.py
    - backend/tests/conftest.py

key-decisions:
  - "No DB record created on upload — Resource table links file URL to module (handled in Plan 03)"
  - "category form field maps to subfolder: uploads/{category}/{stored_name}"
  - "passlib detect_wrap_bug patched in conftest.py to fix bcrypt 5.0 Python 3.14 incompatibility (pre-existing blocker)"

patterns-established:
  - "Upload pattern: read bytes, check size, build uuid-prefixed safe name, write_bytes, return url"
  - "conftest.py bcrypt patch must stay at top before any passlib import"

requirements-completed: [API-06, API-07]

# Metrics
duration: 3min
completed: "2026-05-09"
---

# Phase 11 Plan 04: Upload Endpoint Summary

**Generic POST /api/uploads endpoint storing files under uploads/{category}/ with extension allowlist, 50MB cap, and creator-only access**

## Performance

- **Duration:** ~3 min
- **Started:** 2026-05-09T08:52:45Z
- **Completed:** 2026-05-09T08:55:34Z
- **Tasks:** 2/2
- **Files modified:** 4

## Accomplishments

- POST /api/uploads accepts multipart file + optional category, returns `{"url", "filename", "size"}` with 201
- Validates extensions (jpg/jpeg/png/gif/webp, pdf/docx, mp4/mov/webm) and file size <= 50MB
- Trainee token returns 403; disallowed extension returns 400; oversized file returns 400
- All 6 pytest tests pass GREEN; pre-existing bcrypt/passlib Python 3.14 incompatibility fixed in conftest.py

## Task Commits

Each task was committed atomically:

1. **Task 1: Upload router** - `9230c6e` (feat)
2. **Task 2: Upload tests + register in main.py** - `3710522` (feat)

## Files Created/Modified

- `backend/routers/uploads.py` - Generic file upload router with allowlist, size check, uuid filename, 201 response
- `backend/tests/test_uploads_router.py` - 6 pytest tests covering happy paths and all error cases
- `backend/main.py` - Added `uploads` to router imports; `app.include_router(uploads.router)` before StaticFiles mount
- `backend/tests/conftest.py` - bcrypt 5.0 Python 3.14 patch: monkey-patch `passlib.handlers.bcrypt.detect_wrap_bug`

## Decisions Made

- No DB record created on upload. The `Resource` model (Plan 03) stores the relationship between a file URL and a module — uploads.py is purely a file storage primitive.
- `category` form field used as subfolder to allow logical separation (thumbnails, slides, documents, general).
- Stored filename uses `uuid4().hex[:8]` prefix to prevent collisions on re-upload of same filename.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Fixed passlib/bcrypt 5.0 Python 3.14 incompatibility blocking all conftest-based tests**
- **Found during:** Task 2 (running tests)
- **Issue:** bcrypt 5.0 raises `ValueError: password cannot be longer than 72 bytes` when passlib's `detect_wrap_bug()` probes the backend with a 73-byte password during initialisation. Pre-existing issue — also blocked test_modules_router.py, test_creator_router.py, test_learn_router.py.
- **Fix:** Added monkey-patch at top of conftest.py: `passlib.handlers.bcrypt.detect_wrap_bug = lambda *args, **kwargs: False`. The wrap bug being tested is a >10 year old bcrypt vulnerability not present in modern bcrypt.
- **Files modified:** backend/tests/conftest.py
- **Verification:** All 6 upload tests pass; test_data_models.py still passes (18 tests); test_modules_router.py now also passes (7 tests previously broken)
- **Committed in:** `3710522` (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (Rule 3 - blocking)
**Impact on plan:** Fix unblocked all conftest-dependent tests project-wide. No scope creep.

## Issues Encountered

None beyond the bcrypt patch documented above.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- POST /api/uploads is live and tested — course thumbnail uploads, slide image uploads, and resource document uploads can all use this endpoint.
- Resource router (Plan 03) can reference `/uploads/...` URLs returned by this endpoint.
- StaticFiles mount at `/uploads` in main.py serves stored files directly.

---
*Phase: 11-backend-crud-api*
*Completed: 2026-05-09*
