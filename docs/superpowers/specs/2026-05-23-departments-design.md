# Departments, Assignments & Mandatory Training — Design

**Status:** Approved design (v1)
**Date:** 2026-05-23
**Owner:** Stuart Roberts
**Type:** Extension of the existing LMS module (same repo — FastAPI backend + Vite/React frontend)

---

## 1. Purpose & Framing

Admins need to group users into **departments**, assign **courses and podcasts** to a department, and
mark an assignment **mandatory** with a **completion deadline**. Every member of the department — present
and future — is then required to complete that content by the deadline. This is the data and admin
foundation for compliance training; the email reminders that nudge users toward their deadlines are a
**later** build and are explicitly out of scope here.

A "podcast" can be one of two things in this system, and a department must be able to assign **both**:

1. A **standalone Broadcast** (the `broadcasts` table / `Broadcast` model added by the
   `010_standalone_broadcasts` migration) — org content that lives outside any course (team brief,
   company news, policy update). This is what stakeholders mean by "a standalone podcast." It is
   watched and completed **without an `Enrollment`**: a `BroadcastSession` links directly to the
   broadcast via `broadcast_id` + `learner_id`.
2. A **course-attached broadcast** — a `Course` with `ilb_published=true`. For assignment purposes
   this is just a course.

So a department assignment (`department_content`) targets **either a Course or a standalone Broadcast**.
Completion is read from the appropriate signal for each: courses via `Enrollment.completed`, standalone
broadcasts via a completed `BroadcastSession` for that learner.

> **Design note:** An earlier revision of this spec assumed "a podcast is always a Course with
> `ilb_published`." The `010_standalone_broadcasts` work introduced a genuine standalone entity, so the
> assignment model below was revised to be polymorphic over Course / Broadcast.

---

## 2. Locked Decisions

| # | Decision | Choice | Rationale |
|---|---|---|---|
| 1 | Membership cardinality | **Many-to-many** (a user can be in several departments) | Matches real orgs (e.g. someone in both Sales and Compliance) |
| 2 | Assignable unit | **Course OR standalone Broadcast** (polymorphic assignment) | A standalone `Broadcast` entity exists (`010_standalone_broadcasts`); departments must assign both kinds |
| 3 | Assignment architecture | **Explicit assignment table + auto-enroll (courses only)** (Approach A) | Future joiners inherit requirements; enables real compliance reporting and the later email job. Broadcasts have no enrollment, so nothing to auto-enroll — they're simply "required" |
| 4 | Due date semantics | **Per-assignment choice of fixed calendar date OR relative days** | Fixed matches "by a certain date"; relative ("within N days") is fair to late joiners |
| 5 | Relative-deadline anchor | **The user's department-join date** (`department_members.added_at`) | Works identically for courses and broadcasts (broadcasts have no enrollment date); "N days from when you became responsible" |
| 6 | Source of truth for "required" | **Current membership + current assignments**, not enrollment/session existence | Removing a member/unassigning content must not delete progress or audit history |
| 7 | Completion signal | **Per content type:** course → `Enrollment.completed`; standalone broadcast → a completed `BroadcastSession` for the learner | Standalone broadcasts have no enrollment; course-attached broadcasts still flow through enrollment (see §3 patch) |
| 8 | Scope this pass | **Backend (model + API) + admin UI** | Email reminders and a learner-facing "required training" page are deferred |

---

## 3. Architecture — Reuse vs Extend vs Build

### Reuse as-is
- **`User`** — role enum `ADMIN`/`CREATOR`/`TRAINEE`; no schema change.
- **`Course`** — assignable unit (a course; `ilb_published` marks a course-attached broadcast); no schema change.
- **`Broadcast`** (`broadcasts` table, added by `010_standalone_broadcasts`) — standalone assignable unit; no schema change.
- **`Enrollment`** — per-user/per-course progress + completion. `uq_user_course` (user_id, course_id) makes course auto-enroll idempotent. No schema change.
- **`BroadcastSession`** — per-playthrough record. For a standalone broadcast it carries `broadcast_id` + `learner_id` (no enrollment); `completion_status='completed'` is the finished signal. For a course-attached broadcast it carries `enrollment_id`.
- **Standalone broadcast API** — `GET /api/ilb/broadcasts` (list, supports a published filter) is reused by the admin UI's content picker.
- **Admin auth** — `require_role(UserRole.ADMIN)`.
- **Frontend admin pattern** — `frontend/src/pages/admin/*`, `AdminLayout`, `api.get/post/put/delete` from `@/services/api`.

### Build (new)
- Three tables (§4), one Alembic migration (`department_content` is polymorphic over course/broadcast).
- `backend/services/department_service.py` — course auto-enroll sync + per-type completion + compliance status.
- `backend/routers/departments.py` — admin-only endpoints (§7).
- `frontend/src/pages/admin/DepartmentsPage.tsx` + `DepartmentDetailPage.tsx`, nav entry + routes.

### Patch (small, isolated)
- Broadcast-complete endpoint in [backend/routers/ilb.py](../../../backend/routers/ilb.py): when a `BroadcastSession` completes **and it is enrollment-backed** (course-attached broadcast), also set the linked `Enrollment.completed=True` / `completed_at` / `progress=100.0`. Standalone broadcast sessions have no enrollment, so the patch is a no-op for them (their completion signal is the session itself). This keeps `Enrollment.completed` reliable for course-attached broadcasts; implementation must stay consistent with how regular multi-module courses set `Enrollment.completed` (`progress >= 100`).

---

## 4. Data Model

One additive migration creating three tables. **No columns added to existing tables.**

### `departments`
| Column | Type | Notes |
|---|---|---|
| id | Integer PK | |
| name | String(255) | unique, not null |
| description | Text | nullable |
| is_active | Boolean | default true, not null |
| created_at | DateTime | default utcnow |
| updated_at | DateTime | onupdate utcnow |

### `department_members` (many-to-many users ↔ departments)
| Column | Type | Notes |
|---|---|---|
| id | Integer PK | |
| department_id | Integer FK → departments.id | ondelete CASCADE |
| user_id | Integer FK → users.id | ondelete CASCADE |
| added_at | DateTime | default utcnow |

`UniqueConstraint(department_id, user_id)`; indexes on `user_id` and `department_id`.

### `department_content` (the assignment record — polymorphic over course/broadcast)
| Column | Type | Notes |
|---|---|---|
| id | Integer PK | |
| department_id | Integer FK → departments.id | ondelete CASCADE |
| course_id | Integer FK → courses.id | **nullable**, ondelete CASCADE — set when the target is a course |
| broadcast_id | Integer FK → broadcasts.id | **nullable**, ondelete CASCADE — set when the target is a standalone broadcast |
| mandatory | Boolean | default false, not null |
| due_mode | String(20) | `'fixed'` \| `'relative'` \| null (only meaningful when mandatory) |
| due_date | DateTime | nullable; used when `due_mode='fixed'` |
| due_days | Integer | nullable; used when `due_mode='relative'` |
| assigned_by | Integer FK → users.id | nullable, ondelete SET NULL |
| created_at | DateTime | default utcnow |
| updated_at | DateTime | onupdate utcnow |

**Exactly one** of `course_id` / `broadcast_id` is set per row (enforced at the API boundary). The
content "kind" is *derived* (`'broadcast'` if `broadcast_id` else `'course'`) — no stored type column.
`UniqueConstraint(department_id, course_id)` name `uq_department_course` and
`UniqueConstraint(department_id, broadcast_id)` name `uq_department_broadcast` (SQLite treats NULLs as
distinct, so the unused-FK rows don't collide); indexes on `course_id` and `broadcast_id`.

### SQLAlchemy relationships
- `Department.members` (via `department_members`), `Department.content` (→ `department_content`, cascade delete).
- `DepartmentContent.course` (→ `Course`, for title + `ilb_published`) and `DepartmentContent.broadcast` (→ `Broadcast`, for title + `published`), both one-directional (no back_populates on Course/Broadcast).
- `User` ↔ departments association (read-only convenience query is acceptable; no requirement to back-populate).

---

## 5. Source-of-Truth Rules (computed; not stored on enrollment/session)

1. **Is target T mandatory for user U?** — True iff there exists a `department_content` row with
   `mandatory=true` whose target (`course_id` or `broadcast_id`) is T and whose `department_id` is one
   of U's current memberships.
2. **Multi-department resolution** — A target is mandatory if **any** of U's departments marks it
   mandatory. The **effective due date is the earliest** applicable due date across those rows.
3. **Effective due date per user** (anchor = U's `department_members.added_at` for the owning department)
   - `fixed` → `due_date` (same for everyone; a late joiner inherits it and may already be overdue).
   - `relative` → that user's `added_at + due_days`.
   - mandatory with no due info → required, **no hard deadline** (never "overdue").
4. **Completion** (per content type)
   - **course** → `Enrollment.completed` for (U, course_id) (kept reliable for course-attached
     broadcasts by the §3 patch).
   - **standalone broadcast** → there exists a `BroadcastSession` with `broadcast_id`, `learner_id=U`,
     and `completion_status='completed'`.
5. **Started** (for the `in_progress` distinction)
   - **course** → an `Enrollment` exists with `progress > 0`.
   - **standalone broadcast** → any `BroadcastSession` exists for (broadcast_id, U).
6. **Per-user status** (computed from the booleans above)
   - `completed` — completion signal is true.
   - `overdue` — not completed **and** effective due date is in the past (overrides the rest).
   - `in_progress` — started but not completed.
   - `not_started` — otherwise.

---

## 6. Auto-Enroll Behaviour (`backend/services/department_service.py`)

Auto-enroll applies to **course** assignments only. Standalone broadcasts have no `Enrollment`; a
`BroadcastSession` is created when the learner plays, so there is nothing to pre-create — a broadcast
assignment simply makes the broadcast "required."

- **Assign a course to a department** → create `Enrollment` rows for all current members of that
  department (idempotent via `uq_user_course`; existing enrollments are left untouched).
- **Assign a standalone broadcast** → no enrollment side-effect.
- **Add a member** → create `Enrollment` rows for that department's assigned **courses** (skip broadcasts).
- **Remove a member / unassign content** → **leave enrollments and `BroadcastSession`s intact.** Never
  delete progress, sessions, or `SessionAttestation`s. The requirement stops applying because "required"
  is computed from current membership + content (§5), not from the presence of an enrollment/session.
- Idempotency: check-then-insert (or catch the unique violation) so re-running a sync is safe.

---

## 7. API — `backend/routers/departments.py`, prefix `/api/departments`

All endpoints require `require_role(UserRole.ADMIN)`.

### Departments
- `GET /` — list departments with member count + assignment count.
- `POST /` — `{name, description?}` → create.
- `GET /{id}` — detail: department + members summary + assignments + light stats.
- `PATCH /{id}` — `{name?, description?, is_active?}`.
- `DELETE /{id}` — delete (cascades `department_members` + `department_content`; enrollments untouched).

### Members
- `GET /{id}/members` — list members (id, username, email, role).
- `POST /{id}/members` — `{user_ids: [int]}` → add members, then run enroll sync. Skips users already members.
- `DELETE /{id}/members/{user_id}` — remove member (enrollments left intact).

### Content (assignments)
- `GET /{id}/content` — list assignments. Each row: `id`, `content_type` (`'course'`|`'broadcast'`,
  derived), `course_id`/`broadcast_id`, `title`, `is_podcast` (true for a course-attached broadcast or
  a standalone broadcast), `mandatory`, `due_mode`, `due_date`/`due_days`.
- `POST /{id}/content` — `{course_id? , broadcast_id?, mandatory, due_mode?, due_date?, due_days?}` —
  **exactly one** of `course_id`/`broadcast_id` required → create assignment; if it's a course, run
  course enroll sync.
- `PUT /{id}/content/{content_id}` — update `mandatory` / due settings (target is immutable).
- `DELETE /{id}/content/{content_id}` — unassign (enrollments / sessions left intact).

### Compliance
- `GET /{id}/compliance` — per assignment: counts of `not_started` / `in_progress` /
  `completed` / `overdue` across members, computed with the per-type completion signal (§5) and the
  department-join-date anchor for relative deadlines. This is the query the later email job reuses.

### Validation & errors
- `404` for missing department / course / broadcast / content / user.
- `400` if neither or both of `course_id`/`broadcast_id` are supplied on assignment.
- `409` on duplicate member, duplicate `(department_id, course_id)`, or duplicate `(department_id, broadcast_id)`.
- `400` on inconsistent due config: `due_mode='fixed'` requires `due_date`; `due_mode='relative'`
  requires a positive `due_days`; a non-mandatory assignment ignores due fields.

---

## 8. Admin UI (`frontend/src/pages/admin/`)

Follows the existing pattern (`UserManagementPage`-style fetch via `@/services/api`, wrapped in
`AdminLayout`). Add a nav entry in `AdminLayout` and routes in `App.tsx`.

- **`/admin/departments`** — list table (name, # members, # assignments, active). Create (modal),
  edit, delete.
- **`/admin/departments/:id`** — department detail:
  - **Members** — list current members; "Add users" (multi-select picker from `/users`); remove.
  - **Content** — list assignments labelled **Course** vs **Podcast** (a course-attached or standalone
    broadcast). The "Assign content" picker offers **both courses (`/courses`) and standalone broadcasts
    (`/ilb/broadcasts`)** in one selector, with a **Mandatory** toggle and, when mandatory, a due-date
    control offering **fixed date** or **relative (N days from joining)**; edit and unassign per row.
  - **Compliance summary** — per mandatory assignment, counts of completed / overdue / in-progress /
    not-started (from `GET /{id}/compliance`).

---

## 9. Testing

**Backend (pytest).** Note: the repo lives on iCloud, so pytest/alembic runs are slow (minutes) but
still required.
- Model + migration: tables, constraints (both unique constraints), cascades create correctly.
- Department CRUD endpoints (incl. admin-only enforcement → 403 for non-admins).
- Membership: adding a member, and assigning a **course**, both trigger course enroll sync; a member
  added **after** a course assignment inherits the enrollment; duplicate member/assignment → 409.
- Assigning a **standalone broadcast** creates the assignment with **no** enrollment side-effect.
- Assignment payload validation: neither/both of `course_id`/`broadcast_id` → 400; missing target → 404.
- Due config validation (fixed needs date, relative needs days) → 400.
- Status computation for **both types**: not_started / in_progress / completed / overdue, including
  fixed vs relative due-date math (relative anchored on join date) and the multi-department
  "mandatory wins, earliest due date" rule. Broadcast completion = a completed `BroadcastSession`.
- Broadcast patch: completing an **enrollment-backed** `BroadcastSession` sets `Enrollment.completed`;
  completing a **standalone** broadcast session does not error (no enrollment).
- Remove-member / unassign leaves enrollments and sessions intact.

**Frontend (component tests, following the existing `ILBPlayerPage` test style).**
- `DepartmentsPage`: renders list, create flow.
- `DepartmentDetailPage`: add member; assign a course AND a standalone broadcast (picker shows both),
  with Mandatory + fixed/relative due date.

---

## 10. Out of Scope (explicitly deferred)

- **Email notifications / reminders** (the next build; this design leaves the `GET /{id}/compliance`
  "find overdue" hook ready for it).
- **Learner-facing "My required training" page.** (Auto-enroll means mandatory items still appear in
  the learner's existing course list this pass.)
- Per-user due-date overrides.
- Department hierarchy / nesting.
- Bulk member import (CSV).
