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

In this system a "podcast" is not a separate entity: a podcast is a `Course` row with `ilb_published=true`
(Interactive Learning Broadcast). The assignable unit is therefore always a **Course**, and the API
surfaces `ilb_published` so the UI can label each item "Course" or "Podcast".

---

## 2. Locked Decisions

| # | Decision | Choice | Rationale |
|---|---|---|---|
| 1 | Membership cardinality | **Many-to-many** (a user can be in several departments) | Matches real orgs (e.g. someone in both Sales and Compliance) |
| 2 | Assignable unit | **Course** (podcasts are courses with `ilb_published=true`) | No separate broadcast/podcast entity exists; one assignment model covers both |
| 3 | Assignment architecture | **Explicit assignment table + auto-enroll** (Approach A) | Future joiners inherit requirements; enables real compliance reporting and the later email job |
| 4 | Due date semantics | **Per-assignment choice of fixed calendar date OR relative days** | Fixed matches "by a certain date"; relative ("within N days") is fair to late joiners |
| 5 | Source of truth for "required" | **Current membership + current assignments**, not enrollment existence | Removing a member/unassigning content must not delete progress or audit history |
| 6 | Completion signal | **`Enrollment.completed`**, unified across course types | Single check for compliance; requires patching the broadcast-complete path (see §6) |
| 7 | Scope this pass | **Backend (model + API) + admin UI** | Email reminders and a learner-facing "required training" page are deferred |

---

## 3. Architecture — Reuse vs Extend vs Build

### Reuse as-is
- **`User`** ([backend/models/models.py](../../../backend/models/models.py) ~44–71) — role enum `ADMIN`/`CREATOR`/`TRAINEE`; no schema change.
- **`Course`** (~93–137) — assignable unit; `ilb_published` distinguishes podcasts; no schema change.
- **`Enrollment`** (~139–162) — per-user/per-course progress + completion. `uq_user_course` (user_id, course_id) makes auto-enroll idempotent. No schema change.
- **`BroadcastSession`** (~499–521) — per-playthrough record for podcasts; its `completion_status='completed'` is the broadcast-finished signal.
- **Admin auth** — `require_role(UserRole.ADMIN)` ([backend/middleware/auth_middleware.py](../../../backend/middleware/auth_middleware.py) ~92–115).
- **Frontend admin pattern** — `frontend/src/pages/admin/*`, `AdminLayout`, `api.get/post/put` from `@/services/api`.

### Build (new)
- Three tables (§4), one Alembic migration `010_departments.py` (down_revision `009`).
- `backend/services/department_service.py` — auto-enroll sync + compliance status computation.
- `backend/routers/departments.py` — admin-only endpoints (§5).
- `frontend/src/pages/admin/DepartmentsPage.tsx` + `DepartmentDetailPage.tsx`, nav entry + routes.

### Patch (small, isolated)
- Broadcast-complete endpoint in [backend/routers/ilb.py](../../../backend/routers/ilb.py) (~277–305): when a `BroadcastSession` completes, also set the linked `Enrollment.completed=True` / `completed_at` (and `progress=1.0`). Today only `BroadcastSession.completion_status` is set, so podcasts never mark the enrollment complete — without this, mandatory podcasts could never register as "done". Implementation must first confirm how regular multi-module courses set `Enrollment.completed` and stay consistent with that path.

---

## 4. Data Model

One additive migration. **No columns added to existing tables.**

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

### `department_content` (the assignment record)
| Column | Type | Notes |
|---|---|---|
| id | Integer PK | |
| department_id | Integer FK → departments.id | ondelete CASCADE |
| course_id | Integer FK → courses.id | ondelete CASCADE |
| mandatory | Boolean | default false, not null |
| due_mode | String(20) | `'fixed'` \| `'relative'` \| null (only meaningful when mandatory) |
| due_date | DateTime | nullable; used when `due_mode='fixed'` |
| due_days | Integer | nullable; used when `due_mode='relative'` |
| assigned_by | Integer FK → users.id | nullable |
| created_at | DateTime | default utcnow |
| updated_at | DateTime | onupdate utcnow |

`UniqueConstraint(department_id, course_id)`; index on `course_id`.

### SQLAlchemy relationships
- `Department.members` (via `department_members`), `Department.content` (→ `department_content`, cascade delete).
- `Department.content` rows expose the related `Course` (for title + `ilb_published`).
- `User` ↔ departments association (read-only convenience query is acceptable; no requirement to back-populate).

---

## 5. Source-of-Truth Rules (computed, not stored on enrollment)

1. **Is course X mandatory for user U?** — True iff there exists a `department_content` row with
   `mandatory=true` and `course_id=X` whose `department_id` is one of U's current memberships.
2. **Multi-department resolution** — A course is mandatory if **any** of U's departments marks it
   mandatory. The **effective due date is the earliest** applicable due date across those rows.
3. **Effective due date per user**
   - `fixed` → `due_date` (same for everyone; a late joiner inherits it and may already be overdue).
   - `relative` → that user's `enrollment.enrolled_at + due_days`.
   - mandatory with no due info → required, **no hard deadline** (never "overdue").
4. **Completion** → `Enrollment.completed` (made reliable for podcasts by the §3 patch).
5. **Per-user status**
   - `not_started` — no enrollment, or enrollment with `progress == 0` and not completed.
   - `in_progress` — enrollment exists, `progress > 0`, not completed.
   - `completed` — `Enrollment.completed == true`.
   - `overdue` — not completed **and** effective due date is in the past (overrides the above for display).

---

## 6. Auto-Enroll Behaviour (`backend/services/department_service.py`)

- **Assign content to a department** → create `Enrollment` rows for all current members of that
  department (idempotent via `uq_user_course`; existing enrollments are left untouched).
- **Add a member** → create `Enrollment` rows for that department's assigned courses.
- **Remove a member / unassign content** → **leave enrollments intact.** Never delete progress,
  `BroadcastSession`s, or `SessionAttestation`s. The requirement stops applying because "required" is
  computed from current membership + content (§5), not from the presence of an enrollment row.
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
- `GET /{id}/content` — list assignments: `course_id`, title, `ilb_published`, `mandatory`, `due_mode`, `due_date`/`due_days`.
- `POST /{id}/content` — `{course_id, mandatory, due_mode?, due_date?, due_days?}` → create assignment, then run enroll sync.
- `PATCH /{id}/content/{content_id}` — update `mandatory` / due settings.
- `DELETE /{id}/content/{content_id}` — unassign (enrollments left intact).

### Compliance
- `GET /{id}/compliance` — per mandatory assignment: counts of `not_started` / `in_progress` /
  `completed` / `overdue`, with an optional per-member breakdown. This is the query the later email
  job reuses.

### Validation & errors
- `404` for missing department / course / content / user.
- `409` on duplicate member or duplicate `(department_id, course_id)` assignment.
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
  - **Content** — list assignments labelled **Course** vs **Podcast** (from `ilb_published`); "Assign
    content" picker with a **Mandatory** toggle and, when mandatory, a due-date control offering
    **fixed date** or **relative (N days)**; edit and unassign per row.
  - **Compliance summary** — per mandatory assignment, counts of completed / overdue / in-progress /
    not-started (from `GET /{id}/compliance`).

---

## 9. Testing

**Backend (pytest).** Note: the repo lives on iCloud, so pytest/alembic runs are slow (minutes) but
still required.
- Model + migration: tables, constraints, cascades create correctly.
- Department CRUD endpoints (incl. admin-only enforcement → 403 for non-admins).
- Membership: `POST /{id}/members` and `POST /{id}/content` both trigger enrollment sync; a member
  added **after** an assignment inherits it; duplicate member/assignment → 409.
- Due config validation (fixed needs date, relative needs days) → 400.
- Status computation: not_started / in_progress / completed / overdue, including fixed vs relative
  due-date math and the multi-department "mandatory wins, earliest due date" rule.
- Broadcast patch: completing a `BroadcastSession` sets the linked `Enrollment.completed`.
- Remove-member / unassign leaves enrollments intact.

**Frontend (component tests, following the existing `ILBPlayerPage` test style).**
- `DepartmentsPage`: renders list, create flow.
- `DepartmentDetailPage`: add member, assign content with Mandatory + fixed/relative due date.

---

## 10. Out of Scope (explicitly deferred)

- **Email notifications / reminders** (the next build; this design leaves the `GET /{id}/compliance`
  "find overdue" hook ready for it).
- **Learner-facing "My required training" page.** (Auto-enroll means mandatory items still appear in
  the learner's existing course list this pass.)
- Per-user due-date overrides.
- Department hierarchy / nesting.
- Bulk member import (CSV).
