---
phase: 09-vite-migration
verified: 2026-05-08T12:00:00Z
status: human_needed
score: 5/5 must-haves verified (automated)
re_verification: false
human_verification:
  - test: "Visit https://buildbench.uk/lms in incognito. Log in with admin credentials."
    expected: "Login page loads. After login, /lms/admin renders the admin dashboard. No 'text/babel' script tag in page source."
    why_human: "Production Coolify deploy cannot be verified programmatically — nginx.conf pickup, SPA fallback, and Traefik path-stripping all require live browser verification."
  - test: "Hard-refresh (Cmd+Shift+R) while on /lms/admin, /lms/creator, and /lms/learn."
    expected: "Each page returns the correct route — no 404 from nginx."
    why_human: "nginx try_files behaviour under the /lms path prefix requires a live server to confirm."
  - test: "Check browser Network tab on any page."
    expected: "All JS/CSS assets load from /lms/assets/... paths (e.g. /lms/assets/index-CXHbwQoK.js). No assets from a CDN (babel.min, cdn.tailwindcss)."
    why_human: "Asset path routing through Traefik stripprefix + nginx requires a deployed environment."
  - test: "If you had an active session before deploy, reload the app."
    expected: "Remain logged in — localStorage key 'token' is preserved across the migration."
    why_human: "Session continuity depends on the TOKEN_KEY constant matching the deployed monolith value."
---

# Phase 9: Vite Migration Verification Report

**Phase Goal:** The frontend runs as a proper Vite + React build deployed to Coolify, with all v0.1 features intact
**Verified:** 2026-05-08
**Status:** human_needed (all automated checks pass)
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| #  | Truth                                                                              | Status     | Evidence                                                                                              |
|----|------------------------------------------------------------------------------------|------------|-------------------------------------------------------------------------------------------------------|
| 1  | All 14 routes render their real components (not Todo placeholders)                 | VERIFIED   | App.tsx has 16 Route tags (14 named + 2 catch-alls), all wired to real imported components. `grep "Todo" App.tsx` returns no matches. |
| 2  | Vite build outputs dist/ with base '/lms/' asset paths                             | VERIFIED   | `dist/index.html` contains `/lms/assets/index-CXHbwQoK.js` and `/lms/assets/index-BI9xu74O.css`. `vite.config.ts` has `base: '/lms/'`. |
| 3  | nginx.conf has SPA fallback for all routes                                         | VERIFIED   | `try_files $uri $uri/ /index.html;` present in `frontend/nginx.conf`. |
| 4  | BrowserRouter uses basename=/lms; no window.history pushState usage                | VERIFIED   | `main.tsx` derives `basename` from `import.meta.env.BASE_URL` with trailing slash stripped. `App.tsx` comment references replaced pattern. No `window.history` calls in any .tsx file. |
| 5  | localStorage key 'token' is preserved (no re-login required on deploy)             | VERIFIED   | `AuthContext.tsx` line 6: `const TOKEN_KEY = 'token'` — matches monolith value with explicit preservation comment. |

**Score:** 5/5 truths verified (automated)

---

### Required Artifacts

| Artifact                                  | Expected                                             | Status     | Details                                                             |
|-------------------------------------------|------------------------------------------------------|------------|---------------------------------------------------------------------|
| `frontend/package.json`                   | Vite + React project (not Babel CDN)                 | VERIFIED   | `"vite": "^6.0.5"`, `"react": "^18.3.1"`, proper build scripts     |
| `frontend/vite.config.ts`                 | `base: '/lms/'` configured                           | VERIFIED   | Line 6: `base: '/lms/'`; outDir: 'dist'                            |
| `frontend/nginx.conf`                     | SPA try_files fallback present                       | VERIFIED   | `try_files $uri $uri/ /index.html;` on line 7                      |
| `frontend/src/main.tsx`                   | BrowserRouter with basename + providers              | VERIFIED   | `basename` derived from `BASE_URL`, `AuthProvider` + `ToastProvider` wrap App |
| `frontend/src/App.tsx`                    | 14 routes wired to real components                   | VERIFIED   | 16 Route elements total; all import real components; zero Todo stubs |
| `frontend/src/services/api.ts`            | setNavigate singleton, no window.history             | VERIFIED   | `setNavigate` exported, `navigateFn?.('/login')` in handle401       |
| `frontend/src/context/AuthContext.tsx`    | TOKEN_KEY='token'                                    | VERIFIED   | Line 6: `const TOKEN_KEY = 'token'`                                |
| `frontend/dist/`                          | Build output exists with /lms/ asset paths           | VERIFIED   | `dist/assets/` present; `dist/index.html` references `/lms/assets/` |

---

### Key Link Verification

| From                  | To                      | Via                                      | Status  | Details                                                                   |
|-----------------------|-------------------------|------------------------------------------|---------|---------------------------------------------------------------------------|
| `frontend/src/main.tsx` | `setNavigate` in api.ts | `useEffect calling setNavigate(navigate)` | WIRED  | App.tsx line 34: `useEffect(() => { setNavigate(navigate) }, [navigate])` |
| `frontend/src/App.tsx`  | `ProtectedRoute`        | wraps all authenticated routes           | WIRED   | All 13 authenticated routes use `<ProtectedRoute>` wrapper                |
| `frontend/dist`         | nginx / Coolify         | npm run build outputs dist/              | WIRED (local) | dist/ exists with correct asset paths; live verification needed           |

---

### Requirements Coverage

| Requirement | Source Plan | Description                                                                     | Status         | Evidence                                                              |
|-------------|-------------|---------------------------------------------------------------------------------|----------------|-----------------------------------------------------------------------|
| INFRA-01    | 09-07-PLAN  | Frontend built with Vite + React (replaces single-file Babel)                   | SATISFIED      | `package.json` has Vite 6, React 18; `index.html.monolith.bak` archived |
| INFRA-02    | 09-07-PLAN  | Vite build outputs to `frontend/dist/` with `base: '/lms/'`                    | SATISFIED      | `vite.config.ts` line 6 + `dist/index.html` asset paths confirmed     |
| INFRA-03    | 09-07-PLAN  | `nginx.conf` committed with SPA fallback                                        | SATISFIED      | `frontend/nginx.conf` committed; `try_files` present                  |
| INFRA-04    | 09-07-PLAN  | All existing features (auth, admin, learner, creator) continue to work          | SATISFIED (code) | All components extracted with real logic; needs live smoke test       |
| INFRA-05    | 09-07-PLAN  | React Router with `basename=/lms`; all routes functional under path prefix      | SATISFIED      | `main.tsx` derives basename from `BASE_URL`; 14 routes defined        |

All 5 INFRA requirements are accounted for. No orphaned requirements for Phase 9.

---

### Anti-Patterns Found

| File                                          | Line | Pattern                        | Severity  | Impact                                                                 |
|-----------------------------------------------|------|--------------------------------|-----------|------------------------------------------------------------------------|
| `frontend/src/pages/learn/CourseDetail.tsx`   | 103  | "Course content coming soon."  | INFO      | Conditional empty-state UI when course has no modules — not a stub. Real component with full API fetch, module accordion, and start button. |
| `frontend/vite.config.js`                     | —    | Duplicate of vite.config.ts    | WARNING   | A compiled JS version of the config exists alongside the .ts source. Vite will prefer .ts in most setups but this is redundant and could cause confusion. |

No blocker anti-patterns found. The "coming soon" text is a legitimate empty-state conditional, not a stub return.

---

### Human Verification Required

#### 1. Production Login and Admin Navigation

**Test:** Open https://buildbench.uk/lms in an incognito tab. Log in with admin credentials.
**Expected:** Login page loads; admin dashboard renders at /lms/admin; page source contains no `text/babel` script tag.
**Why human:** Coolify deployment, nginx.conf pickup, and Traefik path-stripping cannot be verified programmatically.

#### 2. Hard-Refresh SPA Routing

**Test:** While on /lms/admin, /lms/creator, and /lms/learn, press Cmd+Shift+R (hard refresh).
**Expected:** Each route returns its correct page with HTTP 200 — no nginx 404.
**Why human:** The `try_files` SPA fallback only proves itself under a running nginx serving the built dist.

#### 3. Asset Path Verification

**Test:** Open browser DevTools Network tab on any page after deploy.
**Expected:** All `.js` and `.css` assets load from `/lms/assets/...` paths. No CDN requests (no `babel.min`, no `cdn.tailwindcss`).
**Why human:** Asset routing through Traefik stripprefix requires a live environment.

#### 4. Session Token Continuity

**Test:** If you had an active session in the old Babel monolith, reload the app after deploy.
**Expected:** Remain logged in without re-entering credentials.
**Why human:** Requires a real browser localStorage state from the pre-migration monolith.

---

### Gaps Summary

No code gaps found. All five INFRA requirements are satisfied by substantive, wired implementations:

- Vite project is real (not a scaffold placeholder) — the dist/ build exists and has correct /lms/ asset paths
- nginx.conf SPA fallback is committed and correct
- BrowserRouter basename is derived from Vite's BASE_URL (not hardcoded), making it resilient
- TOKEN_KEY='token' is preserved with an explicit comment explaining the deployment risk
- All 14 routes are wired to real page components — zero Todo stubs remain

The only pending verification is the live Coolify smoke test (4 human checks above). These cannot be automated without access to the production URL.

---

_Verified: 2026-05-08_
_Verifier: Claude (gsd-verifier)_
