# Learner Portal — Design Spec
**Date:** 2026-05-08  
**Status:** Approved

---

## Goal

Add a learner-facing portal so `trainee` users can browse published courses, read course details, and launch the course player. Trainees currently land in the admin panel after login — this fixes that.

---

## Scope

- New frontend routes: `/learn` (catalogue) and `/learn/:id` (detail)
- One new backend router: `GET /api/learn/courses` and `GET /api/learn/courses/{id}`
- Auth routing: trainees → `/learn`, admins/creators → `/admin`
- Existing course player at `/courses/:id` is unchanged
- No new data models, no schema migrations

---

## Architecture

```
/learn              LearnerCatalogue    course card grid
/learn/:id          CourseDetail        description + modules + Start button
/courses/:id        CourseViewer        existing player (no changes)
/login              LoginPage           existing (no changes)
/admin/*            AdminLayout         existing (no changes)
```

Login redirect logic (in `ProtectedRoute` / post-login handler):
- `trainee` → `/learn`
- `admin` or `creator` → `/admin`
- Trainee visiting `/admin/*` → redirect to `/learn`
- Admin/creator visiting `/learn` → allowed through

---

## Backend

### New file: `backend/routers/learn.py`

Two endpoints. Auth: `get_current_active_user` (any authenticated user, no role restriction).

#### `GET /api/learn/courses`
List published courses for learners.

Query params:
- `q` (optional string) — text search on title and description
- `page` (int, default 1)
- `page_size` (int, default 20, max 50)

Filters: `status == PUBLISHED` only.

Response (JSON):
```json
{
  "total": 42,
  "page": 1,
  "page_size": 20,
  "items": [
    {
      "id": 1,
      "title": "Intro to Python",
      "description": "Learn Python from scratch.",
      "has_content": true,
      "created_at": "2026-05-01T10:00:00Z"
    }
  ]
}
```

No admin fields (no `creator_id`, no internal status metadata beyond what's needed).

#### `GET /api/learn/courses/{course_id}`
Get full detail of one published course.

Response:
```json
{
  "id": 1,
  "title": "Intro to Python",
  "description": "Learn Python from scratch.",
  "content": { ... },
  "has_content": true,
  "created_at": "2026-05-01T10:00:00Z"
}
```

Returns 404 if course does not exist or is not PUBLISHED.

#### Registration
Router registered in `main.py` with prefix `/api/learn`, tag `learn`.

### Existing endpoints reused (no changes)
- `POST /api/courses/{course_id}/enroll` — enroll any authenticated user
- `GET /api/courses/{course_id}/player` — returns HTML player

---

## Frontend

All changes are inside `frontend/index.html`. The file uses inline React + Babel. New components follow the same patterns as existing ones (functional components, `useState`/`useEffect`, `fetch` with `API_BASE`).

### New components

#### `LearnerLayout`
Top navbar only — no sidebar.
- Left: "LMS Course Builder" wordmark (or white-label brand name)
- Right: user avatar circle + username + Logout button
- White background, thin bottom border

#### `LearnerCatalogue` (route: `/learn`)
- Search bar (debounced, 300ms) below navbar
- Course grid: 3 columns on desktop, 1 on mobile (CSS grid / Tailwind)
- `CourseCard` per course:
  - Title (bold, 1 line clamped)
  - Description (2 lines clamped, grey text)
  - "Has Content" green badge if `has_content === true`
  - Created date (small, muted)
  - Entire card is clickable → navigates to `/learn/:id`
- Empty state: centred icon + "No courses available yet."
- Loading state: skeleton cards (3 placeholder cards with pulse animation)
- Error state: "Could not load courses. Please try again." with retry button
- Pagination: "Load more" button if `total > items.length`

#### `CourseDetail` (route: `/learn/:id`)
- Back link: "← Back to Courses" → `/learn`
- **Hero section**: large title, full description
- **Content section** (if `has_content`):
  - Accordion list of modules, each expandable to show lessons
  - Module name as header, lesson names as indented list items
- **Empty content**: "Course content coming soon."
- **Sticky right panel** (desktop) / bottom bar (mobile):
  - Big primary "Start Course" button → navigates to `/courses/:id`
  - Button disabled + tooltip "No content yet" if `has_content === false`
- 404 state: "Course not found." with back link

### Routing changes

In the existing `Router` / `ProtectedRoute` logic:

1. Add routes:
   ```jsx
   <Route path="/learn" element={<ProtectedRoute><LearnerCatalogue /></ProtectedRoute>} />
   <Route path="/learn/:id" element={<ProtectedRoute><CourseDetail /></ProtectedRoute>} />
   ```

2. Post-login redirect: check `user.role`:
   - `trainee` → `navigate('/learn')`
   - `admin` / `creator` → `navigate('/admin')`

3. ProtectedRoute for `/admin/*`: if `user.role === 'trainee'` → redirect to `/learn`

4. Root `/` catch-all: if `trainee` → `/learn`, else → `/admin`

---

## Error Handling

| Scenario | Behaviour |
|---|---|
| `/api/learn/courses` returns error | Show error state with retry button |
| `/api/learn/courses/:id` returns 404 | Show "Course not found" page |
| Trainee visits `/admin` | Redirected to `/learn` |
| Unauthenticated user visits `/learn` | Redirected to `/login` (existing ProtectedRoute behaviour) |
| Course has no content, user clicks Start | Button disabled with tooltip |

---

## Visual Style (Udemy-inspired)

- **Layout**: Full-width catalogue, no sidebar
- **Cards**: White background, subtle shadow, rounded corners, hover lift effect
- **Typography**: Course title in dark (`#1F2937`), description in grey (`#6B7280`)
- **Accent**: Primary blue (`#2563EB`) for buttons and links
- **Badges**: Green pill for "Has Content"
- **Start button**: Large, full-width in the sticky panel, primary blue fill

---

## What Is Not In Scope

- Progress tracking UI (progress bar on cards, % complete)
- Certificate generation
- Course ratings or reviews
- Notifications
- Mobile app

These can be added in a future iteration once the basic catalogue is working.

---

## Files Changed

| File | Change |
|---|---|
| `backend/routers/learn.py` | New file — learner read-only endpoints |
| `backend/main.py` | Register new `learn` router |
| `frontend/index.html` | Add `LearnerLayout`, `LearnerCatalogue`, `CourseDetail` components + routing changes |
