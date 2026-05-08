---
phase: 9
slug: vite-migration
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-08
---

# Phase 9 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Vitest (frontend unit) + Playwright (E2E smoke) |
| **Config file** | `frontend/vitest.config.ts` — Wave 0 installs |
| **Quick run command** | `cd frontend && npm run test:unit` |
| **Full suite command** | `cd frontend && npm run test:unit && npm run build` |
| **Estimated runtime** | ~15 seconds (unit); ~60 seconds (unit + build) |

---

## Sampling Rate

- **After every task commit:** Run `cd frontend && npm run test:unit`
- **After every plan wave:** Run `cd frontend && npm run test:unit && npm run build`
- **Before `/gsd:verify-work`:** Full suite must be green + manual smoke test in browser
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 9-01-01 | 01 | 0 | INFRA-01 | build | `cd frontend && npm run build` | ❌ W0 | ⬜ pending |
| 9-01-02 | 01 | 0 | INFRA-02 | build | `cd frontend && npm run build && grep 'base.*lms' frontend/vite.config.ts` | ❌ W0 | ⬜ pending |
| 9-01-03 | 01 | 1 | INFRA-03 | manual | Verify `nginx.conf` has `try_files $uri $uri/ /index.html` | ✅ | ⬜ pending |
| 9-01-04 | 01 | 1 | INFRA-04 | unit | `cd frontend && npm run test:unit -- --run` | ❌ W0 | ⬜ pending |
| 9-01-05 | 01 | 1 | INFRA-05 | unit | `cd frontend && npm run test:unit -- --run src/router.test.tsx` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `frontend/package.json` — Vite + React + TypeScript project scaffold
- [ ] `frontend/vite.config.ts` — with `base: '/lms/'` and Vite dev proxy
- [ ] `frontend/tsconfig.json` — TypeScript config with path aliases
- [ ] `frontend/src/main.tsx` — app entry with `<BrowserRouter basename="/lms">`
- [ ] `frontend/src/App.tsx` — route definitions (empty route stubs)
- [ ] `frontend/vitest.config.ts` — unit test config
- [ ] `frontend/src/__tests__/router.test.tsx` — route smoke tests (stubs that fail)
- [ ] `frontend/src/__tests__/auth.test.tsx` — AuthContext token key preservation test (stubs that fail)

*These must exist and fail before implementation begins.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Hard-refresh deep link works | INFRA-03, INFRA-05 | Requires live Coolify deploy + nginx serving built output | Deploy to Coolify staging, navigate to `/lms/admin`, hard-refresh (Cmd+Shift+R), verify page loads (not 404) |
| Existing user session preserved after deploy | INFRA-04 | Requires a real browser with a valid token in localStorage | Log in as admin in current prod, deploy new build, reload — user should still be logged in |
| Asset paths use `/lms/` prefix | INFRA-02 | Requires inspecting built HTML in browser | View page source of deployed app, verify `<script src="/lms/assets/...">` not `/assets/...` |
| No Babel CDN script in HTML | INFRA-01 | Inspect deployed HTML | View source of `buildbench.uk/lms`, confirm no `babel.min.js` or `cdn.tailwindcss.com` script tags |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
