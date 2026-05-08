# Creator Portal Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a dedicated `/creator/*` portal so creator-role users get their own dashboard, course management, and learner enrollment view instead of landing in the admin panel.

**Architecture:** New `backend/routers/creator.py` adds two endpoints (`GET /api/creator/stats` and `GET /api/creator/learners`). The frontend gains a `CreatorLayout` (sidebar nav with Dashboard / My Courses / Learners), three creator-specific page components, and updated routing so creators land at `/creator` on login and are redirected away from `/admin/*`. The existing `CourseManagementPage` is reused unchanged inside `CreatorLayout` — it already filters courses by `creator_id` server-side.

**Tech Stack:** FastAPI, SQLAlchemy, Pydantic (backend); React 18 + Babel standalone, Tailwind CSS (frontend); pytest + FastAPI TestClient (tests).

---

## File map

| File | Action | Purpose |
|---|---|---|
| `backend/routers/creator.py` | Create | `GET /api/creator/stats` and `GET /api/creator/learners` |
| `backend/main.py` | Modify (line 26, 205) | Import and register creator router |
| `backend/tests/conftest.py` | Modify (append) | Add `creator_user`, `creator_token`, `creator_course` fixtures |
| `backend/tests/test_creator_router.py` | Create | Tests for both endpoints |
| `frontend/index.html` | Modify (multiple ranges) | ProtectedRoute, LoginPage, SmartRedirect, CreatorLayout, CreatorDashboard, CreatorLearners, App routes |

---

## Task 1: Backend — add test fixtures for creator role

**Files:**
- Modify: `backend/tests/conftest.py` (append after line 123)

- [ ] **Step 1: Append creator fixtures to conftest.py**

Add these three fixtures at the end of `backend/tests/conftest.py`:

```python
@pytest.fixture
def creator_user(db):
    user = User(
        username="creator_test",
        email="creator_test@example.com",
        hashed_password=AuthService.hash_password("pass123"),
        role=UserRole.CREATOR,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def creator_token(creator_user):
    """JWT token for the creator — created directly, no login endpoint DB writes."""
    return AuthService.create_access_token(
        user_id=creator_user.id,
        username=creator_user.username,
        role=creator_user.role.value,
    )


@pytest.fixture
def creator_course(db, creator_user):
    course = Course(
        title="Creator's Python Course",
        description="A course by the creator.",
        status=CourseStatus.PUBLISHED,
        creator_id=creator_user.id,
        content={"modules": [{"title": "Module 1", "lessons": [{"title": "Lesson 1"}]}]},
    )
    db.add(course)
    db.commit()
    db.refresh(course)
    return course
```

- [ ] **Step 2: Verify fixtures load**

Run: `cd backend && python -m pytest tests/conftest.py --collect-only -q 2>&1 | head -20`

Expected: no import errors, no fixture errors.

- [ ] **Step 3: Commit**

```bash
git add backend/tests/conftest.py
git commit -m "test: add creator_user, creator_token, creator_course fixtures"
```

---

## Task 2: Backend — write failing tests for creator router

**Files:**
- Create: `backend/tests/test_creator_router.py`

- [ ] **Step 1: Create the test file**

Create `backend/tests/test_creator_router.py`:

```python
"""Tests for GET /api/creator/stats and GET /api/creator/learners."""
import pytest
from models import Enrollment, CourseStatus


class TestCreatorStats:

    def test_unauthenticated_returns_401(self, client):
        res = client.get("/api/creator/stats")
        assert res.status_code in (401, 403)

    def test_trainee_returns_403(self, client, trainee_token):
        res = client.get(
            "/api/creator/stats",
            headers={"Authorization": f"Bearer {trainee_token}"},
        )
        assert res.status_code == 403

    def test_creator_with_no_courses_returns_zeros(self, client, creator_token):
        res = client.get(
            "/api/creator/stats",
            headers={"Authorization": f"Bearer {creator_token}"},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["total_courses"] == 0
        assert data["published_courses"] == 0
        assert data["draft_courses"] == 0
        assert data["total_enrollments"] == 0

    def test_counts_only_own_courses(self, client, creator_token, creator_course, published_course):
        # published_course belongs to admin_user, not creator_user
        res = client.get(
            "/api/creator/stats",
            headers={"Authorization": f"Bearer {creator_token}"},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["total_courses"] == 1
        assert data["published_courses"] == 1
        assert data["draft_courses"] == 0

    def test_enrollment_count(self, client, creator_token, creator_course, trainee_user, db):
        enrollment = Enrollment(
            user_id=trainee_user.id,
            course_id=creator_course.id,
        )
        db.add(enrollment)
        db.commit()

        res = client.get(
            "/api/creator/stats",
            headers={"Authorization": f"Bearer {creator_token}"},
        )
        assert res.status_code == 200
        assert res.json()["total_enrollments"] == 1

    def test_response_shape(self, client, creator_token):
        res = client.get(
            "/api/creator/stats",
            headers={"Authorization": f"Bearer {creator_token}"},
        )
        assert res.status_code == 200
        data = res.json()
        assert "total_courses" in data
        assert "published_courses" in data
        assert "draft_courses" in data
        assert "total_enrollments" in data


class TestCreatorLearners:

    def test_unauthenticated_returns_401(self, client):
        res = client.get("/api/creator/learners")
        assert res.status_code in (401, 403)

    def test_trainee_returns_403(self, client, trainee_token):
        res = client.get(
            "/api/creator/learners",
            headers={"Authorization": f"Bearer {trainee_token}"},
        )
        assert res.status_code == 403

    def test_no_enrollments_returns_empty_list(self, client, creator_token, creator_course):
        res = client.get(
            "/api/creator/learners",
            headers={"Authorization": f"Bearer {creator_token}"},
        )
        assert res.status_code == 200
        assert res.json() == []

    def test_returns_enrolled_learner(self, client, creator_token, creator_course, trainee_user, db):
        enrollment = Enrollment(
            user_id=trainee_user.id,
            course_id=creator_course.id,
        )
        db.add(enrollment)
        db.commit()

        res = client.get(
            "/api/creator/learners",
            headers={"Authorization": f"Bearer {creator_token}"},
        )
        assert res.status_code == 200
        data = res.json()
        assert len(data) == 1
        assert data[0]["learner_name"] == trainee_user.username
        assert data[0]["email"] == trainee_user.email
        assert data[0]["course_id"] == creator_course.id
        assert data[0]["course_title"] == creator_course.title
        assert "enrolled_at" in data[0]

    def test_course_id_filter(self, client, creator_token, creator_course, trainee_user, db):
        enrollment = Enrollment(
            user_id=trainee_user.id,
            course_id=creator_course.id,
        )
        db.add(enrollment)
        db.commit()

        # Filter to the correct course — should return 1
        res = client.get(
            f"/api/creator/learners?course_id={creator_course.id}",
            headers={"Authorization": f"Bearer {creator_token}"},
        )
        assert res.status_code == 200
        assert len(res.json()) == 1

    def test_course_id_filter_wrong_course_returns_empty(self, client, creator_token, creator_course, trainee_user, db):
        enrollment = Enrollment(
            user_id=trainee_user.id,
            course_id=creator_course.id,
        )
        db.add(enrollment)
        db.commit()

        # Filter to a non-existent course_id — should return empty (not an error)
        res = client.get(
            "/api/creator/learners?course_id=99999",
            headers={"Authorization": f"Bearer {creator_token}"},
        )
        assert res.status_code == 200
        assert res.json() == []

    def test_does_not_return_other_creators_learners(self, client, creator_token, published_course, trainee_user, db):
        # published_course belongs to admin_user, not creator_user
        enrollment = Enrollment(
            user_id=trainee_user.id,
            course_id=published_course.id,
        )
        db.add(enrollment)
        db.commit()

        res = client.get(
            "/api/creator/learners",
            headers={"Authorization": f"Bearer {creator_token}"},
        )
        assert res.status_code == 200
        assert res.json() == []
```

- [ ] **Step 2: Run tests — verify they fail with 404 (router not implemented yet)**

Run: `cd backend && python -m pytest tests/test_creator_router.py -v 2>&1 | tail -20`

Expected: all tests FAIL with connection errors or 404s because `/api/creator/*` doesn't exist yet.

---

## Task 3: Backend — implement creator router

**Files:**
- Create: `backend/routers/creator.py`
- Modify: `backend/main.py` line 26 (import) and line ~205 (register)

- [ ] **Step 1: Create backend/routers/creator.py**

```python
"""
Creator-facing endpoints for stats and learner management.
Available to creator and admin roles only.
"""

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List, Optional
import logging

from database import get_db
from models import User, Course, CourseStatus, Enrollment
from middleware.auth_middleware import require_creator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/creator", tags=["creator"])


class CreatorStatsResponse(BaseModel):
    total_courses: int
    published_courses: int
    draft_courses: int
    total_enrollments: int


class LearnerEnrollmentResponse(BaseModel):
    learner_name: str
    email: str
    course_id: int
    course_title: str
    enrolled_at: datetime

    class Config:
        from_attributes = True


@router.get("/stats", response_model=CreatorStatsResponse)
def get_creator_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_creator),
) -> CreatorStatsResponse:
    """Return course and enrollment stats for the current creator."""
    courses = db.query(Course).filter(Course.creator_id == current_user.id).all()

    total = len(courses)
    published = sum(1 for c in courses if c.status == CourseStatus.PUBLISHED)
    draft = sum(1 for c in courses if c.status == CourseStatus.DRAFT)

    course_ids = [c.id for c in courses]
    enrollments = (
        db.query(Enrollment).filter(Enrollment.course_id.in_(course_ids)).count()
        if course_ids
        else 0
    )

    logger.info(f"Creator stats: user={current_user.id}, courses={total}, enrollments={enrollments}")
    return CreatorStatsResponse(
        total_courses=total,
        published_courses=published,
        draft_courses=draft,
        total_enrollments=enrollments,
    )


@router.get("/learners", response_model=List[LearnerEnrollmentResponse])
def get_creator_learners(
    course_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_creator),
) -> List[LearnerEnrollmentResponse]:
    """Return all learners enrolled in the current creator's courses."""
    course_query = db.query(Course).filter(Course.creator_id == current_user.id)
    if course_id is not None:
        course_query = course_query.filter(Course.id == course_id)
    courses = course_query.all()
    course_map = {c.id: c.title for c in courses}

    if not course_map:
        return []

    enrollments = (
        db.query(Enrollment)
        .filter(Enrollment.course_id.in_(course_map.keys()))
        .all()
    )

    result = []
    for e in enrollments:
        user = db.query(User).filter(User.id == e.user_id).first()
        if user:
            result.append(
                LearnerEnrollmentResponse(
                    learner_name=user.username,
                    email=user.email,
                    course_id=e.course_id,
                    course_title=course_map[e.course_id],
                    enrolled_at=e.enrolled_at,
                )
            )

    logger.info(f"Creator learners: user={current_user.id}, count={len(result)}")
    return result
```

- [ ] **Step 2: Register creator router in main.py**

In `backend/main.py`, line 26, change:
```python
from routers import admin, auth, users, courses, security, dev_tools, whitelabel, learn
```
to:
```python
from routers import admin, auth, users, courses, security, dev_tools, whitelabel, learn, creator
```

Then find the `app.include_router(learn.router)` line (~line 205) and add after it:
```python
app.include_router(creator.router)
```

- [ ] **Step 3: Run all creator tests — verify they pass**

Run: `cd backend && python -m pytest tests/test_creator_router.py -v 2>&1 | tail -30`

Expected: all 13 tests PASS.

- [ ] **Step 4: Run full test suite — verify nothing broken**

Run: `cd backend && python -m pytest tests/ -v 2>&1 | tail -20`

Expected: all tests PASS (no regressions).

- [ ] **Step 5: Commit**

```bash
git add backend/routers/creator.py backend/main.py backend/tests/test_creator_router.py
git commit -m "feat: add creator router with stats and learners endpoints"
```

---

## Task 4: Frontend — ProtectedRoute, LoginPage redirect, SmartRedirect, catch-all

**Files:**
- Modify: `frontend/index.html`

### What to change

**1. ProtectedRoute** (around line 560) — add `creatorRoute` prop and creator-to-`/creator` redirect on admin routes.

Replace the existing `ProtectedRoute` component:
```javascript
        const ProtectedRoute = ({ children, adminOnly = false }) => {
            const { auth, loading, user } = useAuth();
            const { pathname } = useLocation();

            if (loading) {
                return <div className="flex items-center justify-center h-screen"><div className="spin text-4xl">⏳</div></div>;
            }

            if (!auth) return <Navigate to="/login" />;

            // Trainees must not access admin routes
            if (adminOnly && user?.role === 'trainee') return <Navigate to="/learn" />;

            return children;
        };
```
With:
```javascript
        const ProtectedRoute = ({ children, adminOnly = false, creatorRoute = false }) => {
            const { auth, loading, user } = useAuth();
            const { pathname } = useLocation();

            if (loading) {
                return <div className="flex items-center justify-center h-screen"><div className="spin text-4xl">⏳</div></div>;
            }

            if (!auth) return <Navigate to="/login" />;

            // Admin routes: trainees → /learn, creators → /creator
            if (adminOnly) {
                if (user?.role === 'trainee') return <Navigate to="/learn" />;
                if (user?.role === 'creator') return <Navigate to="/creator" />;
            }

            // Creator routes: trainees → /learn
            if (creatorRoute && user?.role === 'trainee') return <Navigate to="/learn" />;

            return children;
        };
```

**2. LoginPage redirect** (around line 949) — add creator branch.

Replace:
```javascript
                    const dest = result.user?.role === 'trainee' ? '/learn' : '/admin';
```
With:
```javascript
                    const dest = result.user?.role === 'trainee' ? '/learn' : result.user?.role === 'creator' ? '/creator' : '/admin';
```

**3. SmartRedirect component** — add just before `const LoginPage` (around line 900). This is used by catch-all routes.

Add:
```javascript
        const SmartRedirect = () => {
            const { user, loading } = useAuth();
            const nav = useNavigate();
            useEffect(() => {
                if (loading) return;
                if (!user) nav('/login');
                else if (user.role === 'trainee') nav('/learn');
                else if (user.role === 'creator') nav('/creator');
                else nav('/admin');
            }, [user, loading]);
            return null;
        };
```

**4. Catch-all routes** (lines 3028-3029) — replace `<Navigate to="/learn" />` with `<SmartRedirect />`.

Replace:
```javascript
                        <Route path="/" element={<Navigate to="/learn" />} />
                        <Route path="*" element={<Navigate to="/learn" />} />
```
With:
```javascript
                        <Route path="/" element={<SmartRedirect />} />
                        <Route path="*" element={<SmartRedirect />} />
```

- [ ] **Step 1: Apply all four changes above to frontend/index.html**

- [ ] **Step 2: Manual smoke test — verify syntax**

Run: `node -e "const fs=require('fs'); const src=fs.readFileSync('frontend/index.html','utf8'); console.log('lines:', src.split('\n').length, '— OK')"`

Expected: prints line count without error.

- [ ] **Step 3: Commit**

```bash
git add frontend/index.html
git commit -m "feat: creator-aware ProtectedRoute, login redirect, and SmartRedirect catch-all"
```

---

## Task 5: Frontend — CreatorLayout component

**Files:**
- Modify: `frontend/index.html` (add after LearnerLayout, around line 616)

- [ ] **Step 1: Add CreatorLayout after the LearnerLayout closing brace (after line 616)**

Insert the following block between the end of `LearnerLayout` and the start of `LearnerCatalogue`:

```javascript
        // ============= CREATOR PORTAL =============

        const CreatorLayout = ({ children }) => {
            const { user, logout } = useAuth();
            const location = useLocation();
            const navigate = useNavigate();
            const [sidebarOpen, setSidebarOpen] = useState(true);
            const [brandName, setBrandName] = useState('LMS Course Builder');

            useEffect(() => {
                fetch(API_BASE + '/api/whitelabel/preview')
                    .then(r => r.ok ? r.json() : null)
                    .then(d => d && setBrandName(d.brand_name || 'LMS Course Builder'))
                    .catch(() => {});
            }, []);

            const navItems = [
                { label: 'Dashboard', path: '/creator', icon: '📊' },
                { label: 'My Courses', path: '/creator/courses', icon: '📚' },
                { label: 'Learners', path: '/creator/learners', icon: '👥' },
            ];

            const getPageTitle = () => {
                const item = navItems.find(n => n.path === location.pathname);
                return item ? item.label : 'Creator Portal';
            };

            return (
                <div className="flex h-screen bg-gray-100">
                    {/* Sidebar */}
                    <div className={`${sidebarOpen ? 'w-64' : 'w-20'} bg-gray-900 text-white transition-all duration-200 flex flex-col`}>
                        <div className="p-4 border-b border-gray-700">
                            <h1 className={`font-bold ${sidebarOpen ? 'text-lg' : 'text-xs text-center'}`}>
                                {sidebarOpen ? brandName : '◉'}
                            </h1>
                        </div>

                        <nav className="flex-1 p-4 space-y-2">
                            {navItems.map(item => (
                                <button
                                    key={item.path}
                                    onClick={() => navigate(item.path)}
                                    className={`w-full flex items-center space-x-3 px-3 py-2 rounded-lg transition ${location.pathname === item.path ? 'bg-blue-600' : 'hover:bg-gray-800'}`}
                                >
                                    <span className="text-xl">{item.icon}</span>
                                    {sidebarOpen && <span>{item.label}</span>}
                                </button>
                            ))}
                        </nav>

                        <div className="p-4 border-t border-gray-700 space-y-2">
                            <button
                                onClick={() => setSidebarOpen(!sidebarOpen)}
                                className="w-full flex items-center justify-center px-3 py-2 rounded-lg hover:bg-gray-800 transition text-sm"
                            >
                                {sidebarOpen ? '◀' : '▶'}
                            </button>
                            <button
                                onClick={() => { logout(); navigate('/login'); }}
                                className="w-full flex items-center space-x-3 px-3 py-2 rounded-lg hover:bg-gray-800 transition text-red-400"
                            >
                                <span className="text-xl">🚪</span>
                                {sidebarOpen && <span>Logout</span>}
                            </button>
                        </div>
                    </div>

                    {/* Main Content */}
                    <div className="flex-1 flex flex-col">
                        {/* Top Bar */}
                        <div className="bg-white border-b border-gray-200 p-4 flex justify-between items-center shadow-sm">
                            <h2 className="text-2xl font-bold">{getPageTitle()}</h2>
                            <div className="flex items-center space-x-4">
                                {user && (
                                    <div className="flex items-center space-x-2">
                                        <div className="w-10 h-10 rounded-full bg-indigo-600 text-white flex items-center justify-center font-bold">
                                            {user.username?.charAt(0).toUpperCase()}
                                        </div>
                                        <div className="text-sm">
                                            <p className="font-medium">{user.username}</p>
                                            <p className="text-gray-500 text-xs">{user.role}</p>
                                        </div>
                                    </div>
                                )}
                            </div>
                        </div>

                        {/* Page Content */}
                        <div className="flex-1 overflow-auto p-6">
                            {children}
                        </div>
                    </div>
                </div>
            );
        };
```

- [ ] **Step 2: Commit**

```bash
git add frontend/index.html
git commit -m "feat: add CreatorLayout component"
```

---

## Task 6: Frontend — CreatorDashboard component

**Files:**
- Modify: `frontend/index.html` (add after CreatorLayout, before LearnerCatalogue)

- [ ] **Step 1: Add CreatorDashboard component immediately after CreatorLayout**

Insert after the closing `};` of `CreatorLayout`:

```javascript
        const CreatorDashboard = () => {
            const [stats, setStats] = useState(null);
            const [recentCourses, setRecentCourses] = useState([]);
            const [loading, setLoading] = useState(true);
            const [error, setError] = useState('');
            const { user } = useAuth();
            const navigate = useNavigate();

            useEffect(() => {
                fetchDashboard();
            }, []);

            const fetchDashboard = async () => {
                setLoading(true);
                setError('');
                try {
                    const [statsRes, coursesRes] = await Promise.all([
                        api.get('/creator/stats'),
                        api.get('/courses'),
                    ]);
                    if (statsRes.ok) setStats(await statsRes.json());
                    else setError('Could not load stats.');
                    if (coursesRes.ok) {
                        const d = await coursesRes.json();
                        const list = Array.isArray(d) ? d : d.items || [];
                        setRecentCourses(list.slice(0, 5));
                    }
                } catch (err) {
                    setError('Could not load dashboard. Please try again.');
                } finally {
                    setLoading(false);
                }
            };

            const StatCard = ({ title, value, icon }) => (
                <Card className="p-6">
                    <div className="flex items-center justify-between">
                        <div>
                            <p className="text-gray-600 text-sm">{title}</p>
                            <p className="text-3xl font-bold mt-2">{value ?? '—'}</p>
                        </div>
                        <div className="text-4xl">{icon}</div>
                    </div>
                </Card>
            );

            if (loading) {
                return <div className="text-center py-12"><div className="spin text-4xl inline-block">⏳</div></div>;
            }

            if (error) {
                return (
                    <div className="text-center py-12">
                        <p className="text-red-600 mb-4">{error}</p>
                        <button onClick={fetchDashboard} className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700">
                            Retry
                        </button>
                    </div>
                );
            }

            return (
                <div className="space-y-6">
                    <div className="bg-indigo-50 border-l-4 border-indigo-500 p-4 rounded">
                        <p className="text-lg font-semibold">Welcome, {user?.username}! 👋</p>
                        <p className="text-gray-600 text-sm mt-1">Here's an overview of your courses and learners.</p>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                        <StatCard title="Total Courses" value={stats?.total_courses} icon="📚" />
                        <StatCard title="Published" value={stats?.published_courses} icon="✅" />
                        <StatCard title="Drafts" value={stats?.draft_courses} icon="📝" />
                        <StatCard title="Total Enrollments" value={stats?.total_enrollments} icon="👥" />
                    </div>

                    <Card className="p-6">
                        <div className="flex items-center justify-between mb-4">
                            <h3 className="text-lg font-semibold">Recent Courses</h3>
                            <button
                                onClick={() => navigate('/creator/courses')}
                                className="text-sm text-blue-600 hover:underline"
                            >
                                View all →
                            </button>
                        </div>
                        {recentCourses.length === 0 ? (
                            <p className="text-gray-500 text-sm">No courses yet. <button onClick={() => navigate('/creator/courses')} className="text-blue-600 hover:underline">Create your first course →</button></p>
                        ) : (
                            <table className="w-full text-sm">
                                <thead>
                                    <tr className="text-left text-gray-500 border-b">
                                        <th className="pb-2 font-medium">Title</th>
                                        <th className="pb-2 font-medium">Status</th>
                                        <th className="pb-2 font-medium"></th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {recentCourses.map(c => (
                                        <tr key={c.id} className="border-b last:border-0">
                                            <td className="py-2 font-medium text-gray-900">{c.title}</td>
                                            <td className="py-2">
                                                <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${c.status === 'published' ? 'bg-green-100 text-green-700' : 'bg-yellow-100 text-yellow-700'}`}>
                                                    {c.status}
                                                </span>
                                            </td>
                                            <td className="py-2 text-right">
                                                <button
                                                    onClick={() => navigate('/creator/courses')}
                                                    className="text-blue-600 hover:underline text-xs"
                                                >
                                                    Edit
                                                </button>
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        )}
                    </Card>
                </div>
            );
        };
```

- [ ] **Step 2: Commit**

```bash
git add frontend/index.html
git commit -m "feat: add CreatorDashboard component"
```

---

## Task 7: Frontend — CreatorLearners component

**Files:**
- Modify: `frontend/index.html` (add after CreatorDashboard)

- [ ] **Step 1: Add CreatorLearners component immediately after CreatorDashboard**

Insert after the closing `};` of `CreatorDashboard`:

```javascript
        const CreatorLearners = () => {
            const [learners, setLearners] = useState([]);
            const [courses, setCourses] = useState([]);
            const [selectedCourse, setSelectedCourse] = useState('');
            const [loading, setLoading] = useState(true);
            const [error, setError] = useState('');

            useEffect(() => {
                fetchCourses();
            }, []);

            useEffect(() => {
                fetchLearners();
            }, [selectedCourse]);

            const fetchCourses = async () => {
                try {
                    const res = await api.get('/courses');
                    if (res.ok) {
                        const d = await res.json();
                        setCourses(Array.isArray(d) ? d : d.items || []);
                    }
                } catch (err) {
                    console.error('Failed to load courses', err);
                }
            };

            const fetchLearners = async () => {
                setLoading(true);
                setError('');
                try {
                    const path = '/creator/learners' + (selectedCourse ? `?course_id=${selectedCourse}` : '');
                    const res = await api.get(path);
                    if (res.ok) {
                        setLearners(await res.json());
                    } else {
                        setError('Could not load learners.');
                    }
                } catch (err) {
                    setError('Could not load learners. Please try again.');
                } finally {
                    setLoading(false);
                }
            };

            return (
                <div className="space-y-4">
                    <div className="flex items-center gap-4">
                        <select
                            value={selectedCourse}
                            onChange={e => setSelectedCourse(e.target.value)}
                            className="border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                        >
                            <option value="">All Courses</option>
                            {courses.map(c => (
                                <option key={c.id} value={c.id}>{c.title}</option>
                            ))}
                        </select>
                    </div>

                    {loading ? (
                        <div className="text-center py-12"><div className="spin text-4xl inline-block">⏳</div></div>
                    ) : error ? (
                        <div className="text-center py-12">
                            <p className="text-red-600 mb-4">{error}</p>
                            <button onClick={fetchLearners} className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700">Retry</button>
                        </div>
                    ) : learners.length === 0 ? (
                        <Card className="p-12 text-center">
                            <p className="text-4xl mb-3">👥</p>
                            <p className="text-gray-600">No learners enrolled yet.</p>
                        </Card>
                    ) : (
                        <Card className="overflow-hidden">
                            <table className="w-full text-sm">
                                <thead className="bg-gray-50 border-b">
                                    <tr className="text-left text-gray-500">
                                        <th className="px-4 py-3 font-medium">Learner</th>
                                        <th className="px-4 py-3 font-medium">Email</th>
                                        <th className="px-4 py-3 font-medium">Course</th>
                                        <th className="px-4 py-3 font-medium">Enrolled</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {learners.map((l, i) => (
                                        <tr key={i} className="border-b last:border-0 hover:bg-gray-50">
                                            <td className="px-4 py-3 font-medium text-gray-900">{l.learner_name}</td>
                                            <td className="px-4 py-3 text-gray-600">{l.email}</td>
                                            <td className="px-4 py-3 text-gray-700">{l.course_title}</td>
                                            <td className="px-4 py-3 text-gray-500">{new Date(l.enrolled_at).toLocaleDateString()}</td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </Card>
                    )}
                </div>
            );
        };
```

- [ ] **Step 2: Commit**

```bash
git add frontend/index.html
git commit -m "feat: add CreatorLearners component"
```

---

## Task 8: Frontend — add creator routes to App

**Files:**
- Modify: `frontend/index.html` (App component, around line 2999)

- [ ] **Step 1: Add three creator routes inside the Routes block in App**

Find the closing `</Route>` of the `/admin/whitelabel` route (around line 2998) and insert the following three routes immediately after it, before the `/courses/:id` route:

```javascript
                        <Route
                            path="/creator"
                            element={
                                <ProtectedRoute creatorRoute={true}>
                                    <CreatorLayout>
                                        <CreatorDashboard />
                                    </CreatorLayout>
                                </ProtectedRoute>
                            }
                        />
                        <Route
                            path="/creator/courses"
                            element={
                                <ProtectedRoute creatorRoute={true}>
                                    <CreatorLayout>
                                        <CourseManagementPage />
                                    </CreatorLayout>
                                </ProtectedRoute>
                            }
                        />
                        <Route
                            path="/creator/learners"
                            element={
                                <ProtectedRoute creatorRoute={true}>
                                    <CreatorLayout>
                                        <CreatorLearners />
                                    </CreatorLayout>
                                </ProtectedRoute>
                            }
                        />
```

- [ ] **Step 2: Verify syntax**

Run: `node -e "const fs=require('fs'); const src=fs.readFileSync('frontend/index.html','utf8'); console.log('lines:', src.split('\n').length, '— OK')"`

Expected: prints line count without error.

- [ ] **Step 3: Commit**

```bash
git add frontend/index.html
git commit -m "feat: add /creator/* routes to App"
```

---

## Task 9: Deploy and verify

- [ ] **Step 1: Push to remote**

```bash
git push
```

- [ ] **Step 2: Deploy backend in Coolify**

Trigger a redeploy of the LMS backend service in Coolify. Wait for "Running" status.

- [ ] **Step 3: Deploy frontend in Coolify**

Trigger a redeploy of the LMS frontend service in Coolify. Wait for "Running" status (should take ~15–20 seconds with the nixpacks staticfile provider).

- [ ] **Step 4: Verify creator login flow**

1. Go to `https://buildbench.uk/lms/login`
2. Log in as a creator-role user
3. Confirm you land at `https://buildbench.uk/lms/creator` (not `/admin`)
4. Confirm the sidebar shows: Dashboard, My Courses, Learners
5. Click My Courses — confirm `CourseManagementPage` loads and shows only the creator's courses
6. Click Learners — confirm the learners table loads (empty state if no enrollments)

- [ ] **Step 5: Verify admin redirect**

1. Log in as admin
2. Confirm you land at `/admin` (unchanged)
3. Navigate to `/creator` — confirm you can access it (admin allowed through)

- [ ] **Step 6: Verify trainee cannot access creator portal**

1. Log in as a trainee
2. Manually navigate to `https://buildbench.uk/lms/creator`
3. Confirm you are redirected to `/learn`

- [ ] **Step 7: Verify creator cannot access admin portal**

1. Log in as a creator
2. Manually navigate to `https://buildbench.uk/lms/admin`
3. Confirm you are redirected to `/creator`
