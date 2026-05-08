---
phase: 09-vite-migration
plan: 02
subsystem: auth
tags: [react, typescript, context, localStorage, api, vite]

# Dependency graph
requires:
  - phase: 09-01
    provides: Vite + React scaffold with TypeScript, vitest, path aliases (@/)
provides:
  - api.ts with get/post/put/delete + setNavigate singleton for 401 handling
  - AuthContext with AuthProvider, useAuth hook, loading state, TOKEN_KEY='token'
  - ToastContext with ToastProvider, useToast hook, auto-remove toasts
  - Expanded auth tests covering loading state and provider guard
affects: [09-03, 09-04, 09-05, 09-06]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Module-level navigate singleton: setNavigate(fn) called once from React Router tree; api.ts uses navigateFn?.() to redirect on 401 without useNavigate hook"
    - "TOKEN_KEY constant in AuthContext enforces 'token' key — changing breaks live user sessions"
    - "AuthProvider loading flag: starts true, set false only after localStorage hydration completes"

key-files:
  created:
    - frontend/src/services/api.ts
    - frontend/src/context/AuthContext.tsx
    - frontend/src/context/ToastContext.tsx
  modified:
    - frontend/src/__tests__/auth.test.tsx

key-decisions:
  - "api.ts reads localStorage 'token' directly rather than via TOKEN_KEY constant — AuthContext owns the key contract"
  - "fetchUserProfile uses raw fetch (not api.get) to avoid circular dependency between AuthContext and api.ts"
  - "401 handler uses navigateFn singleton (not window.location.href) to keep navigation within React Router history"

patterns-established:
  - "setNavigate singleton pattern: call setNavigate(navigate) once inside a component wrapped in BrowserRouter, then api.ts uses it for all auth redirects"
  - "useAuth/useToast guard: both hooks throw descriptive errors if called outside their Provider"

requirements-completed: [INFRA-04, INFRA-05]

# Metrics
duration: 2min
completed: 2026-05-08
---

# Phase 9 Plan 02: API Service + Auth/Toast Contexts Summary

**TypeScript api service with navigate singleton + AuthContext (loading state, TOKEN_KEY='token') + ToastContext extracted from monolith, with 6 passing unit tests**

## Performance

- **Duration:** 2 min
- **Started:** 2026-05-08T21:21:27Z
- **Completed:** 2026-05-08T21:23:00Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- api.ts extracted: all 4 HTTP methods (get/post/put/delete) with Bearer token headers, 401 handler using navigateFn singleton, API_BASE using import.meta.env.PROD
- AuthContext extracted: AuthProvider with localStorage hydration, loading state, login/logout, User type exported
- ToastContext extracted: ToastProvider with showToast auto-remove and toast list rendering
- Auth tests expanded from 1 to 3 tests: token key contract + loading state + provider guard

## Task Commits

Each task was committed atomically:

1. **Task 1: Create api service with singleton navigate pattern** - `69fd9ff` (feat)
2. **Task 2: Extract AuthContext, ToastContext and update auth tests** - `db925ff` (feat)

**Plan metadata:** (to be added with final commit)

## Files Created/Modified
- `frontend/src/services/api.ts` - HTTP api with 401 redirect via setNavigate singleton
- `frontend/src/context/AuthContext.tsx` - AuthProvider + useAuth + User type + TOKEN_KEY constant
- `frontend/src/context/ToastContext.tsx` - ToastProvider + useToast + toast list renderer
- `frontend/src/__tests__/auth.test.tsx` - Expanded from 1 to 3 tests

## Decisions Made
- api.ts reads localStorage 'token' directly rather than importing TOKEN_KEY from AuthContext — avoids a circular dependency (AuthContext imports api.ts)
- fetchUserProfile uses raw fetch rather than api.get for the same circular-dependency reason
- 401 handler uses navigateFn singleton (module-level) so api.ts can redirect without being a React hook

## Deviations from Plan
None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- api.ts, AuthContext, and ToastContext are ready for import in Plans 03-06
- Components can now import useAuth and useToast with full TypeScript types
- The User type is exported from AuthContext.tsx for use across the app
- No blockers

---
*Phase: 09-vite-migration*
*Completed: 2026-05-08*
