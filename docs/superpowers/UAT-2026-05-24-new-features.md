# UAT Checklist — New Features (2026-05-24)

Manual user-acceptance tests for everything added recently. Tick `[x]` as each passes; note failures inline.

**Scope:** (A) Departments & mandatory training, (B) Learner "My Required Training", (C) Admin "Training Reminders", (D) Standalone Podcast / ILB, (E) Course-attached Podcast, (F) AI Course Generation.

---

## 0. Test environment & setup (do first)

- Decide where we test: **Prod** (https://buildbench.uk/lms) or **local dev** (`~/dev/lms`). Prod is freshly deployed; its SQLite was wiped on the last backend redeploy, so it starts with only the default admin.
- [ ] **0.1** Log in as admin (`admin` / default password) at `/lms/login`.
- [ ] **0.2** Confirm backend env keys are set on the test environment:
  - `CLAUDE_API_KEY` — **required** for AI course generation and podcast script generation/Q&A.
  - `ELEVENLABS_API_KEY` — optional; needed to render podcast narration audio (else audio steps degrade).
  - `DEEPGRAM_API_KEY` — optional; needed for podcast voice questions (else voice input degrades).
- [ ] **0.3** Create test users (Admin → Users → create): one **creator** (`creator1`) and two **trainees** (`trainee1`, `trainee2`). Note their emails (used by reminders).

> Tip: features depend on data, so run sections in order F → D/E → A → B → C (generate a course, make a podcast, assign them in a department, then verify learner + reminders views).

---

## F. AI Course Generation (creator)

Route: `/lms/creator/courses` → "Generate from content". Needs `CLAUDE_API_KEY`.

- [ ] **F.1** As creator, open `/creator/courses`, click **"Generate from content"** → wizard opens on the Upload step.
- [ ] **F.2** Upload 1–3 source files (`.pptx`/`.docx`/`.pdf`). Verify: unsupported types are rejected with an error; selected files list; "Next" enables.
- [ ] **F.3** Settings step: set modules/videos-per-module/slides-per-video, tone, difficulty → click **"Generate outline"**.
- [ ] **F.4** Outline generated (Phase 1, `POST /api/courses/ai/outline-from-content`): a course title + editable module/video/slide tree appears. Verify content reflects the uploaded docs.
- [ ] **F.5** Edit the outline (rename/delete a node) → click **"Create course"** (Phase 2a, `POST /api/courses/from-outline`): draft course created.
- [ ] **F.6** Content fill (Phase 2b, SSE per video): progress bar advances "Filling content… N/total slides". Verify it completes; note any "couldn't be generated" slide count.
- [ ] **F.7** Click **"Done"** → lands in the Course Builder (`/creator/courses/{id}/builder`) with the generated modules/videos/slides/blocks present.
- [ ] **F.8** Publish the course (so it can be assigned/enrolled later). Verify status → Published.
- [ ] **F.9 (negative)** Try with an unreadable/empty file or bad settings → graceful error + retry, no crash.

---

## D. Standalone Podcast / ILB (creator authoring + learner playback)

Creator route: `/lms/creator/podcasts` → "Standalone" tab. Needs `CLAUDE_API_KEY` (script/Q&A); `ELEVENLABS_API_KEY` (audio) optional.

### Authoring
- [ ] **D.1** As creator, open `/creator/podcasts`, **Standalone** tab → **"New broadcast"**, enter a title → broadcast created, shows "Draft".
- [ ] **D.2** Add source content: paste text OR **"Upload doc"** (`POST /api/ilb/broadcasts/{id}/source-upload`) → "Extracted N chars".
- [ ] **D.3** Set host persona + pick a voice (`GET /api/ilb/voices`) + target minutes.
- [ ] **D.4** **"Generate script"** (`POST /api/ilb/broadcasts/{id}/generate-script`) → script populates with `[SEGMENT BREAK]`s; segment count shown.
- [ ] **D.5** **"Save"** (`PUT /api/ilb/broadcasts/{id}`) → "Saved"; segments stored.
- [ ] **D.6** **"Render audio"** (`POST .../render-audio`) → "Narration rendered — N clip(s)". *(If no `ELEVENLABS_API_KEY`: expect a clear 503/"TTS not configured" — record as degraded-pass.)*
- [ ] **D.7** **"Publish"** (`POST .../publish`) → badge "Published"; sidebar updates.

### Learner playback
- [ ] **D.8** As trainee, go to `/learn/broadcasts` (`GET /api/ilb/broadcasts`) → only **published** broadcasts listed; click **Launch** (or open `/learn/broadcast/{id}`).
- [ ] **D.9** Pick **Interrupt** mode → **"Start broadcast"** (`POST /api/ilb/sessions`) → player enters playing; segment text shows; audio plays if rendered.
- [ ] **D.10** Navigate segments (Prev/Next); captions toggle works.
- [ ] **D.11** Type a question → **"Ask now"** (`POST /api/ilb/sessions/{id}/ask`) → grounded answer appears in transcript with citations/escalation as applicable.
- [ ] **D.12 (optional)** **Defer** mode: queue a question, then "Answer queued (N)" at a segment break → answered.
- [ ] **D.13 (optional, needs `DEEPGRAM_API_KEY`)** **🎤 Speak** → record → stop (`POST /api/ilb/stt`) → transcript fills the question. *(No key: record as degraded.)*
- [ ] **D.14** **"Finish"** (`POST /api/ilb/sessions/{id}/complete`) → "Session completed and sealed (audit chain #X)"; button → "Completed ✓".

---

## E. Course-attached Podcast (variant of D)

Creator route: `/lms/creator/podcasts` → "From course" tab.

- [ ] **E.1** Select a course → **"Generate script"** (`POST /api/ilb/courses/{cid}/podcast-script`, grounded in the course's modules/videos/slides) → script populates.
- [ ] **E.2** **Save** (`PUT /api/ilb/courses/{cid}/podcast`) → "Saved".
- [ ] **E.3** **Render audio** + **Publish** (`POST /api/ilb/courses/{cid}/podcast/publish`).
- [ ] **E.4** Launch preview `/learn/{cid}/broadcast` → plays; ask + complete works (as D.9–D.14).
- [ ] **E.5** Completing a course-attached broadcast marks the **enrolment** complete (the fix): verify the course shows completed for that learner.

---

## A. Departments & Mandatory Training (admin)

Route: `/lms/admin/departments` (sidebar "Departments" 🏢). Admin only.

- [ ] **A.1** Open `/admin/departments` → **"+ New Department"** → create "Operations" (+ description). Card appears with 0 members / 0 assignments.
- [ ] **A.2** Open the department → **Members**: add `trainee1` and `trainee2` (`POST /{id}/members`). They appear; re-adding the same user is a no-op.
- [ ] **A.3** **Content**: assign the **AI-generated course** (from F) — toggle **Mandatory**, choose **Fixed date** in the near future → **Assign** (`POST /{id}/content`). Row shows "Course" + "Mandatory" + due date.
- [ ] **A.4** Assign the **standalone podcast** (from D) — Mandatory, **Relative (N days from joining)**. Row shows "Podcast" + "Mandatory" + "Due N days after joining".
- [ ] **A.5** Verify **auto-enrolment**: trainees got an enrolment for the assigned **course** (e.g. it shows in their learner course list); the **podcast** assignment did NOT create an enrolment (broadcasts have none).
- [ ] **A.6** **Compliance summary** on each mandatory row shows counts (e.g. 2 not-started for a fresh course; overdue if the date is past).
- [ ] **A.7** Add a member AFTER assigning → they **inherit** the course enrolment automatically.
- [ ] **A.8** Remove a member / unassign content → the assignment/membership goes, but learner progress/enrolments are **left intact** (no data loss).
- [ ] **A.9 (negative)** Assign with Mandatory + Fixed but no date → 400 error; assign the same content twice → 409; duplicate department name → 409.
- [ ] **A.10** Delete a department → members + assignments removed; enrolments untouched.

---

## B. Learner — "My Required Training"

Route: `/lms/learn/my-training` (learner nav "My Training").

- [ ] **B.1** As `trainee1`, open **My Training** (`GET /api/learn/required-training`) → lists the mandatory **course** and **podcast** from A, each with Course/Podcast label, due date (or "No deadline"), and a status badge.
- [ ] **B.2** A past-due item shows **Overdue** (red); an in-future item shows **Not started/In progress**.
- [ ] **B.3** Same target mandatory in two departments appears **once**, with the **earliest** due date.
- [ ] **B.4** Click **Start** on the course → routes to the course; complete it → return to My Training → status flips to **Completed** (green).
- [ ] **B.5** Complete the podcast (play + Finish, per D) → its status flips to **Completed**.
- [ ] **B.6** Non-mandatory content does NOT appear here.

---

## C. Admin — "Training Reminders"

Route: `/lms/admin/reminders` (sidebar "Reminders" ⏰). Admin only.

- [ ] **C.1** Open **Reminders** (`GET /api/departments/reminders?within_days=14`) → table of learners with mandatory training that is **overdue or due-soon**: learner (name + email), item (+ Course/Podcast), due date, status.
- [ ] **C.2** **Overdue** rows show first (sorted), with a red "Overdue" badge; upcoming show "Due soon".
- [ ] **C.3** Change the **window** (7/14/30 days) → list updates (more/fewer due-soon items).
- [ ] **C.4** A learner who **completed** their item drops off the list.
- [ ] **C.5** When nobody is behind → "No one is overdue or due soon 🎉".

---

## Result log

| Section | Pass/Fail | Notes |
|---|---|---|
| 0 Setup | | |
| F AI Course Gen | | |
| D Standalone Podcast | | |
| E Course Podcast | | |
| A Departments | | |
| B Learner Training | | |
| C Reminders | | |

---

### Deferred / known
- **Email reminder *sending*** is not built (needs a transport + creds + schedule) — only the reminders **data + report** exist. Not in this UAT.
- 2 pre-existing backend unit-test failures (`has_content` in the learner catalogue) — known `Course.content` retirement issue, unrelated.
