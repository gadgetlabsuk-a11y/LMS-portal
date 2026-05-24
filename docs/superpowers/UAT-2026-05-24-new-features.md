# UAT Checklist — Full Portal (2026-05-24)

Complete manual test inventory for the LMS portal, organised by role. Tick `[x]` as each passes; note failures inline. 🆕 = newly built this cycle · ⚠️ = stubbed/incomplete or needs an external key.

**Test env:** Prod https://buildbench.uk/lms (freshly deployed; DB wiped → only default admin exists, so we create data as we go) or local `~/dev/lms`. Backend reached at `/lms/api/...`.

---

## 0. Setup & environment

- [ ] **0.1** Reach `/lms/login`; brand/logo loads (whitelabel).
- [ ] **0.2** Log in as admin (`admin` / default password).
- [ ] **0.3** Confirm backend keys on this env: `CLAUDE_API_KEY` (**required** for AI gen + podcast script/Q&A); `ELEVENLABS_API_KEY` (podcast audio, else ⚠️); `DEEPGRAM_API_KEY` (voice Q&A, else ⚠️).
- [ ] **0.4** Create test users (Admin → Users): `creator1` (creator), `trainee1`, `trainee2` (trainees). Note emails.

> Suggested order to chain data: create users → Creator builds/generates a course + a podcast → Admin assigns them in a department → log in as trainee to verify training/player → Admin checks reminders.

---

## 1. Auth & Account (all roles)

- [ ] **1.1** Login with valid creds → tokens stored, lands on role-appropriate home. (`POST /api/auth/login`)
- [ ] **1.2** Login with wrong password → "Invalid credentials"; after 5 fails the account locks ("Account is locked…").
- [ ] **1.3** Inactive user cannot log in ("User is inactive").
- [ ] **1.4** MFA: for an MFA-enabled user, login returns a code challenge → enter TOTP → success; bad code → "Invalid MFA code". (`POST /api/auth/verify-mfa`)
- [ ] **1.5** `GET /api/auth/me` returns current user (id, role, mfa_enabled).
- [ ] **1.6** Token refresh works (session persists past access-token expiry). (`POST /api/auth/refresh`)
- [ ] **1.7** Logout → sessions deactivated, redirected to `/login`. (`POST /api/auth/logout`)
- [ ] **1.8** Role gating: a trainee cannot reach `/admin/*` or `/creator/*` (403 / redirect).
- ⚠️ **1.9** Self-service registration, self password-change, and self profile-edit are **not implemented** (admin-managed only) — confirm they're absent/disabled, don't test as features.

---

## 2. USER / Learner

Layout: `LearnerLayout` (nav: Catalogue · My Training). Login as `trainee1`.

### 2.1 Catalogue & course detail
- [ ] **2.1.1** `/learn` lists **published** courses in a grid; pagination/"Load more". (`GET /api/learn/courses`)
- [ ] **2.1.2** Search box filters by title/description (debounced). (`?q=`)
- [ ] **2.1.3** Open a course → detail shows module/video/slide structure (accordions). (`GET /api/learn/courses/{id}`)
- [ ] **2.1.4** A course with a published broadcast shows a "Launch broadcast" entry.

### 2.2 Enrolment, player & progress
- [ ] **2.2.1** Enroll in a course → enrolment created at 0%. (`POST /api/courses/{id}/enroll`); re-enroll → handled (no dupe).
- [ ] **2.2.2** Navigate modules/videos; expand/collapse accordions.
- ⚠️ **2.2.3** Slide/block **player UI** for learners appears to be a placeholder/legacy — verify what renders when opening a lesson (`GET /api/courses/{id}/player` returns a placeholder for slide-based courses). Record actual behaviour.
- [ ] **2.2.4** Progress update / completion: reaching 100% marks completed + timestamp. (`PUT /api/courses/{id}/progress?progress=100`)
- ⚠️ **2.2.5** Learner **quiz-taking** — no learner submit endpoint found; quizzes are authored but may not be playable yet. Verify/record.
- ⚠️ **2.2.6** **Certificates** — `certificate_enabled` exists but no learner certificate endpoint found. Verify/record.

### 2.3 Broadcasts / ILB player
- [ ] **2.3.1** `/learn/broadcasts` lists **published** broadcasts; Launch. (`GET /api/ilb/broadcasts`)
- [ ] **2.3.2** Start a session (Interrupt/Defer). (`POST /api/ilb/sessions`); segment text shows; audio plays if rendered.
- [ ] **2.3.3** Ask a text question → grounded answer + citations/escalation. (`POST /api/ilb/sessions/{id}/ask`)
- ⚠️ **2.3.4** Voice question (needs `DEEPGRAM_API_KEY`) (`POST /api/ilb/stt`); avatar is HeyGen-stubbed. Record degraded behaviour if no key.
- [ ] **2.3.5** Finish session → "completed and sealed (audit chain #N)". (`POST /api/ilb/sessions/{id}/complete`)
- [ ] **2.3.6 (opt)** Audit pack downloads JSON+HTML. (`GET /api/ilb/sessions/{id}/audit-pack`)

### 2.4 🆕 My Required Training
- [ ] **2.4.1** `/learn/my-training` lists mandatory items (Course/Podcast), due date or "No deadline", status badge. (`GET /api/learn/required-training`)
- [ ] **2.4.2** Past-due item → **Overdue** (red); future → Not started/In progress.
- [ ] **2.4.3** Same target mandatory in two departments → appears **once**, earliest due date.
- [ ] **2.4.4** Complete an item → status flips to **Completed**.
- [ ] **2.4.5** Non-mandatory content does NOT appear here.

---

## 3. CREATOR

Layout: creator nav. Login as `creator1`.

### 3.1 Dashboard & course list
- [ ] **3.1.1** `/creator` dashboard stats (total/published/draft courses, enrolments). (`GET /api/creator/stats`)
- [ ] **3.1.2** `/creator/courses` lists own courses; create a course (DRAFT). (`POST /api/courses`)
- [ ] **3.1.3** Edit metadata on a published course → status flips to HAS_UNPUBLISHED_CHANGES. (`PUT /api/courses/{id}`)
- [ ] **3.1.4** `/creator/learners` lists learners in own courses (+ course filter). (`GET /api/creator/learners`)

### 3.2 Course builder hierarchy
- [ ] **3.2.1** Create/rename/delete **modules**; reorder (atomic). (`/api/courses/{id}/modules`, `/modules/{id}`, `/reorder`)
- [ ] **3.2.2** Create/edit/delete **videos** in a module; reorder. (`/api/modules/{id}/videos`, `/videos/{id}`)
- [ ] **3.2.3** Create/edit/delete **slides** in a video; reorder; set layout/transition. (`/api/videos/{id}/slides`, `/slides/{id}`)
- [ ] **3.2.4** Slide editor: add/edit/delete **blocks** (heading/text/image/code/quote/list…); drag/resize on canvas saves grid position; text autosaves (~500ms); undo/redo (Cmd+Z). (`/api/slides/{id}/blocks`, `/blocks/{id}`)
- [ ] **3.2.5** Delete cascades (delete module → its videos/slides/blocks gone).

### 3.3 Quizzes
- [ ] **3.3.1** Create a quiz in a module (pass_rate, attempts, feedback timing). (`POST /api/modules/{id}/quizzes`)
- [ ] **3.3.2** Add questions (MCQ single/multi, true/false, short answer); reorder; set correct answer + explanation. (`/api/quizzes/{id}/questions`)
- [ ] **3.3.3** 🆕-ish AI-generate questions (SSE). (`POST /api/quizzes/{id}/ai/generate-questions`)

### 3.4 AI generation helpers (SSE) — need `CLAUDE_API_KEY`
- [ ] **3.4.1** Generate course description / objectives. (`/api/courses/ai/generate-description`, `/generate-objectives`)
- [ ] **3.4.2** Generate module description; slide narration; slide outline. (`/modules/{id}/ai/generate-description`, `/slides/{id}/ai/generate-narration`, `/generate-outline`)

### 3.5 🆕 AI Course Generation (content → course)
- [ ] **3.5.1** `/creator/courses` → "Generate from content" → upload .pptx/.docx/.pdf (≤10, ≤10MB); bad type rejected.
- [ ] **3.5.2** Settings (modules/videos/slides, tone, difficulty) → **Generate outline**. (`POST /api/courses/ai/outline-from-content`)
- [ ] **3.5.3** Edit outline tree → **Create course** (draft + source docs stored). (`POST /api/courses/from-outline`)
- [ ] **3.5.4** Content fill progress bar (SSE per video) completes; note any failed slides. (`POST /api/videos/{id}/ai/generate-content`)
- [ ] **3.5.5** "Done" → lands in builder with generated modules/videos/slides/blocks.
- [ ] **3.5.6 (neg)** Unreadable file / >10 files → graceful error + retry.

### 3.6 Narration / TTS — need `ELEVENLABS_API_KEY`
- [ ] **3.6.1** Generate audio for a slide. (`POST /api/slides/{id}/tts/generate`)
- [ ] **3.6.2** Bulk-generate for a video (skips no-script + cached). (`POST /api/videos/{id}/tts/bulk-generate`)
- ⚠️ **3.6.3** Without the key → clean 503 "TTS not configured".

### 3.7 🆕 Podcast / ILB authoring
- [ ] **3.7.1** `/creator/podcasts` **From course**: pick course → Generate script → Save → Render audio → Publish. (`/api/ilb/courses/{id}/podcast*`)
- [ ] **3.7.2** **Standalone**: New broadcast → add source (paste/upload doc) → pick voice → Generate script → Save → Render audio → Publish. (`/api/ilb/broadcasts*`, `/api/ilb/voices`)
- [ ] **3.7.3** Launch preview routes to the learner player.

### 3.8 Media uploads & preview/publish
- [ ] **3.8.1** Upload an image/doc/video (≤50MB; bad type rejected). (`POST /api/uploads`)
- [ ] **3.8.2** Preview full course tree. (`GET /api/courses/{id}/preview`)
- [ ] **3.8.3** Preflight check before publish (title, ≥1 module, quizzes ≥3 Qs). (`GET /api/courses/{id}/preflight`)
- [ ] **3.8.4** Publish (creates version snapshot) → PUBLISHED; Archive hides from catalogue. (`/publish`, `/archive`)

---

## 4. ADMIN

Layout: `AdminLayout` sidebar. Login as `admin`.

### 4.1 Dashboard
- [ ] **4.1.1** `/admin` shows KPI cards (users, active courses, completion rate, API calls) + recent activity. (`GET /api/admin/stats`, `/audit-log?limit=5`)

### 4.2 User management (`/admin/users`)
- [ ] **4.2.1** List/search/filter users (paginated). (`GET /api/users`)
- [ ] **4.2.2** Create user (password policy enforced; dupe username/email → 400). (`POST /api/users`)
- [ ] **4.2.3** Edit user (email/role/is_active). (`PUT /api/users/{id}`)
- [ ] **4.2.4** Deactivate user (can't delete self). (`DELETE /api/users/{id}`)
- [ ] **4.2.5** Reset password → temp password returned. (`POST /api/users/{id}/reset-password`)
- [ ] **4.2.6** Toggle MFA → QR + secret on enable. (`POST /api/users/{id}/toggle-mfa`)
- [ ] **4.2.7** Unlock a locked account. (`POST /api/users/{id}/unlock`)
- [ ] **4.2.8** View user activity (login attempts + audit). (`GET /api/users/{id}/activity`)
- [ ] **4.2.9** Bulk CSV import (created/failed/errors). (`POST /api/users/bulk-import`)

### 4.3 Course management (`/admin/courses`)
- [ ] **4.3.1** List all courses (any creator); view/edit/delete; see enrolment counts. (`/api/courses`)

### 4.4 Security (`/admin/security`)
- [ ] **4.4.1** Summary: active sessions, failed logins 24h, locked accounts. (`GET /api/security/dashboard`)
- [ ] **4.4.2** Sessions tab: list; kill a session (force logout). (`GET/DELETE /api/security/sessions`)
- [ ] **4.4.3** Login attempts tab: list/filter by user/success. (`GET /api/security/login-attempts`)
- [ ] **4.4.4** Audit log tab: list/filter by action/resource/user. (`GET /api/security/audit-log`)
- [ ] **4.4.5** IP allowlist: add / list / remove. (`/api/security/ip-allowlist`)

### 4.5 🆕 Departments (`/admin/departments`)
- [ ] **4.5.1** Create department (dupe name → 409). (`POST /api/departments`)
- [ ] **4.5.2** Add members (`trainee1`,`trainee2`); re-add = no-op; unknown user → 400. (`POST /{id}/members`)
- [ ] **4.5.3** Assign a **course** mandatory + **fixed** date → row labelled Course/Mandatory/due. (`POST /{id}/content`)
- [ ] **4.5.4** Assign a **standalone podcast** mandatory + **relative** N days → labelled Podcast.
- [ ] **4.5.5** Auto-enrol: members got the **course** enrolment; the **podcast** created none.
- [ ] **4.5.6** Compliance counts per mandatory row (not-started/in-progress/completed/overdue). (`GET /{id}/compliance`)
- [ ] **4.5.7** Add a member after assignment → inherits the course enrolment.
- [ ] **4.5.8** Edit assignment (toggle mandatory / change deadline). (`PUT /{id}/content/{cid}`)
- [ ] **4.5.9** Remove member / unassign content → enrolments & sessions **kept**. (`DELETE …`)
- [ ] **4.5.10 (neg)** Mandatory+fixed w/o date → 400; assign same content twice → 409.
- [ ] **4.5.11** Delete department → members+assignments gone, enrolments intact. (`DELETE /{id}`)

### 4.6 🆕 Training Reminders (`/admin/reminders`)
- [ ] **4.6.1** Table of learners overdue/due-soon (name+email, item, due, status); overdue first. (`GET /api/departments/reminders?within_days=14`)
- [ ] **4.6.2** Window filter 7/14/30 days updates the list.
- [ ] **4.6.3** A completed learner drops off; nobody behind → all-clear message.

### 4.7 White-label / branding (`/admin/whitelabel`)
- [ ] **4.7.1** Edit brand name; upload logo + favicon. (`PUT /api/whitelabel/config`, `/logo`, `/favicon`)
- [ ] **4.7.2** Edit colours (hex validated), fonts, border radius, custom CSS; Save. 
- [ ] **4.7.3** Export / import theme JSON. (`/export`, `/import`); live preview reflects changes. (`GET /api/whitelabel/preview`)

### 4.8 Dev tools (`/admin/dev-tools`)
- [ ] **4.8.1** System health (uptime/CPU/mem/disk/db size). (`GET /api/dev/health`)
- [ ] **4.8.2** Error log list/filter. (`GET /api/dev/errors`)
- [ ] **4.8.3** Claude API usage stats. (`GET /api/dev/api-usage`)
- [ ] **4.8.4** Feature flags: list / create / toggle. (`/api/dev/feature-flags`)
- [ ] **4.8.5** Environment info. (`GET /api/dev/env-info`)

---

## Result log

| Area | Pass/Fail | Notes |
|---|---|---|
| 0 Setup | | |
| 1 Auth & Account | | |
| 2 Learner | | |
| 3 Creator | | |
| 4 Admin | | |

---

## Known stubbed / incomplete / deferred
- ⚠️ Learner **quiz-taking** and **certificates** — authored/flagged but no learner-facing play/download endpoints found.
- ⚠️ Learner **slide/block player** — appears to be a placeholder for slide-based courses (legacy player).
- ⚠️ **Voice STT / TTS / HeyGen avatar** in ILB — degrade/stub without `DEEPGRAM`/`ELEVENLABS`/HeyGen keys.
- ⚠️ **Self-service** registration / password-change / profile-edit — not implemented (admin-managed only).
- 🆕→later: **Email reminder *sending*** (transport + creds + schedule) — only the reminders data + report exist.
- Pre-existing backend unit-test failures: 2× `has_content` in learner catalogue (known `Course.content` retirement issue).
