---
phase: 12-course-identity-structure
verified: 2026-05-09T12:00:00Z
status: gaps_found
score: 3/4 success criteria verified
re_verification: false
gaps:
  - truth: "A creator on /creator/courses sees a list of their existing courses"
    status: failed
    reason: "CreatorCourseListPage calls GET /api/courses which returns { total, page, page_size, items: [...] }, but the page reads data.courses ?? [] — the field 'courses' does not exist in the response. The correct field is 'items'. Courses will always render as an empty list."
    artifacts:
      - path: "frontend/src/pages/creator/CreatorCourseListPage.tsx"
        issue: "Line 27: `data.courses ?? []` should be `data.items ?? []` — API returns CourseListResponse with an 'items' field, not 'courses'"
    missing:
      - "Change `data.courses ?? []` to `data.items ?? []` in fetchCourses()"
human_verification:
  - test: "Full Modal 1A → Modal 1B → builder navigation flow in the browser"
    expected: "Streaming text appears in description field in real time; skeleton tree updates on every keystroke; scaffolding completes and browser navigates to /creator/courses/:id/builder"
    why_human: "SSE streaming behaviour, live DOM updates, and navigation cannot be verified programmatically without a running server"
  - test: "Existing course list displays after fix"
    expected: "After fixing data.courses → data.items, existing courses appear as cards with status badges and 'Open Builder' links"
    why_human: "Requires browser with auth session to confirm the fix resolves the empty-list condition"
---

# Phase 12: Course Identity & Structure Verification Report

**Phase Goal:** Creators can create a course with a full identity (title, description, objectives, AI tone) and scaffold its module/video/quiz structure before any content authoring begins
**Verified:** 2026-05-09T12:00:00Z
**Status:** gaps_found — 1 wiring gap blocks the course list view
**Re-verification:** No — initial verification

---

## Goal Achievement

### Success Criteria Assessment

| # | Criterion | Status | Evidence |
|---|-----------|--------|----------|
| 1 | Creator can open Modal 1A, fill identity fields, save course | VERIFIED | CourseIdentityModal.tsx implements all fields (title, description, audience level, tone preset, up to 5 objectives) and POSTs to /api/courses via api.post('/courses') |
| 2 | "Generate with AI" streams text into fields in real time | VERIFIED | streamDescription() and streamObjectives() use fetch + ReadableStream pattern, parsing SSE data: lines on each chunk read |
| 3 | Creator can open Modal 1B, see live skeleton tree update as they type | VERIFIED | CourseStructureModal passes live state to SkeletonTreePreview as props — synchronous re-render on every onChange |
| 4 | Creator confirms structure, navigates to Course Builder with empty modules/videos scaffolded | PARTIAL | Scaffolding logic is correct and sequential. Builder stub route exists. BUT: the course list page will always show empty due to the data.courses wiring gap |

**Score:** 3/4 success criteria fully verified

---

## Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | POST /api/courses accepts and persists audience_level, learning_objectives, ai_tone_preset | VERIFIED | courses.py CourseCreate extended; ORM assignments at lines 230-234; CourseResponse includes Phase 12 fields; test_create_course_with_identity PASSES |
| 2 | POST /api/courses/ai/generate-description returns text/event-stream | VERIFIED | Route at line 256-270, declared before /{course_id} at line 292; test_generate_description_sse PASSES |
| 3 | POST /api/courses/ai/generate-objectives returns text/event-stream | VERIFIED | Route at line 273-289; test_generate_objectives_sse PASSES |
| 4 | ClaudeService has stream_course_description() and stream_learning_objectives() async generators | VERIFIED | Both methods exist in claude_service.py (lines 530-590), delegate to _stream_text() |
| 5 | SSE generator checks request.is_disconnected() on every yield | VERIFIED | Both SSE route generators include `if await request.is_disconnected(): break` |
| 6 | /ai/... routes declared before /{course_id} to avoid FastAPI path collision | VERIFIED | generate-description at line 256, generate-objectives at line 273, /{course_id} GET at line 292 |
| 7 | SkeletonTreePreview renders tree nodes correctly per props | VERIFIED | Component exists, exports named SkeletonTreePreview, both tests GREEN (2/2 tests pass) |
| 8 | CourseIdentityModal form has all required fields and AI streaming | VERIFIED | title, description, audienceLevel, tonePreset, objectives array — all present with proper handlers |
| 9 | CourseStructureModal wires SkeletonTreePreview with live state | VERIFIED | imports SkeletonTreePreview from '@/components/course/SkeletonTreePreview', passes moduleCount/videosPerModule/quizPerModule as live state |
| 10 | Scaffolding is sequential (not parallel) and POSTs modules then videos | VERIFIED | Sequential for-loop with await at each step in handleConfirm() |
| 11 | CreatorCourseListPage at /creator/courses loads existing courses | FAILED | fetchCourses reads data.courses ?? [] but API returns { items: [...] } — courses list always renders empty |
| 12 | /creator/courses/:id/builder route renders stub (not 404) | VERIFIED | App.tsx lines 125-134 render "Course Builder / Coming in Phase 13." inside ProtectedRoute |

---

## Required Artifacts

| Artifact | Status | Details |
|----------|--------|---------|
| `backend/requirements.txt` | VERIFIED | Contains `sse-starlette==2.1.3` |
| `backend/tests/test_courses_phase12.py` | VERIFIED | 4 tests, all GREEN (4 passed, 0 failed) |
| `backend/routers/courses.py` | VERIFIED | Extended CourseCreate, CourseResponse, two SSE endpoints, correct route ordering |
| `backend/services/claude_service.py` | VERIFIED | stream_course_description(), stream_learning_objectives(), _stream_text() all present and substantive |
| `frontend/src/components/course/SkeletonTreePreview.tsx` | VERIFIED | Named export, interface, buildSkeletonNodes(), renders `<li>` elements |
| `frontend/src/components/course/CourseIdentityModal.tsx` | VERIFIED | Named export, all form fields, both AI stream handlers, save to API, abort on close |
| `frontend/src/components/course/CourseStructureModal.tsx` | VERIFIED | Named export, wires SkeletonTreePreview, sequential scaffolding |
| `frontend/src/pages/creator/CreatorCourseListPage.tsx` | PARTIAL | Exists and substantive but has data.courses wiring gap |
| `frontend/src/App.tsx` | VERIFIED | /creator/courses routes to CreatorCourseListPage; /creator/courses/:id/builder stub present |

---

## Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| courses.py SSE endpoints | sse_starlette.sse | import | WIRED | `from sse_starlette.sse import EventSourceResponse` at line 16 |
| generate_description_stream | claude_service.stream_course_description | async generator delegation | WIRED | `async for token in claude_service.stream_course_description(...)` at line 265 |
| generate_objectives_stream | claude_service.stream_learning_objectives | async generator delegation | WIRED | `async for token in claude_service.stream_learning_objectives(...)` at line 282 |
| create_course | Course ORM (audience_level, learning_objectives, ai_tone_preset) | ORM assignment | WIRED | Lines 230-234 assign all Phase 12 fields |
| CourseIdentityModal | POST /api/courses | api.post via api.ts | WIRED | `api.post('/courses', {...})` at line 162 |
| CourseIdentityModal | POST /api/courses/ai/generate-description | fetch + ReadableStream | WIRED | `fetch(\`${API_BASE}/api/courses/ai/generate-description\`, ...)` at line 75 |
| CourseStructureModal | SkeletonTreePreview | named import | WIRED | `import { SkeletonTreePreview } from '@/components/course/SkeletonTreePreview'` at line 5 |
| CourseStructureModal | POST /api/courses/:id/modules + /api/modules/:id/videos | sequential fetch | WIRED | `api.post(\`/courses/${courseId}/modules\`, ...)` and `api.post(\`/modules/${mod.id}/videos\`, ...)` |
| CreatorCourseListPage | GET /api/courses | api.get('/courses') | PARTIAL | Call is correct but response parsing reads `data.courses` instead of `data.items` |
| App.tsx | CreatorCourseListPage | named import + route | WIRED | Import at line 23; route at line 116 |

---

## Requirements Coverage

| Requirement | Description | Status | Evidence |
|-------------|-------------|--------|----------|
| COURSE-01 | Creator can create a course via Modal 1A (title, description, audience level, AI tone preset, up to 5 learning objectives) | VERIFIED | Backend persists all fields (test GREEN); CourseIdentityModal form has all fields |
| COURSE-02 | Creator can generate a course description via AI from topic (streaming) | VERIFIED | SSE endpoint + streamDescription() with ReadableStream; test GREEN |
| COURSE-03 | Creator can generate learning objectives via AI from course title/description (streaming) | VERIFIED | SSE endpoint + streamObjectives() with ReadableStream; test GREEN |
| COURSE-04 | Creator sees Course Structure wizard (Modal 1B) with module/video/quiz count inputs and live skeleton tree preview | VERIFIED | CourseStructureModal + SkeletonTreePreview, 2 frontend tests GREEN |
| COURSE-05 | Creator can confirm structure and have empty modules/videos scaffolded automatically | VERIFIED | Sequential scaffolding in handleConfirm(); test_scaffold_structure GREEN; navigation to builder stub confirmed |

---

## Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `frontend/src/pages/creator/CreatorCourseListPage.tsx` | 27 | `data.courses ?? []` — wrong field name for API response | Blocker | Course list always renders empty; creator cannot see existing courses on the page |

No other anti-patterns found. No TODO/FIXME/placeholder comments in Phase 12 implementation files. No empty handlers or stubs.

---

## Test Results

**Backend:** 4/4 Phase 12 tests GREEN. Full suite: 52/53 tests pass — 1 pre-existing failure in `test_learn_router.py::TestListLearnCourses::test_returns_only_published_courses` introduced in Phase 11 (predates Phase 12; not a regression from this phase).

**Frontend:** 8/8 tests pass including both SkeletonTreePreview tests. TypeScript compiles clean (`npx tsc --noEmit` exits 0). Frontend build succeeds (247.71 kB JS bundle).

---

## Human Verification Required

### 1. Full Modal flow in browser

**Test:** Log in as a creator, navigate to /creator/courses, click "New Course", fill in Title + Tone Preset, click "Generate with AI" for Description.
**Expected:** Streamed text appears incrementally in the Description textarea in real time (character-by-character, not all at once).
**Why human:** SSE streaming behaviour and incremental DOM updates cannot be verified without a running server.

### 2. Skeleton tree live update

**Test:** In Modal 1B, change "Number of Modules" to 3, then "Videos per Module" to 2, then toggle "Include a quiz in each module".
**Expected:** The tree preview below updates immediately on every change with no delay — 3 module rows, 6 video rows, 3 quiz rows (11 total).
**Why human:** Requires browser DOM observation of synchronous rendering.

---

## Gaps Summary

One wiring gap blocks the course list from displaying. The fix is a single line change:

`CreatorCourseListPage.tsx` line 27: `data.courses ?? []` must be `data.items ?? []`

The backend `GET /api/courses` returns `CourseListResponse` with shape `{ total, page, page_size, items: [...] }`. The page correctly calls `api.get('/courses')` and handles the response, but reads the wrong field name. After fix, existing courses will appear as cards.

All other Phase 12 deliverables are fully implemented and wired. The 4 backend tests are GREEN. The 2 SkeletonTreePreview tests are GREEN. The build is clean. The one failing backend test (`test_learn_router`) predates Phase 12 and is not a regression.

---

_Verified: 2026-05-09T12:00:00Z_
_Verifier: Claude (gsd-verifier)_
