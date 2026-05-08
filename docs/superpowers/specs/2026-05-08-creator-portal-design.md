# Creator Portal — Design Spec
**Date:** 2026-05-08  
**Status:** Approved

---

## Goal

Give `creator` users a dedicated portal at `/creator/*` where they can manage their own courses, view enrollment stats, and see which learners are enrolled. Creators currently land on the admin dashboard, which exposes inappropriate admin-only features (user management, audit logs, security, whitelabel settings).

---

## Scope

- New frontend routes: `/creator`, `/creator/courses`, `/creator/courses/new`, `/creator/courses/:id`, `/creator/learners`
- New `CreatorLayout` component with its own navbar and sidebar
- Extract shared `CourseList` and `CourseEditor` components from `AdminLayout` (reused by both portals)
- Two new backend endpoints: `GET /api/creator/stats` and `GET /api/creator/learners`
- Auth routing: creators → `/creator` post-login; redirect creators away from `/admin/*`

---

## Architecture

```
/creator              CreatorDashboard    stats overview
/creator/courses      CreatorCourseList   their courses (create/edit/delete)
/creator/courses/new  CreatorCourseEditor create new course
/creator/courses/:id  CreatorCourseEditor edit existing course
/creator/learners     CreatorLearners     enrolled learners across their courses

/admin/*              AdminLayout         unchanged (admin + creator roles)
/learn/*              LearnerCatalogue    unchanged (trainee role)
```

Post-login redirect logic:
- `trainee` → `/learn`
- `creator` → `/creator`
- `admin` → `/admin`

ProtectedRoute rules:
- `/creator/*` — requires `creator` or `admin` role; trainee → `/learn`
- `/admin/*` — requires `admin` or `creator` role; creator visiting → allow (admin can also use creator portal); trainee → `/learn`
- Creator visiting `/admin/*` directly — redirect to `/creator`

---

## Component Extraction

Two components extracted from the existing `AdminLayout` in `frontend/index.html` and made standalone:

### `CourseList`
The existing courses table with create/edit/delete actions. No logic changes — `GET /api/courses` already filters by `creator_id` server-side, so creators automatically see only their own courses.

### `CourseEditor`
The full create/edit course form including AI course generation. Identical behaviour for both admin and creator — no changes to the component itself.

`AdminLayout` continues to render these components at its existing routes. `CreatorLayout` renders the same components at `/creator/courses/*`.

---

## Frontend

All changes in `frontend/index.html`.

### `CreatorLayout`

Top navbar + collapsible left sidebar. Structure mirrors `AdminLayout` but with three nav items only:

| Nav item | Route | Icon |
|---|---|---|
| Dashboard | `/creator` | grid/home |
| My Courses | `/creator/courses` | book |
| Learners | `/creator/learners` | users |

Right side of navbar: user avatar + username + Logout button.

No user management, no audit logs, no security panel, no whitelabel settings.

### `CreatorDashboard` (route: `/creator`)

Four stat cards:
- **Total Courses** — from `GET /api/creator/stats`
- **Published** — from stats response
- **Drafts** — from stats response
- **Total Enrollments** — from stats response

Below cards: "Recent Courses" table showing the creator's last 5 courses with status badge and a quick Edit link to `/creator/courses/:id`.

Loading state: skeleton cards. Error state: "Could not load stats. Please try again."

### `CreatorCourseList` (route: `/creator/courses`)

Renders the extracted `CourseList` component. The "Create Course" button navigates to `/creator/courses/new`. Edit links navigate to `/creator/courses/:id`. No other changes — the component already filters by creator server-side.

### `CreatorCourseEditor` (route: `/creator/courses/new` and `/creator/courses/:id`)

Renders the extracted `CourseEditor` component. On save, returns to `/creator/courses`. No other changes.

### `CreatorLearners` (route: `/creator/learners`)

Table of enrolled learners across all the creator's courses.

Columns: Learner name, Email, Course, Enrolled date.

Course filter dropdown at the top populated from `GET /api/courses` (their courses). Selecting a course filters the table. Default: all courses.

Data from `GET /api/creator/learners?course_id=<optional>`.

Empty state: "No learners enrolled yet." No pagination for v1.

---

## Backend

### New file: `backend/routers/creator.py`

Auth: `get_current_active_user` with role check — `creator` or `admin` only (403 otherwise).

#### `GET /api/creator/stats`

Aggregation query on the authenticated user's courses and their enrollments.

Response:
```json
{
  "total_courses": 5,
  "published_courses": 3,
  "draft_courses": 2,
  "total_enrollments": 47
}
```

#### `GET /api/creator/learners`

Query params:
- `course_id` (optional int) — filter to a specific course

Returns all enrollments for courses owned by the authenticated user (filtered by `course_id` if provided).

Response:
```json
[
  {
    "learner_name": "Jane Smith",
    "email": "jane@example.com",
    "course_id": 3,
    "course_title": "Intro to Python",
    "enrolled_at": "2026-05-01T10:00:00Z"
  }
]
```

Returns 403 if caller is not `creator` or `admin`. Returns empty array (not 404) if no enrollments.

#### Registration

Router registered in `main.py` with prefix `/api/creator`, tag `creator`.

---

## Files Changed

| File | Change |
|---|---|
| `frontend/index.html` | Extract `CourseList` and `CourseEditor` components; add `CreatorLayout`, `CreatorDashboard`, `CreatorCourseList`, `CreatorCourseEditor`, `CreatorLearners`; update routing and post-login redirects |
| `backend/routers/creator.py` | New file — `GET /api/creator/stats` and `GET /api/creator/learners` |
| `backend/main.py` | Register new `creator` router |

---

## What Is Not In Scope

- Creator analytics beyond enrollment counts (time-on-course, completion rates, etc.)
- Creators inviting or messaging learners directly
- Course-level revenue or payment tracking
- Mobile-specific creator experience
- Pagination on the learners table (add when needed)

These can be added in a future iteration.

---

## Error Handling

| Scenario | Behaviour |
|---|---|
| `GET /api/creator/stats` fails | Dashboard shows error state with retry |
| `GET /api/creator/learners` fails | Learners table shows error state with retry |
| Creator visits `/admin/*` | Redirect to `/creator` |
| Trainee visits `/creator/*` | Redirect to `/learn` |
| Unauthenticated user visits `/creator` | Redirect to `/login` |
