---
phase: 09-vite-migration
plan: "04"
subsystem: auth
tags: [react, react-router-dom, typescript, vite, layout, auth-guard]

requires:
  - phase: 09-02
    provides: "useAuth, AuthProvider, User type, login/logout from AuthContext; useToast from ToastContext"
  - phase: 09-03
    provides: "Button, Input, Card common components"

provides:
  - ProtectedRoute component with adminOnly and creatorRoute guards
  - SmartRedirect component routing by role
  - AdminLayout with collapsible sidebar and 6 nav items
  - CreatorLayout with collapsible sidebar and 3 nav items
  - LearnerLayout with top navbar
  - LoginPage with username/password and MFA 202 flow

affects:
  - 09-05
  - 09-06

tech-stack:
  added: []
  patterns:
    - "Auth guards use Navigate replace=true on all redirects (no back-button loops)"
    - "Layouts define API_BASE = import.meta.env.PROD ? '/lms' : '' locally"
    - "SmartRedirect uses useEffect + useNavigate for role-based routing on mount"
    - "LoginPage navigates to '/' on success; SmartRedirect handles role routing"

key-files:
  created:
    - frontend/src/components/auth/ProtectedRoute.tsx
    - frontend/src/components/auth/SmartRedirect.tsx
    - frontend/src/components/layout/AdminLayout.tsx
    - frontend/src/components/layout/LearnerLayout.tsx
    - frontend/src/components/layout/CreatorLayout.tsx
    - frontend/src/pages/LoginPage.tsx

key-decisions:
  - "LoginPage navigates to '/' on success (not role-specific path) — SmartRedirect handles role dispatch, avoids duplicating role-routing logic"
  - "LoginResult from AuthContext does not include user object; LoginPage does not access result.user — uses navigate('/') + SmartRedirect instead"
  - "AdminLayout and CreatorLayout both define navItems as module-level const (not inside component) for stable reference"

patterns-established:
  - "Auth guard: check loading first, then auth token, then role — three-tier gate"
  - "Layout whitelabel fetch: fetch on mount with .catch(() => {}) to silently degrade"
  - "Collapsible sidebar: boolean sidebarOpen state, conditional w-64/w-20 class, toggle button at sidebar bottom"

requirements-completed:
  - INFRA-04
  - INFRA-05

duration: 8min
completed: 2026-05-08
---

# Phase 09 Plan 04: Auth Guards, Layout Shells, and Login Page Summary

**React Router auth guards (ProtectedRoute + SmartRedirect), three layout shells (Admin/Creator/Learner), and MFA-capable LoginPage extracted from monolith and typed in TypeScript**

## Performance

- **Duration:** 8 min
- **Started:** 2026-05-08T22:20:00Z
- **Completed:** 2026-05-08T22:28:00Z
- **Tasks:** 2/2
- **Files modified:** 6

## Accomplishments

- ProtectedRoute guards adminOnly and creatorRoute paths with role-based redirects using `replace` (no back-button loops)
- SmartRedirect dispatches users to /admin, /creator, or /learn on mount based on role
- AdminLayout and CreatorLayout provide collapsible sidebars with whitelabel brand name fetched from /api/whitelabel/preview
- LearnerLayout provides minimal top navbar with username display and logout
- LoginPage handles username/password form, 202 MFA challenge response, and showToast error feedback
- Build clean, all 6 existing tests pass (no regressions)

## Task Commits

1. **Task 1: Auth guards** - `da980d1` (feat)
2. **Task 2: Layout shells and LoginPage** - `35fe18c` (feat)

## Files Created/Modified

- `frontend/src/components/auth/ProtectedRoute.tsx` - Role-aware route guard wrapping children
- `frontend/src/components/auth/SmartRedirect.tsx` - Mounts and navigates to role home
- `frontend/src/components/layout/AdminLayout.tsx` - Admin sidebar with 6 nav items + collapsible
- `frontend/src/components/layout/CreatorLayout.tsx` - Creator sidebar with 3 nav items + getPageTitle()
- `frontend/src/components/layout/LearnerLayout.tsx` - Top navbar only, logout button
- `frontend/src/pages/LoginPage.tsx` - Username/password + MFA 202 flow, useToast on error

## Decisions Made

- LoginPage navigates to '/' on success rather than a role-specific path. The monolith's approach of reading `result.user?.role` doesn't work because AuthContext's `LoginResult` type doesn't include a `user` field. Navigate to '/' + SmartRedirect provides the same outcome without duplicating role-routing logic.
- AdminLayout/CreatorLayout define `navItems` as module-level const (not inside the component function) for stable reference without useMemo.

## Deviations from Plan

None — plan executed exactly as written, with one minor adaptation: LoginPage navigates to '/' (not role-specific path) because `LoginResult` doesn't carry a `user` field, matching the plan's stated intent ("On success: navigates to '/' (SmartRedirect handles role routing)").

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- All layout wrappers and auth guards are ready for import by page components in Plans 09-05 (admin pages) and 09-06 (creator pages)
- Imports: `import { ProtectedRoute } from '@/components/auth/ProtectedRoute'`, `import { AdminLayout } from '@/components/layout/AdminLayout'`, etc.
- No blockers.

---
*Phase: 09-vite-migration*
*Completed: 2026-05-08*
