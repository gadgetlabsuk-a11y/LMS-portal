# Phase 9: Vite Migration - Research

**Researched:** 2026-05-08
**Domain:** Vite 6 + React 18 + TypeScript — single-file Babel-to-build-tool migration, path-prefix deployment on Coolify/Traefik/nginx
**Confidence:** HIGH

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| INFRA-01 | Frontend is built with Vite + React (replaces single-file Babel; proper build step) | Vite 6 setup via `npm create vite@latest`, `@vitejs/plugin-react`, TypeScript template |
| INFRA-02 | Vite build outputs to `frontend/dist/` with `base: '/lms/'` (compatible with existing Traefik stripprefix + nginx setup) | `base: '/lms/'` in `vite.config.ts`; `build.outDir` defaults to `dist` — no override needed |
| INFRA-03 | `nginx.conf` committed to the repo with SPA fallback for all routes | Custom `nginx.conf` with `try_files $uri $uri/ /index.html`; nixpacks Staticfile is fragile and must be replaced |
| INFRA-04 | All existing features (auth, admin panel, learner portal, creator portal) continue to work after migration | Full component inventory extracted; `localStorage` key `'token'` must be preserved exactly; API_BASE logic must be replicated |
| INFRA-05 | React Router operates with `basename=/lms`; all routes functional under path prefix | `<BrowserRouter basename="/lms">` (no trailing slash); router replaces custom hand-rolled `RouterCtx` |
</phase_requirements>

---

## Summary

Phase 9 migrates the frontend from a monolithic 3420-line `frontend/index.html` (React 18 + Babel standalone, CDN Tailwind, hand-rolled router) to a proper Vite 6 + React 18 + TypeScript build. The existing file is a complete, working SPA: it contains a custom router, AuthContext, a toast system, a full set of page components (LoginPage, AdminDashboard, UserManagementPage, CourseManagementPage, SecurityPage, DevToolsPage, WhiteLabelPage, CreatorDashboard, CreatorLearners, LearnerCatalogue, CourseDetail, CourseViewerPage), and a shared API service object.

The deployment constraint is already well-understood from 5 nginx emergency commits in this repo: Traefik strips `/lms` from URLs before forwarding to nginx; Vite `base` and React Router `basename` are set to `/lms/` and `/lms` respectively to make asset URLs correct in the built HTML, while nginx itself serves from path `/`. The existing nixpacks `Staticfile` at `frontend/Staticfile` must be replaced by a committed `nginx.conf` to prevent opaque auto-generated config from breaking SPA deep links.

The `frontend/src/` skeleton already exists (empty subdirectories: `components/admin`, `components/auth`, `components/common`, `components/course`, `components/layout`, `context/`, `hooks/`, `pages/`, `services/`, `styles/`) — Vite project initialisation must populate this structure. The CI workflow (`frontend-build` job in `.github/workflows/ci.yml`) already expects `npm ci && npm run build` to succeed in `frontend/`, confirming the target structure. No package.json currently exists in `frontend/`, so all scaffolding is Wave 0.

**Primary recommendation:** Scaffold Vite + React + TypeScript in `frontend/`, migrate the monolith by extracting each named component into the matching `src/` subdirectory, then verify deployment on Coolify staging before closing the phase.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Vite | 6.x | Build tool, dev server, HMR | Fastest cold start and HMR; official React plugin; `base` config cleanly handles /lms subpath |
| React | 18.3.x | UI framework | Already proven in this codebase; React 19 ecosystem lag is real — stay on 18.3 for v1 |
| TypeScript | 5.x | Type safety | First-class support across all chosen libraries; prevents data model bugs in future phases |
| react-router-dom | 6.28.x | SPA routing | Replaces hand-rolled `RouterCtx`; v6 `<BrowserRouter basename>` is the correct primitive |
| @vitejs/plugin-react | 4.x | Babel fast refresh | Use this NOT `@vitejs/plugin-react-swc` — swc has edge cases with TipTap (needed in Phase 14) |

### Supporting (Phase 9 scope only)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Tailwind CSS | 3.4.x | Utility styling | Replaces CDN `<script src="https://cdn.tailwindcss.com">` with PostCSS pipeline |
| vite-tsconfig-paths | 5.x | Path alias resolution (`@/`) | Avoids deep relative imports in nested component tree |
| @types/react | 18.3.x | TypeScript defs | Required peer for TypeScript projects |
| @types/react-dom | 18.3.x | TypeScript defs | Required peer |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| @vitejs/plugin-react (Babel) | @vitejs/plugin-react-swc | SWC is faster but has edge cases with TipTap ProseMirror — not worth the risk |
| react-router-dom v6 | v7 Framework mode | v7 Framework mode adds file-based routing and SSR complexity with no benefit for this SPA |
| Tailwind 3.4 | Tailwind 4 | Tailwind 4 rewrites configuration format; ecosystem (shadcn/ui) still on 3.4; migrate later |

**Installation:**
```bash
# In frontend/ directory — scaffolds Vite + React + TypeScript
npm create vite@latest . -- --template react-ts

# Routing
npm install react-router-dom@6

# Styling
npm install tailwindcss@3 postcss autoprefixer
npx tailwindcss init -p

# Dev tools
npm install -D vite-tsconfig-paths @types/react @types/react-dom
```

---

## Architecture Patterns

### Recommended Project Structure

```
frontend/
├── index.html              # Vite entry point (minimal shell — just <div id="root">)
├── vite.config.ts          # base: '/lms/', outDir: dist (default)
├── tailwind.config.js      # content: ['./src/**/*.{ts,tsx}']
├── tsconfig.json           # strict mode, path alias @/ -> src/
├── nginx.conf              # committed SPA fallback config (replaces Staticfile)
├── package.json
├── public/
│   └── favicon.ico
└── src/
    ├── main.tsx            # createRoot, BrowserRouter with basename="/lms"
    ├── App.tsx             # <Routes> tree (maps 1:1 from existing index.html App)
    ├── context/
    │   ├── AuthContext.tsx  # AuthProvider, useAuth — extract from index.html lines 262–341
    │   └── ToastContext.tsx # ToastProvider, useToast — extract from index.html lines 422–453
    ├── services/
    │   └── api.ts          # api.get/post/put/delete — extract from index.html lines 344–418
    ├── components/
    │   ├── common/         # Modal, Button, Card, Badge, Input, Select, Textarea
    │   ├── layout/         # AdminLayout, LearnerLayout, CreatorLayout
    │   ├── auth/           # ProtectedRoute, SmartRedirect
    │   ├── admin/          # AdminDashboard, UserManagementPage, CourseManagementPage,
    │   │                   # SecurityPage, DevToolsPage, WhiteLabelPage
    │   └── course/         # CourseViewerPage, ModuleAccordion
    ├── pages/
    │   ├── LoginPage.tsx
    │   ├── admin/          # AdminDashboard page wrappers
    │   ├── creator/        # CreatorDashboard, CreatorLearners
    │   └── learn/          # LearnerCatalogue, CourseDetail
    └── styles/
        └── globals.css     # CSS vars (:root) + utility classes from index.html <style> block
```

**Note:** `frontend/src/` subdirectory skeleton already exists with empty directories — populate rather than recreate.

### Pattern 1: Vite Base + React Router Basename

**What:** Two distinct config values that must point to the same path prefix with different trailing-slash conventions.
**When to use:** Any SPA served under a sub-path via Traefik/nginx.

```typescript
// vite.config.ts
// Source: https://vite.dev/config/shared-options#base
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tsconfigPaths from 'vite-tsconfig-paths'

export default defineConfig({
  base: '/lms/',          // trailing slash REQUIRED — controls built asset URLs
  plugins: [react(), tsconfigPaths()],
  build: {
    outDir: 'dist',       // explicit, matches gitignore entry frontend/dist/
  },
  server: {
    proxy: {
      '/api': 'http://localhost:8000',  // dev: forward API calls to FastAPI
    },
  },
})
```

```typescript
// src/main.tsx
import { BrowserRouter } from 'react-router-dom'

// basename: no trailing slash — React Router convention
// import.meta.env.BASE_URL resolves to '/lms/' from vite base
const basename = import.meta.env.BASE_URL.replace(/\/$/, '') // '/lms'

createRoot(document.getElementById('root')!).render(
  <BrowserRouter basename={basename}>
    <App />
  </BrowserRouter>
)
```

### Pattern 2: nginx.conf SPA Fallback

**What:** Committed nginx config with `try_files` fallback so hard refreshes on any route return `index.html`.
**When to use:** Always — the nixpacks Staticfile approach is fragile (opaque generated config, multiple prior failures).

```nginx
# frontend/nginx.conf
server {
    listen 80;
    root /app/dist;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    # Serve uploads from backend (if static file serving is needed)
    location /uploads/ {
        proxy_pass http://backend:8000;
    }
}
```

**Deployment note:** Coolify's nixpacks staticfile provider must be configured to use this file. If nixpacks cannot use a custom nginx.conf, the escape hatch is a `Dockerfile` in `frontend/` that copies `dist/` into an `nginx:alpine` image.

### Pattern 3: API_BASE Migration

**What:** The existing `API_BASE` constant uses `window.location.hostname` to detect production vs development. In the Vite build, this logic becomes an environment variable.

**Existing code (index.html line 187–194):**
```javascript
const API_BASE = (() => {
    const h = window.location.hostname;
    if (h === 'localhost' || h === '127.0.0.1') return '';
    return '/lms';
})();
```

**Vite replacement:**
```typescript
// src/services/api.ts
// In dev: Vite proxy forwards /api -> localhost:8000, so base is ''
// In prod: Traefik strips /lms before FastAPI, so API calls are /api/... (no /lms prefix)
// The existing API_BASE adds '/lms' in prod but Traefik strips it — this was correct.
// With Vite proxy in dev, no prefix needed. In prod, keep '/lms' for API calls OR set to ''.
// VERIFY: Does the existing /lms prefix survive Traefik stripping before reaching FastAPI?
// If Traefik strips /lms completely, then FastAPI sees /api/... and API_BASE should be ''.
// Current code sets API_BASE='/lms' in prod which means fetch('/lms/api/...') — Traefik
// strips /lms and FastAPI sees /api/... — this IS correct.
const API_BASE = import.meta.env.PROD ? '/lms' : ''
```

### Pattern 4: Auth Hydration (localStorage key preservation)

**What:** The Vite app must read the same `localStorage` key as the existing app to avoid logging users out on deploy.

```typescript
// src/context/AuthContext.tsx
// CRITICAL: key name must remain 'token' — matches existing app
const TOKEN_KEY = 'token'

const AuthProvider = ({ children }: { children: React.ReactNode }) => {
  const [auth, setAuth] = useState<string | null>(null)
  
  useEffect(() => {
    const token = localStorage.getItem(TOKEN_KEY)
    if (token) {
      setAuth(token)
      fetchUserProfile(token).finally(() => setLoading(false))
    } else {
      setLoading(false)
    }
  }, [])
  // ...
}
```

### Pattern 5: 401 Navigation via React Router

**What:** The existing API service uses `window.history.pushState` + `PopStateEvent` for 401 redirects. Vite build replaces this with React Router navigation.

**Existing code (index.html line 356–359):**
```javascript
localStorage.removeItem('token');
window.history.pushState(null, '', '/login');
window.dispatchEvent(new PopStateEvent('popstate'));
```

**Vite replacement — requires a navigation-capable API service:**
```typescript
// Option: store navigate ref in a module-level singleton, set it from within the router
// src/services/api.ts
let navigateFn: ((to: string) => void) | null = null
export const setNavigate = (fn: (to: string) => void) => { navigateFn = fn }

// In 401 handler:
localStorage.removeItem('token')
navigateFn?.('/login')
```

### Anti-Patterns to Avoid

- **Keeping both `frontend/index.html` and `frontend/dist/index.html`:** After Vite build, `frontend/index.html` is the Vite project entry shell (minimal `<div id="root">`). The old monolith must be renamed or removed — keeping it causes confusion about which file is served.
- **Setting `base: '/'` thinking Traefik handles it:** Traefik strips `/lms` at layer 7 before forwarding to nginx. But the browser initially requests `/lms/assets/main.js` — Traefik must pass that through to nginx. Vite `base: '/lms/'` ensures built HTML references those paths correctly. If `base` is `/`, assets in the built HTML will be at `/assets/main.js`, and the browser will request that — but Traefik won't route it correctly.
- **Using `window.location.href =` for navigation:** The existing code used `window.history.pushState` (correct) but had earlier `window.location.href` assignments patched out in a prior commit. Do not reintroduce them — use `useNavigate()` from react-router-dom throughout.
- **CDN Tailwind in the Vite build:** Remove `<script src="https://cdn.tailwindcss.com">` entirely — it conflicts with PostCSS/Tailwind pipeline and adds 300KB+ to page weight.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| SPA routing | Custom `RouterCtx` + `matchRoute` (currently in index.html) | react-router-dom v6 | The existing custom router lacks: nested routes, scroll restoration, loader pattern, proper history management |
| CSS class purging | None — CDN Tailwind loads all classes | PostCSS + Tailwind CLI via Vite | CDN loads all 3MB of Tailwind; build-time purging reduces to ~10-30KB |
| Path alias resolution | Relative import chains (`../../components/`) | vite-tsconfig-paths + `tsconfig.json` `paths` | Already in stack; single config change vs. updating every import |
| Dev API proxy | Manual CORS configuration or hardcoded localhost URLs | Vite `server.proxy` config | Built-in; avoids CORS errors during local dev without touching backend CORS settings |

**Key insight:** The existing hand-rolled router is the largest single refactor. Every `useNavigate()` call, every `useLocation()` call, and every `<Route>` definition maps 1:1 to react-router-dom equivalents — mechanical extraction, not redesign.

---

## Common Pitfalls

### Pitfall 1: Vite `base` Trailing Slash vs React Router `basename`

**What goes wrong:** App builds, assets 404, or deep links return blank page on hard refresh.
**Why it happens:** Vite wants trailing slash; React Router must NOT have trailing slash. Setting both to `/lms` or both to `/lms/` will break one or the other.
**How to avoid:**
- `vite.config.ts`: `base: '/lms/'` (trailing slash)
- `main.tsx`: `basename="/lms"` (no trailing slash), or `import.meta.env.BASE_URL.replace(/\/$/, '')`
**Warning signs:** JS chunks 404; hard refresh on `/lms/admin` shows blank page or nginx 404.

### Pitfall 2: Nixpacks Staticfile Auto-Generated nginx Config

**What goes wrong:** Deploy works locally but deep links 404 in Coolify staging.
**Why it happens:** This repo has 5 prior commits from this exact problem. The nixpacks-generated nginx config is opaque and may not include `try_files` fallback.
**How to avoid:** Commit `frontend/nginx.conf` with explicit `try_files $uri $uri/ /index.html`. Configure Coolify to use it OR use a minimal `Dockerfile` in `frontend/` that copies `dist/` into `nginx:alpine`.
**Warning signs:** `/lms/admin` works via link-click but 404s on browser refresh.

### Pitfall 3: Auth Regression — `localStorage` Key Name or Timing

**What goes wrong:** Users are logged out after deployment; login redirect loops.
**Why it happens:** If the Vite app reads a different localStorage key or initialises AuthContext before hydrating from storage, the app treats existing sessions as unauthenticated.
**How to avoid:** Keep `localStorage.getItem('token')` / `localStorage.setItem('token', ...)` / `localStorage.removeItem('token')` with key `'token'` exactly. Auth loading state must be `true` during hydration, blocking route rendering.
**Warning signs:** User reports being logged out after update; console shows "useAuth must be used within AuthProvider" (context not yet initialised).

### Pitfall 4: API_BASE Production vs Dev

**What goes wrong:** API calls work in dev (same-origin via Vite proxy) but fail in production with CORS errors or 404s.
**Why it happens:** In dev, Vite proxy handles `/api` -> `localhost:8000`. In prod, the frontend is served from nginx and makes calls to `https://buildbench.uk/lms/api/...` which Traefik routes to FastAPI after stripping `/lms`. The `API_BASE` must account for this.
**How to avoid:** Use `import.meta.env.PROD ? '/lms' : ''`. Verify the existing backend CORS list in `main.py` includes `https://buildbench.uk` (it does — line 135).
**Warning signs:** API calls 404 or CORS error in production; dev works fine.

### Pitfall 5: Old `frontend/index.html` Being Served Instead of Vite Output

**What goes wrong:** After Vite migration, the old 3420-line file is still being served because Coolify is pointed at the wrong file or the old file wasn't removed.
**Why it happens:** The old deployment served `frontend/index.html` directly. The Vite build creates `frontend/dist/index.html`. Without updating the Coolify config's publish directory, the old file still serves.
**How to avoid:** Coolify's static site build directory must be set to `frontend/dist`. The Vite entry point `frontend/index.html` (post-migration) is a minimal shell, not the app. Remove or archive the old monolith before the first deploy.
**Warning signs:** Production page shows `<script type="text/babel">` source tag; Babel standalone is still loading.

### Pitfall 6: 401 Handler Uses `window.history.pushState` Without Router Awareness

**What goes wrong:** After a token expiry, the app navigates to `/login` but React Router's `<BrowserRouter>` doesn't know about the navigation — the URL changes but React state doesn't update, leaving a stale component tree.
**Why it happens:** The existing custom router dispatches a `PopStateEvent` to simulate navigation. React Router's BrowserRouter already listens to `popstate`, so this pattern technically works. But in the Vite build, the navigate function should come from React Router.
**How to avoid:** Use a singleton navigate ref set during app initialisation (see Pattern 5 above), or restructure the API service as a hook that uses `useNavigate` directly.
**Warning signs:** After a 401 error, the URL shows `/login` but the old page content is still visible.

---

## Code Examples

### vite.config.ts (complete)
```typescript
// Source: https://vite.dev/config/shared-options#base
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tsconfigPaths from 'vite-tsconfig-paths'

export default defineConfig({
  base: '/lms/',
  plugins: [react(), tsconfigPaths()],
  build: {
    outDir: 'dist',
    sourcemap: false,
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
```

### tsconfig.json path alias
```json
{
  "compilerOptions": {
    "baseUrl": ".",
    "paths": {
      "@/*": ["src/*"]
    }
  }
}
```

### nginx.conf (committed to frontend/)
```nginx
server {
    listen 80;
    root /app/dist;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

### Complete route inventory (from index.html App component)

These routes must exist in `src/App.tsx`:

| Path | Component | Auth Guard |
|------|-----------|------------|
| `/login` | LoginPage | None |
| `/admin` | AdminDashboard in AdminLayout | adminOnly |
| `/admin/users` | UserManagementPage in AdminLayout | adminOnly |
| `/admin/courses` | CourseManagementPage in AdminLayout | adminOnly |
| `/admin/security` | SecurityPage in AdminLayout | adminOnly |
| `/admin/dev-tools` | DevToolsPage in AdminLayout | adminOnly |
| `/admin/whitelabel` | WhiteLabelPage in AdminLayout | adminOnly |
| `/creator` | CreatorDashboard in CreatorLayout | creatorRoute |
| `/creator/courses` | CourseManagementPage in CreatorLayout | creatorRoute |
| `/creator/learners` | CreatorLearners in CreatorLayout | creatorRoute |
| `/courses/:id` | CourseViewerPage | authenticated |
| `/learn` | LearnerCatalogue in LearnerLayout | authenticated |
| `/learn/:id` | CourseDetail in LearnerLayout | authenticated |
| `/` | SmartRedirect | None |
| `*` | SmartRedirect | None |

### SmartRedirect logic (from index.html)

```typescript
// src/components/auth/SmartRedirect.tsx
// Existing logic: redirect based on user role
const SmartRedirect = () => {
  const { user, loading } = useAuth()
  const navigate = useNavigate()
  
  useEffect(() => {
    if (loading) return
    if (!user) { navigate('/login'); return }
    if (user.role === 'admin') navigate('/admin')
    else if (user.role === 'creator') navigate('/creator')
    else navigate('/learn')
  }, [user, loading, navigate])
  
  return null
}
```

### CSS variables migration

The `<style>` block in `index.html` (lines 13–164) defines CSS custom properties and utility classes. These move to `src/styles/globals.css`:

```css
/* src/styles/globals.css */
:root {
  --primary: #2563eb;
  --secondary: #7c3aed;
  --accent: #f59e0b;
  --bg: #f8fafc;
  --text: #1e293b;
  --font-family: 'Inter', sans-serif;
  --heading-font: 'Inter', sans-serif;
  --border-radius: 8px;
}
/* ... spin, fadeIn, toast, skeleton, modal-overlay, badge, chart-bar keyframes */
```

---

## Component Inventory (Full Extraction Map)

All components currently in `index.html` must be migrated to TypeScript files in `frontend/src/`:

### Contexts (extract verbatim, add TypeScript types)
- `AuthContext` → `src/context/AuthContext.tsx` (lines 262–341)
- `ToastContext` → `src/context/ToastContext.tsx` (lines 422–453)

### Services
- `api` object → `src/services/api.ts` (lines 344–418)
  - Replace 401 handler `window.history.pushState` with singleton `navigateFn`
  - Replace hostname-based `API_BASE` with `import.meta.env.PROD ? '/lms' : ''`

### Common Components (no dependencies)
- `Modal` → `src/components/common/Modal.tsx`
- `Button` → `src/components/common/Button.tsx`
- `Card` → `src/components/common/Card.tsx`
- `Badge` → `src/components/common/Badge.tsx`
- `Input` → `src/components/common/Input.tsx`
- `Select` → `src/components/common/Select.tsx`
- `Textarea` → `src/components/common/Textarea.tsx`

### Auth Components
- `ProtectedRoute` → `src/components/auth/ProtectedRoute.tsx`
- `SmartRedirect` → `src/components/auth/SmartRedirect.tsx`
- `LoginPage` → `src/pages/LoginPage.tsx`

### Layout Components
- `AdminLayout` → `src/components/layout/AdminLayout.tsx`
- `LearnerLayout` → `src/components/layout/LearnerLayout.tsx`
- `CreatorLayout` → `src/components/layout/CreatorLayout.tsx`

### Admin Pages
- `AdminDashboard` → `src/pages/admin/AdminDashboard.tsx`
- `UserManagementPage` → `src/pages/admin/UserManagementPage.tsx`
- `CourseManagementPage` → `src/pages/admin/CourseManagementPage.tsx` (also used in creator)
- `SecurityPage` → `src/pages/admin/SecurityPage.tsx`
- `DevToolsPage` → `src/pages/admin/DevToolsPage.tsx`
- `WhiteLabelPage` → `src/pages/admin/WhiteLabelPage.tsx`

### Creator Pages
- `CreatorDashboard` → `src/pages/creator/CreatorDashboard.tsx`
- `CreatorLearners` → `src/pages/creator/CreatorLearners.tsx`

### Learner Pages
- `LearnerCatalogue` → `src/pages/learn/LearnerCatalogue.tsx`
- `CourseDetail` → `src/pages/learn/CourseDetail.tsx`
- `ModuleAccordion` → `src/pages/learn/ModuleAccordion.tsx` (sub-component)

### Course Components
- `CourseViewerPage` → `src/pages/CourseViewerPage.tsx`

---

## Deployment Strategy

### Current State
- `frontend/Staticfile` exists with `status_codes: 404: /index.html`
- No `package.json`, no `vite.config.ts`, no `tsconfig.json` in `frontend/`
- CI `frontend-build` job expects `npm ci && npm run build` in `frontend/`

### Target State
```
frontend/
├── package.json         # NEW: scripts.build = "vite build"
├── vite.config.ts       # NEW
├── tsconfig.json        # NEW (generated by vite create)
├── nginx.conf           # NEW: replaces Staticfile
├── index.html           # REPLACED: was 3420-line monolith, now Vite entry shell
├── Staticfile           # DELETE (or leave; nginx.conf takes precedence)
└── dist/                # GITIGNORED: build output served by nginx
```

### Coolify Configuration
- Build command: `npm ci && npm run build` (in `frontend/` directory)
- Publish directory: `frontend/dist`
- The committed `nginx.conf` must be in scope for nixpacks staticfile — confirm in Coolify UI

### Traefik/nginx Path Flow (verified from prior commits)
```
Browser: GET https://buildbench.uk/lms/admin
Traefik: stripprefix /lms → GET /admin forwarded to nginx container
nginx: try_files /admin → /admin/ → /index.html (SPA fallback)
React Router: basename="/lms", URL is /lms/admin, renders AdminDashboard
```

**CRITICAL VERIFY:** The asset URLs in the built `dist/index.html` will be `/lms/assets/main.js`. Browser requests `GET https://buildbench.uk/lms/assets/main.js`. Traefik strips `/lms` → nginx receives `GET /assets/main.js`. nginx root is `dist/`, so this resolves to `dist/assets/main.js`. This is correct.

---

## State of the Art

| Old Approach | Current Approach | Impact for This Phase |
|--------------|------------------|-----------------------|
| CDN React + Babel standalone | Vite + React + TypeScript build | No runtime compilation; ~10x faster page load; tree-shaking |
| CDN Tailwind (3MB) | PostCSS Tailwind pipeline | CSS bundle ~10-30KB vs 3MB+ |
| Hand-rolled router with `RouterCtx` | react-router-dom v6 | Standard API; nested routes possible for Phase 12+ |
| `type="text/babel"` script tag | TypeScript source files with JSX | Type checking; IDE support; enables dnd-kit, TipTap, etc. |
| Single 3420-line file | Component files in `src/` | Maintainable; required for Phase 12+ feature additions |

---

## Open Questions

1. **Traefik stripprefix exact behaviour for static assets**
   - What we know: Prior commits show Traefik strips `/lms` before nginx. This works for HTML navigation. Static assets at `/lms/assets/main.js` should also be stripped.
   - What's unclear: Exact Traefik middleware config (not visible in this repo). If Traefik only strips on HTML requests or has path exceptions, asset 404s would occur.
   - Recommendation: After first Vite deploy, check browser network tab — asset requests should return 200. If not, inspect Traefik `stripPrefix` rule scope in Coolify dashboard.

2. **Coolify nginx.conf injection mechanism**
   - What we know: The prior commits experimented with nixpacks.toml, Caddyfile, Staticfile — eventually settling on nginx.conf committed to the repo. The current `Staticfile` handles SPA fallback via `status_codes`.
   - What's unclear: Whether Coolify's nixpacks staticfile provider automatically picks up a committed `nginx.conf`, or whether a `Dockerfile` is required for full control.
   - Recommendation: Test in Coolify staging. If nixpacks ignores `nginx.conf`, create a minimal `frontend/Dockerfile`: `FROM nginx:alpine; COPY dist/ /usr/share/nginx/html; COPY nginx.conf /etc/nginx/conf.d/default.conf`.

3. **`CourseManagementPage` shared between admin and creator routes**
   - What we know: In index.html, the same `CourseManagementPage` component is used for both `/admin/courses` and `/creator/courses` routes with different parent layouts.
   - What's unclear: Whether it uses role-conditional logic internally.
   - Recommendation: Extract as a shared component in `src/pages/shared/CourseManagementPage.tsx` and import from both admin and creator route definitions.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (backend, existing) + none established for frontend |
| Config file | `backend/pytest.ini` (implied from CI) |
| Quick run command | `cd backend && pytest -x -q` |
| Full suite command | `cd backend && pytest -v` |
| Frontend build check | `cd frontend && npm run build` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| INFRA-01 | Vite build succeeds with no errors | build smoke | `cd frontend && npm run build` | Wave 0 (package.json doesn't exist yet) |
| INFRA-02 | Built `dist/index.html` references `/lms/assets/` paths | build artifact check | `grep '/lms/assets' frontend/dist/index.html` | Wave 0 |
| INFRA-03 | nginx.conf exists and contains try_files fallback | file check | `grep 'try_files' frontend/nginx.conf` | Wave 0 |
| INFRA-04 | All existing features work (auth cycle, admin, learner, creator) | manual smoke | Manual browser test on Coolify staging | Manual only — no automated e2e |
| INFRA-05 | Hard refresh on each route returns 200 with correct page | manual + curl | `curl -s -o /dev/null -w "%{http_code}" https://buildbench.uk/lms/admin` | Manual (requires deploy) |

### Sampling Rate
- **Per task commit:** `cd frontend && npm run build` (confirms TypeScript compilation clean)
- **Per wave merge:** Backend test suite + frontend build
- **Phase gate:** Manual smoke test on Coolify staging — login, navigate all main routes, hard refresh on each

### Wave 0 Gaps
- [ ] `frontend/package.json` — must exist before `npm ci` works in CI
- [ ] `frontend/vite.config.ts` — required for build
- [ ] `frontend/tsconfig.json` — required for TypeScript compilation
- [ ] `frontend/nginx.conf` — required for SPA routing in Coolify
- [ ] `frontend/src/main.tsx` — Vite entry point
- [ ] `frontend/src/App.tsx` — route tree
- Framework install: `cd frontend && npm create vite@latest . -- --template react-ts`

---

## Sources

### Primary (HIGH confidence)
- Vite official docs — `base` option: https://vite.dev/config/shared-options#base
- react-router-dom v6 `basename`: https://reactrouter.com/en/main/router-components/browser-router#basename
- Existing codebase — `frontend/index.html` (3420 lines, inspected directly)
- Existing codebase — `backend/main.py` (CORS origins, catch-all route)
- Existing codebase — `.github/workflows/ci.yml` (CI expects `npm ci && npm run build` in `frontend/`)
- Existing git history — 5 nginx/Staticfile/Caddyfile commits confirm path-prefix complexity

### Secondary (MEDIUM confidence)
- STACK.md (project research, 2026-05-08) — Vite config details, plugin choices
- PITFALLS.md (project research, 2026-05-08) — nginx SPA fallback, auth regression patterns
- STATE.md — Architecture decisions, `base: '/lms/'` trailing slash decision documented

### Tertiary (LOW confidence)
- Coolify nixpacks staticfile nginx.conf pickup behaviour — not directly verified; requires deploy test

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — versions verified via existing CI config and project STACK.md
- Architecture: HIGH — component inventory extracted directly from index.html source
- Deployment path: MEDIUM — Traefik/nginx flow inferred from git history and PITFALLS.md; needs staging verification
- Pitfalls: HIGH — drawn from direct codebase inspection + documented git history

**Research date:** 2026-05-08
**Valid until:** 2026-06-08 (Vite 6.x stable; no breaking changes expected on this timeline)
