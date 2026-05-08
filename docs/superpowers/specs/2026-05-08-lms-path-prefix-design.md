# LMS Path-Prefix Migration Design Spec
**Date:** 2026-05-08  
**Status:** Approved

---

## Goal

Move the entire LMS stack under the `buildbench.uk/lms` path prefix so tenant company subdomains (`{company}.buildbench.uk`) never collide with platform infrastructure.

---

## Current State

| Service | URL |
|---|---|
| LMS frontend | `http://dta9d9jm5k5tb94wnomxfxps.188.245.67.238.sslip.io` |
| LMS backend API | `https://api.buildbench.uk` |
| Other app (Laravel) | `https://buildbench.uk` |

---

## Target State

| Path | Routes to | Notes |
|---|---|---|
| `buildbench.uk/lms/api/*` | FastAPI backend | Traefik strips `/lms`, FastAPI sees `/api/...` unchanged |
| `buildbench.uk/lms/*` | LMS nginx frontend | Traefik strips `/lms`, nginx serves `index.html` |
| `buildbench.uk/*` | Laravel app | Unchanged — lower Traefik priority |
| `{company}.buildbench.uk` | Tenant subdomains | Free, no collision risk |

Traefik resolves priority by rule length: `/lms/api` (longer) beats `/lms` automatically.

---

## Architecture

```
Browser
  │
  ├─ buildbench.uk/lms/api/auth/login
  │     → Traefik strips /lms
  │     → FastAPI container :8000 sees /api/auth/login  ✓
  │
  ├─ buildbench.uk/lms/learn
  │     → Traefik strips /lms
  │     → nginx container :80 sees /learn
  │     → try_files serves /app/index.html
  │     → React mounts, BrowserRouter strips /lms from window.location.pathname
  │     → Internal path /learn matches <Route path="/learn">  ✓
  │
  └─ buildbench.uk/ (non-lms)
        → Laravel app (unchanged)  ✓
```

---

## Code Changes

### 1. `frontend/index.html`

**`API_BASE` constant** — return `/lms` for production (Traefik strips `/lms`, leaving `/api/...` for FastAPI):

```javascript
const API_BASE = (() => {
    const h = window.location.hostname;
    if (h === 'localhost' || h === '127.0.0.1') return '';
    return '/lms';
})();
```

All existing `fetch(API_BASE + '/api/...')` calls become `fetch('/lms/api/...')` in production, which Traefik rewrites to `/api/...` before hitting FastAPI. No other API call changes needed.

**`BrowserRouter` base path** — strip `/lms` from `window.location.pathname` so internal route matching is unchanged:

```javascript
const BASE = '/lms';

const BrowserRouter = ({ children }) => {
    const getInternalPath = () => {
        const p = window.location.pathname;
        return p.startsWith(BASE) ? p.slice(BASE.length) || '/' : p;
    };
    const [path, setPath] = useState(getInternalPath);
    useEffect(() => {
        const handler = () => setPath(getInternalPath());
        window.addEventListener('popstate', handler);
        return () => window.removeEventListener('popstate', handler);
    }, []);
    const navigate = useCallback((to) => {
        window.history.pushState(null, '', BASE + to);
        setPath(to);
    }, []);
    return React.createElement(RouterCtx.Provider, { value: { path, navigate } }, children);
};
```

All existing `<Route path="/learn">`, `navigate('/learn')`, `<Navigate to="/login">` etc. stay **unchanged** — the base path is handled entirely in the router.

### 2. `backend/main.py`

Add `https://buildbench.uk` to the CORS allowed origins list:

```python
_cors_origins = (
    settings.CORS_ORIGINS
    if settings.CORS_ORIGINS != ["*"]
    else [
        "http://localhost:8000",
        "http://localhost:3000",
        "http://127.0.0.1:8000",
        "https://buildbench.uk",
        "http://buildbench.uk",
        # Legacy sslip.io dev frontend (can be removed later)
        "http://dta9d9jm5k5tb94wnomxfxps.188.245.67.238.sslip.io",
    ]
)
```

---

## Infrastructure Changes (Coolify Custom Labels)

Coolify v4 allows custom Docker labels per service to override Traefik routing. The generated labels are merged with custom labels; custom labels win on conflict.

### LMS Frontend service — custom labels to add in Coolify

```
traefik.http.routers.http-0-dta9d9jm5k5tb94wnomxfxps.rule=Host(`buildbench.uk`) && PathPrefix(`/lms`)
traefik.http.routers.http-0-dta9d9jm5k5tb94wnomxfxps.middlewares=strip-lms,gzip
traefik.http.middlewares.strip-lms.stripprefix.prefixes=/lms
```

### LMS Backend service — custom labels to add in Coolify

```
traefik.http.routers.https-0-grezgrjpzsiy1x1aqlqu4yml.rule=Host(`buildbench.uk`) && PathPrefix(`/lms/api`)
traefik.http.routers.https-0-grezgrjpzsiy1x1aqlqu4yml.middlewares=strip-lms,gzip
traefik.http.routers.http-0-grezgrjpzsiy1x1aqlqu4yml.rule=Host(`buildbench.uk`) && PathPrefix(`/lms/api`)
traefik.http.routers.http-0-grezgrjpzsiy1x1aqlqu4yml.middlewares=strip-lms,redirect-to-https
traefik.http.middlewares.strip-lms.stripprefix.prefixes=/lms
```

The `strip-lms` middleware is defined once and referenced by both services. Traefik deduplicates middleware definitions by name.

---

## nginx / nixpacks.toml

No changes needed. The `nixpacks.toml` sed patch inserts `try_files $uri $uri/ /index.html;` in the `location /` block. Since Traefik strips `/lms` before the request reaches nginx, nginx always sees paths without the prefix (`/learn`, `/admin`, `/learn/1`, etc.) — exactly what the current config handles.

---

## Files Changed

| File | Change |
|---|---|
| `frontend/index.html` | Update `API_BASE` and `BrowserRouter` base path |
| `backend/main.py` | Add `https://buildbench.uk` to CORS origins |
| Coolify dashboard | Add custom Traefik labels to frontend and backend services |

---

## What Is Not In Scope

- Moving the Laravel app — it continues to own `buildbench.uk/` unchanged
- HTTPS cert for the LMS frontend — the existing Laravel app's cert covers `buildbench.uk`; Traefik will serve the frontend over the same TLS connection
- Removing the sslip.io frontend URL — it can stay alive during transition and be removed later

---

## Rollback

Removing the custom Traefik labels in Coolify and redeploying restores the previous routing instantly. The sslip.io URL continues to work throughout.
