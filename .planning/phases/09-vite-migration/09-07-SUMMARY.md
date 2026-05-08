---
phase: 09-vite-migration
plan: 07
subsystem: infra
tags: [vite, react, react-router, typescript, nginx, coolify]

# Dependency graph
requires:
  - phase: 09-05
    provides: Admin pages and shared CourseManagementPage extracted from monolith
  - phase: 09-06
    provides: Creator and Learner portal pages + CourseViewerPage extracted

provides:
  - App.tsx with all 14 routes wired to real components with ProtectedRoute guards
  - main.tsx with AuthProvider + ToastProvider wrapping and setNavigate wired
  - Fully-wired Vite + React app deployed and verified on Coolify (buildbench.uk/lms)

affects: [all future frontend phases - this is the final integration of the migration]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - setNavigate singleton pattern — App.tsx calls setNavigate(navigate) in useEffect so api.ts can redirect on 401 without being a React hook
    - AuthProvider > ToastProvider > App provider nesting in main.tsx
    - ProtectedRoute wraps all authenticated routes; adminOnly/creatorRoute props for role-based guards

key-files:
  created: []
  modified:
    - frontend/src/App.tsx
    - frontend/src/main.tsx
    - frontend/src/__tests__/router.test.tsx

key-decisions:
  - "router.test.tsx updated to wrap App with AuthProvider + ToastProvider and test real component behaviour (redirect to /login when unauthenticated) rather than Todo placeholder text"

patterns-established:
  - "All authenticated routes use ProtectedRoute children pattern; adminOnly and creatorRoute boolean props control role access"
  - "setNavigate called in App-level useEffect — only place where navigate hook is called and wired to the singleton"

requirements-completed: [INFRA-01, INFRA-02, INFRA-03, INFRA-04, INFRA-05]

# Metrics
duration: ~10min
completed: 2026-05-08
---

# Phase 09 Plan 07: Final Route Wiring + Deploy Summary

**Vite + React migration complete: all 14 routes wired to real components with ProtectedRoute guards, AuthProvider + setNavigate hooked up in main.tsx, build outputs /lms/-prefixed assets, human smoke test on buildbench.uk/lms passed**

## Performance

- **Duration:** ~10 min
- **Started:** 2026-05-08T22:30:00Z
- **Completed:** 2026-05-08T22:40:00Z
- **Tasks:** 2/2 complete
- **Files modified:** 3

## Accomplishments

- App.tsx fully replaced: all 14 routes wired to real components (zero Todo placeholders remain)
- main.tsx updated with AuthProvider + ToastProvider wrapping and setNavigate import
- Build passes cleanly: 60 modules transformed, /lms/assets/ paths confirmed in dist/index.html
- All 6 unit tests pass (auth.test.tsx x3, router.test.tsx x3)
- Pre-deploy automated checks pass: /lms/assets/ in dist, no Babel CDN, try_files in nginx.conf
- Human smoke test approved: all checks passed on buildbench.uk/lms

## Task Commits

1. **Task 1: Wire App.tsx with real components and main.tsx with providers + setNavigate** - `7d3e457` (feat)
2. **Task 2: Human verification smoke test** - checkpoint approved by user (no code commit required)

## Files Created/Modified

- `frontend/src/App.tsx` - All 14 routes wired to real components with ProtectedRoute + layout wrappers; setNavigate hooked via useEffect
- `frontend/src/main.tsx` - AuthProvider + ToastProvider added wrapping App; setNavigate import present
- `frontend/src/__tests__/router.test.tsx` - Updated from Todo-placeholder assertions to real-component behaviour tests (AuthProvider wrap, redirect-to-login checks)

## Decisions Made

- router.test.tsx required a rewrite when real components replaced Todo placeholders — old tests checked for text like "LoginPage" which no longer renders; new tests verify unauthenticated redirects to /login and the login form renders

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Updated router.test.tsx for real components**
- **Found during:** Task 1 verification (npm run test:unit)
- **Issue:** router.test.tsx used Todo-placeholder text assertions ("LoginPage", "AdminDashboard", "LearnerCatalogue") and lacked AuthProvider/ToastProvider wrapping — all 3 tests threw "useAuth must be used within AuthProvider"
- **Fix:** Rewrote tests to wrap with AuthProvider + ToastProvider and assert real component behaviour (login form button present, unauthenticated routes redirect to login)
- **Files modified:** frontend/src/__tests__/router.test.tsx
- **Verification:** npm run test:unit — 6/6 tests pass
- **Committed in:** 7d3e457 (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - test update for real components)
**Impact on plan:** Necessary correctness fix. No scope creep.

## Issues Encountered

None beyond the router test update above.

## Human Verification (Smoke Test)

Task 2 was a `checkpoint:human-verify`. Human smoke test passed with all checks approved:

- Login works on buildbench.uk/lms
- All 14 routes render correct pages
- Hard refresh on /lms/admin, /lms/creator, /lms/learn all return 200
- No Babel CDN script in page source
- Asset paths start with /lms/assets/
- Existing session tokens preserved across deploy

**Status: APPROVED**

## Phase 09 Complete

- All 7 plans (09-01 through 09-07) complete
- All 27 monolith components extracted and integrated
- Vite + React migration fully deployed and verified on Coolify
- Requirements INFRA-01 through INFRA-05 satisfied
- Phase 10 is unblocked

---
*Phase: 09-vite-migration*
*Completed: 2026-05-08*
