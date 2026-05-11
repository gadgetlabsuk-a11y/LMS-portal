---
phase: 18-preview-publish
verified: 2026-05-11T21:00:00Z
status: human_needed
score: 11/11 must-haves verified
human_verification:
  - test: "Open Course Builder, click Preview button, confirm amber watermark bar appears with text 'Preview Mode — Draft', course content is visible, and Exit Preview returns to builder"
    expected: "Preview mode launches full-screen with amber watermark overlay over learner iframe; all course content visible; exit lands back in Course Builder"
    why_human: "The preview renders via an iframe pointing to the backend player — cannot test iframe content loading programmatically; returnTo navigation and live content require visual confirmation"
  - test: "Open Course Builder, click Publish, observe PreflightModal — verify colour-coded pass/warn/fail rows render, Fix deep-links navigate to correct screen, Publish button disabled when fails exist"
    expected: "PreflightModal opens with structured results list; failed rows show red Fail badge and clickable Fix button; can_publish=false disables Publish button"
    why_human: "Real API response needed to verify colour rendering, fix_url navigation, and disabled state in a live environment"
  - test: "Complete a course to pass all preflight rules, click Publish, confirm PublishConfirmModal appears, click Confirm & Publish, verify course appears in learner catalogue"
    expected: "Course transitions to PUBLISHED; CourseVersion row created in DB; course visible at /learn"
    why_human: "End-to-end publish flow requires live backend DB state and learner catalogue verification"
  - test: "Publish a course, make an edit, confirm archive button appears, click Archive, verify course disappears from learner catalogue"
    expected: "Archive button visible when status is published or has_unpublished_changes; course removed from /learn after archiving"
    why_human: "Archive button conditional rendering and catalogue disappearance require live state verification"
  - test: "Verify enrolled learner version pinning: enroll a learner, publish v1, re-publish v2, confirm learner still sees v1 snapshot (or verify via DB SELECT * FROM course_versions)"
    expected: "CourseVersion rows exist with correct snapshots; enrolled learner's pinned version_number matches enrollment.course_version"
    why_human: "Requires two-user test or direct DB inspection to confirm snapshot data integrity"
---

# Phase 18: Preview and Publish Verification Report

**Phase Goal:** Creators can preview the full course as a learner, then publish with confidence using a pre-flight checklist — with version history ensuring enrolled learners are never disrupted
**Verified:** 2026-05-11T21:00:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | CoursePreviewPage renders fixed amber watermark banner reading "Preview Mode — Draft" | VERIFIED | `CoursePreviewPage.tsx` line 16: `data-testid="preview-watermark"` with text "Preview Mode — Draft"; `PreviewMode.test.tsx` asserts `toHaveTextContent('Preview Mode — Draft')` |
| 2 | Preview renders full learner course player via backend iframe (all block types, quizzes) | VERIFIED | `CoursePreviewPage.tsx` line 56: `src={\`${API_BASE}/api/courses/${id}/player\`}`; no duplicate renderer; test asserts iframe src contains `/api/courses/1/player` |
| 3 | Exit Preview button navigates to returnTo query param | VERIFIED | `CoursePreviewPage.tsx` line 36: `onClick={() => navigate(returnTo)}`; `returnTo` from `decodeURIComponent(searchParams.get('returnTo'))`; test asserts navigation to custom return path |
| 4 | Route /creator/courses/:id/preview registered in App.tsx behind ProtectedRoute(creatorRoute), no layout wrapper | VERIFIED | `App.tsx` lines 193–200: exact pattern confirmed — `ProtectedRoute creatorRoute`, no `CreatorLayout` wrapper |
| 5 | CourseBuilderPage has Preview button (data-testid="preview-mode-btn") and Publish button (data-testid="publish-btn") in header | VERIFIED | `CourseBuilderPage.tsx` line 105: `data-testid="preview-mode-btn"`, line 121: `data-testid="publish-btn"` |
| 6 | GET /api/courses/:id/preview returns full course tree for creator (bypasses PUBLISHED filter) | VERIFIED | `courses.py` line 492: `preview_course` endpoint; uses `_serialize_course_tree` with `selectinload`; backend test `test_preview_endpoint_returns_draft_course` passes with DRAFT course |
| 7 | GET /api/courses/:id/preflight returns structured pass/warn/fail results with fix_url | VERIFIED | `courses.py` line 504: `preflight_course` endpoint; `_run_preflight()` at line 167 implements 4 rules with fix_url pointing to `/creator/courses/{id}/builder` or `/creator/courses/{id}/quizzes/{quiz_id}` |
| 8 | POST /api/courses/:id/publish creates CourseVersion snapshot and transitions DRAFT→PUBLISHED | VERIFIED | `courses.py` lines 517–550: creates `CourseVersion` row with `_serialize_course_tree` snapshot, bumps `course.version`, sets `status=PUBLISHED`; `test_publish_creates_version_snapshot` passes |
| 9 | POST /api/courses/:id/archive transitions course to ARCHIVED | VERIFIED | `courses.py` line 558: `archive_course` endpoint sets `status=ARCHIVED`; `test_archive_hides_from_catalogue` passes |
| 10 | Enrolled learner version pinning: learn.py looks up CourseVersion snapshot by enrollment.course_version | VERIFIED | `learn.py` lines 110–126: queries `CourseVersion` by `course_id` + `version_number`, serves snapshot title/description; falls back to live course if no row found; `test_learner_gets_enrolled_version` passes |
| 11 | HAS_UNPUBLISHED_CHANGES propagated from all 5 child routers (modules, videos, slides, blocks, quizzes) | VERIFIED | Each child router has local `_mark_course_changed()` helper called in POST/PUT/DELETE handlers — confirmed in modules.py (line 90), videos.py (line 79), slides.py (line 112), blocks.py (line 102), quizzes.py (line 160) |

**Score:** 11/11 truths verified

---

## Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `frontend/src/pages/creator/CoursePreviewPage.tsx` | Full-screen preview with amber watermark and iframe | VERIFIED | 64 lines; contains `preview-watermark`, `exit-preview-btn`, iframe to backend player; no stubs |
| `frontend/src/components/publish/PreflightModal.tsx` | Pre-flight checklist modal with pass/warn/fail rows | VERIFIED | 143 lines; contains `preflight-result-{rule}` testids, `preflight-publish-btn`, `confirm-publish-btn`; real API calls via `api.get` + `.json()` |
| `frontend/src/components/publish/PublishConfirmModal.tsx` | Publish confirmation modal | INFO | 4-line placeholder file — confirm flow is intentionally embedded inside `PreflightModal` as a nested `<Modal>`; `confirm-publish-btn` exists in `PreflightModal.tsx` line 129 |
| `frontend/src/App.tsx` | Route for /creator/courses/:id/preview | VERIFIED | Lines 193–200: route registered behind `ProtectedRoute creatorRoute`, no `CreatorLayout` |
| `frontend/src/pages/creator/CourseBuilderPage.tsx` | Publish, Archive, Preview buttons | VERIFIED | Lines 105 (preview-mode-btn), 121 (publish-btn), 138 (archive-btn); `PreflightModal` imported and wired at line 168 |
| `backend/models/models.py` | CourseVersion model | VERIFIED | Line 450: `class CourseVersion(Base)` with `course_id`, `version_number`, `snapshot`, `published_at`, UniqueConstraint |
| `backend/alembic/versions/005_course_versions.py` | Migration creating course_versions table | VERIFIED | Creates `course_versions` table with `idx_course_version` index; downgrade drops table |
| `backend/routers/courses.py` | preview, preflight, publish, archive endpoints | VERIFIED | Lines 492, 504, 517, 558; all registered before the generic `/{course_id}` GET to avoid path collision |
| `backend/routers/learn.py` | Learner version pinning with snapshot fallback | VERIFIED | Lines 110–126; imports `CourseVersion`, queries by `course_id` + `version_number`, falls back to live course |
| `backend/tests/test_publish_phase18.py` | 9 real test functions (not stubs) | VERIFIED | 9 `def test_` functions with real assertions; no `pytest.fail` remaining; uses `draft_creator_course` local fixture |

---

## Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `CoursePreviewPage.tsx` | `/api/courses/:id/player` | `iframe src` using `API_BASE` | WIRED | Line 56: `src={\`${API_BASE}/api/courses/${id}/player\`}` |
| `CoursePreviewPage.tsx` | `useSearchParams` | `returnTo = decodeURIComponent(searchParams.get('returnTo'))` | WIRED | Lines 7–10: `searchParams.get('returnTo')` decoded and used in `navigate(returnTo)` |
| `CourseBuilderPage.tsx` | `/creator/courses/:id/preview` | `navigate()` in `handlePreview` with encoded `returnTo` | WIRED | `data-testid="preview-mode-btn"` at line 105 triggers `handlePreview`; navigate to preview route confirmed |
| `PreflightModal.tsx` | `/api/courses/:id/preflight` | `api.get` on modal open | WIRED | Lines 37–41: `api.get(`/courses/${courseId}/preflight`).then(res => res.json())` in `useEffect` |
| `PreflightModal.tsx` | `/api/courses/:id/publish` | `api.post` on confirm click | WIRED | Line 56: `await api.post(`/courses/${courseId}/publish`, {})` in `handleConfirmPublish` |
| `CourseBuilderPage.tsx` | `PreflightModal` | `open={showPreflight}` state | WIRED | Line 168: `<PreflightModal open={showPreflight} ...>` wired to `publish-btn` click at line 122 |
| `backend/routers/courses.py` | `backend/models/models.py` | `CourseVersion` import + `selectinload` for snapshot | WIRED | Line 20: `from models.models import CourseVersion`; line 249: `selectinload(Course.modules)...` |
| `backend/routers/learn.py` | `backend/models/models.py` | `CourseVersion` snapshot fallback | WIRED | Line 15: `from models.models import CourseVersion`; lines 110–126: snapshot lookup with fallback |

---

## Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| PREVIEW-01 | 18-01, 18-02, 18-03 | Creator can preview course in learner-view mode with draft watermark | SATISFIED | `CoursePreviewPage.tsx` amber watermark + `/api/courses/:id/preview` endpoint; backend test passes; frontend test passes |
| PREVIEW-02 | 18-01, 18-02, 18-03 | Preview renders all block types; narration scripts visible; quiz in answerable form | SATISFIED | iframe to `/api/courses/:id/player` reuses full backend-rendered player; `_serialize_course_tree` eager-loads full tree; test asserts iframe src |
| PREVIEW-03 | 18-01, 18-03 | Creator can exit preview and return to where they were in builder | SATISFIED | `exit-preview-btn` calls `navigate(returnTo)`; returnTo decoded from searchParams; test confirms navigation to custom return path |
| PUBLISH-01 | 18-04 | Creator can initiate publish flow from Course Builder | SATISFIED | `publish-btn` at line 121 of `CourseBuilderPage.tsx` opens `PreflightModal` via `setShowPreflight(true)` |
| PUBLISH-02 | 18-01, 18-02, 18-04 | Creator sees pre-flight validation checklist with pass/warn/fail per rule | SATISFIED | `PreflightModal` renders `preflight-result-{rule}` rows with colour-coded status badges; `PreflightModal.test.tsx` verifies rendering |
| PUBLISH-03 | 18-01, 18-02, 18-04 | Pre-flight rules: thumbnail uploaded, at least one module, each quiz has ≥3 questions | SATISFIED | `_run_preflight()` in `courses.py`: 4 rules including `thumbnail_uploaded` (WARN), `has_at_least_one_module` (FAIL), `each_quiz_has_minimum_questions` (FAIL); backend test `test_preflight_fails_no_modules` passes |
| PUBLISH-04 | 18-01, 18-02, 18-04 | Each failed rule deep-links to exact fix screen | SATISFIED | `_run_preflight()` sets `fix_url` per rule; `PreflightModal.tsx` renders `preflight-fix-{rule}` button for non-pass results; test confirms Fix link shown |
| PUBLISH-05 | 18-01, 18-02, 18-04 | Creator can publish course (draft → published state transition) | SATISFIED | `POST /api/courses/:id/publish` transitions to `PUBLISHED`; `api.post` called from `PreflightModal.handleConfirmPublish`; backend test passes |
| PUBLISH-06 | 18-01, 18-02, 18-04 | Creator can update published course; system creates version snapshot | SATISFIED | `publish_course` creates `CourseVersion` row with `_serialize_course_tree` snapshot, bumps `course.version`; `test_publish_creates_version_snapshot` passes |
| PUBLISH-07 | 18-01, 18-02 | Learners enrolled on prior version retain progress; new enrolees get latest | SATISFIED | `learn.py` version pinning looks up `CourseVersion` by `enrollment.course_version`, returns snapshot content; `test_learner_gets_enrolled_version` passes |
| PUBLISH-08 | 18-01, 18-02, 18-04 | Creator can archive a published course | SATISFIED | `POST /api/courses/:id/archive` sets `status=ARCHIVED`; `archive-btn` in `CourseBuilderPage` calls `api.post(`/courses/${id}/archive`)`; `test_archive_hides_from_catalogue` passes |

**All 11 requirements: SATISFIED**

---

## Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `frontend/src/components/publish/PublishConfirmModal.tsx` | 4 | `export type { } // placeholder` — empty module | INFO | Not a blocker — the confirm-publish-btn and publish POST call are implemented inside `PreflightModal.tsx` (lines 128–137, 53–62). The plan intentionally made `PublishConfirmModal.tsx` a thin stub for future extraction. All PUBLISH-05/06 test assertions in `PreflightModal.test.tsx` pass. |

No blocker anti-patterns found. No `pytest.fail` stubs remaining in backend tests. No empty React component renders. No static API returns.

---

## Human Verification Required

The automated checks confirm all 11 requirements are implemented and wired. The following items require human browser verification to confirm end-to-end behaviour with live data:

### 1. Preview Mode — Entry, Content, Exit

**Test:** Open Course Builder for a draft course. Click Preview. Observe amber watermark bar. Scroll through course content. Click Exit Preview.
**Expected:** Amber watermark with "Preview Mode — Draft" text appears at top. Course modules and content visible in iframe player (all block types, quizzes). Exit Preview returns to Course Builder.
**Why human:** iframe content loading cannot be tested programmatically; actual course content rendering in the backend player requires a live server.

### 2. Pre-flight Checklist — Colours, Deep-links, Disabled State

**Test:** Open Course Builder. Click Publish. Observe PreflightModal results list. Check colours. If failures exist, click a Fix link.
**Expected:** Pass rows are green, Warn rows are amber, Fail rows are red. Fix buttons navigate to the correct fix screen (e.g., builder, quiz editor). Publish button is disabled when any fail exists.
**Why human:** Colour rendering and navigation to fix screens require visual confirmation with real API data.

### 3. Full Publish Flow — Catalogue Visibility

**Test:** Add module with quiz (3+ questions). Click Publish in CourseBuilderPage. In PreflightModal, click Publish then Confirm & Publish. Log in as learner and check catalogue.
**Expected:** Course status updates to published. Course appears at /learn for a learner user.
**Why human:** End-to-end requires live frontend + backend + two-user scenario.

### 4. Archive Flow — Catalogue Disappearance

**Test:** With a published course, click Archive in CourseBuilderPage. Log in as learner.
**Expected:** Archive button visible when course is published. After archiving, course disappears from learner catalogue at /learn.
**Why human:** Conditional button rendering and catalogue state require live data.

### 5. Learner Version Pinning

**Test:** Publish v1 of a course. Enroll a learner. Make an edit to the course. Publish v2. Check DB `SELECT * FROM course_versions` and confirm enrolled learner still sees v1 snapshot data.
**Expected:** Two CourseVersion rows; enrolled learner's `enrollment.course_version` matches v1 snapshot.
**Why human:** Requires either a two-user setup or direct DB inspection.

---

## Summary

All 11 phase requirements (PREVIEW-01 through PUBLISH-08) are implemented with real code, real tests, and verified wiring. No stub implementations or missing artifacts found. The automated verification gate is clear.

The phase is blocked only on human browser verification to confirm the live end-to-end experience, which Plan 18-05 identifies as the final gate before milestone closure. Per the 18-05 SUMMARY, all 10 browser checks were approved by the creator — however, as this is an automated verification report, those human checks are listed here for formal completeness.

---

_Verified: 2026-05-11T21:00:00Z_
_Verifier: Claude (gsd-verifier)_
