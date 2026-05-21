# Stadler Corporate Rebrand — LMS Frontend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restyle the LMS web frontend to the Stadler corporate design system (palette, Arial typography, gradient + yellow accents, logo) with minimal per-component churn.

**Architecture:** Remap Tailwind's `blue` colour scale to the Stadler palette so all existing hardcoded `blue-*` usages rebrand automatically; add semantic `brand`/`accent` tokens, an Arial font stack, and a gradient utility; align the CSS-variable defaults and white-label `DEFAULT_CONFIG` to Stadler; then hand-upgrade the high-visibility chrome (login, sidebars, headers, learner nav, Button) and bundle the Stadler logo.

**Tech Stack:** Vite 6, React 18, TypeScript (strict), Tailwind 3, react-router 6, Vitest + Testing Library.

**Brand palette:** Stadler Blue `#1E5A9A` · Light Blue `#007BC0` · Dark Blue `#0B3F75` · Warm Yellow `#FFBD00` · Off-white `#F0F7FE`. Gradient: `linear-gradient(-45deg, #007BC0, #0B3F75)`.

**Conventions confirmed in this repo:**
- `@/*` resolves to `frontend/src/*` (tsconfig paths + `vite-tsconfig-paths`).
- PNG imports are typed via `vite/client` (`src/vite-env.d.ts`) — no extra declaration needed.
- Vite `base` is `/lms/`; `public/` assets are served at `/lms/<file>`.
- Build: `npm run build` = `tsc -b && vite build`. Strict TS with `noUnusedLocals`/`noUnusedParameters` — do not leave unused imports.
- Tests: Vitest, jsdom, `css: false`, files matched by `src/**/*.test.{ts,tsx}`, setup at `src/__tests__/setup.ts`.
- All commands below run from `frontend/`.

---

### Task 1: Stadler design tokens in Tailwind config

**Files:**
- Modify: `frontend/tailwind.config.js`

- [ ] **Step 1: Replace the config with the Stadler token set**

Overwrite `frontend/tailwind.config.js` with:

```js
/** @type {import('tailwindcss').Config} */
export default {
  content: [
    './index.html',
    './src/**/*.{ts,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        // Remap Tailwind's blue scale to the Stadler palette so existing
        // hardcoded blue-* usages rebrand automatically.
        blue: {
          50: '#F0F7FE',
          100: '#D6E6F5',
          200: '#AECCEB',
          300: '#7FAEDC',
          400: '#4B8BCB',
          500: '#007BC0', // Stadler Light Blue — focus rings
          600: '#1E5A9A', // Stadler Blue — primary
          700: '#0B3F75', // Stadler Dark Blue — hover / dark
          800: '#093059',
          900: '#07223F',
        },
        // Semantic aliases for new on-brand styling.
        brand: {
          DEFAULT: '#1E5A9A',
          dark: '#0B3F75',
          light: '#007BC0',
          accent: '#FFBD00',
          surface: '#F0F7FE',
        },
      },
      fontFamily: {
        sans: ['Arial', 'Helvetica', 'sans-serif'],
      },
      backgroundImage: {
        'brand-gradient': 'linear-gradient(-45deg, #007BC0, #0B3F75)',
      },
    },
  },
  plugins: [],
}
```

- [ ] **Step 2: Verify the build still compiles**

Run: `npm run build`
Expected: completes with no TypeScript or Vite errors, writes `dist/`.

- [ ] **Step 3: Commit**

```bash
git add tailwind.config.js
git commit -m "feat(frontend): add Stadler brand tokens to Tailwind config"
```

---

### Task 2: Align CSS-variable defaults to Stadler

**Files:**
- Modify: `frontend/src/styles/globals.css:5-14` (the `:root` block)

- [ ] **Step 1: Update the `:root` defaults**

Replace the `:root { ... }` block (lines 5-14) with:

```css
:root {
  --primary: #1E5A9A;
  --secondary: #0B3F75;
  --accent: #FFBD00;
  --bg: #F0F7FE;
  --text: #0B3F75;
  --font-family: 'Arial', 'Helvetica', sans-serif;
  --heading-font: 'Arial', 'Helvetica', sans-serif;
  --border-radius: 8px;
}
```

Leave the rest of the file unchanged (utility classes, animations, toast/badge/skeleton styles already reference these variables where relevant).

- [ ] **Step 2: Verify the build**

Run: `npm run build`
Expected: completes with no errors.

- [ ] **Step 3: Commit**

```bash
git add src/styles/globals.css
git commit -m "feat(frontend): default CSS theme variables to Stadler palette + Arial"
```

---

### Task 3: Bundle the Stadler logo and update the page title/favicon

**Files:**
- Create: `frontend/src/assets/stadler-logo.png` (copied from `~/Downloads/stalder logo.png`)
- Create: `frontend/public/stadler-logo.png` (favicon source, served at `/lms/stadler-logo.png`)
- Modify: `frontend/index.html`

- [ ] **Step 1: Copy the logo into the project**

Run (from `frontend/`):

```bash
mkdir -p src/assets
cp "$HOME/Downloads/stalder logo.png" src/assets/stadler-logo.png
cp "$HOME/Downloads/stalder logo.png" public/stadler-logo.png
ls -l src/assets/stadler-logo.png public/stadler-logo.png
```

Expected: both files exist (~2.5 KB each).

- [ ] **Step 2: Update `index.html` title and favicon**

In `frontend/index.html`, replace the favicon `<link>` and `<title>` lines:

```html
    <link rel="icon" type="image/png" href="/lms/stadler-logo.png" />
```
```html
    <title>SRSUK Learning Portal</title>
```

- [ ] **Step 3: Verify the build copies the public asset**

Run: `npm run build && ls dist/stadler-logo.png`
Expected: build succeeds and `dist/stadler-logo.png` exists.

- [ ] **Step 4: Commit**

```bash
git add src/assets/stadler-logo.png public/stadler-logo.png index.html
git commit -m "feat(frontend): bundle Stadler logo and set portal title/favicon"
```

---

### Task 4: Add a yellow `accent` variant to the Button component (TDD)

**Files:**
- Create: `frontend/src/components/common/__tests__/Button.test.tsx`
- Modify: `frontend/src/components/common/Button.tsx`

- [ ] **Step 1: Write the failing test**

Create `frontend/src/components/common/__tests__/Button.test.tsx`:

```tsx
import { render, screen } from '@testing-library/react'
import { Button } from '../Button'

describe('Button', () => {
  it('applies Stadler yellow classes for the accent variant', () => {
    render(<Button variant="accent">Save</Button>)
    const btn = screen.getByRole('button', { name: 'Save' })
    expect(btn.className).toContain('bg-brand-accent')
    expect(btn.className).toContain('text-brand-dark')
  })

  it('still defaults to the primary (Stadler blue) variant', () => {
    render(<Button>Go</Button>)
    const btn = screen.getByRole('button', { name: 'Go' })
    expect(btn.className).toContain('bg-blue-600')
  })
})
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `npx vitest run src/components/common/__tests__/Button.test.tsx`
Expected: FAIL — the accent variant is not yet in `variantClasses`, so TypeScript/`variant="accent"` is invalid and the className lacks `bg-brand-accent`.

- [ ] **Step 3: Add the accent variant**

In `frontend/src/components/common/Button.tsx`, update the variant type and the `variantClasses` map:

```tsx
type ButtonVariant = 'primary' | 'secondary' | 'danger' | 'ghost' | 'accent'
```

```tsx
const variantClasses: Record<ButtonVariant, string> = {
  primary: 'bg-blue-600 text-white hover:bg-blue-700 focus:ring-blue-500',
  secondary: 'bg-gray-200 text-gray-900 hover:bg-gray-300 focus:ring-gray-400',
  danger: 'bg-red-600 text-white hover:bg-red-700 focus:ring-red-500',
  ghost: 'text-blue-600 hover:bg-blue-50 focus:ring-blue-500',
  accent: 'bg-brand-accent text-brand-dark hover:bg-[#E6AA00] focus:ring-brand-accent',
}
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `npx vitest run src/components/common/__tests__/Button.test.tsx`
Expected: PASS (both tests).

- [ ] **Step 5: Commit**

```bash
git add src/components/common/Button.tsx src/components/common/__tests__/Button.test.tsx
git commit -m "feat(frontend): add Stadler yellow accent Button variant"
```

---

### Task 5: Admin sidebar + header chrome

**Files:**
- Modify: `frontend/src/components/layout/AdminLayout.tsx`

- [ ] **Step 1: Import the logo and capture the white-label logo URL**

At the top of `AdminLayout.tsx`, add the logo import after the existing imports:

```tsx
import stadlerLogo from '@/assets/stadler-logo.png'
```

Add a `logoUrl` state next to `brandName`:

```tsx
  const [brandName, setBrandName] = useState('Stadler')
  const [logoUrl, setLogoUrl] = useState('')
```

In the `fetchBrandConfig` effect, also capture the logo URL — update the success branch:

```tsx
        if (res.ok) {
          const data = await res.json()
          setBrandName(data.brand_name || 'Stadler')
          setLogoUrl(data.logo_url || '')
        }
```

- [ ] **Step 2: Replace the sidebar container + logo header**

Change the sidebar wrapper background from `bg-gray-900` to the Stadler dark blue, and replace the logo header block. Replace:

```tsx
      <div className={`${sidebarOpen ? 'w-64' : 'w-20'} bg-gray-900 text-white transition-all duration-200 flex flex-col`}>
        <div className="p-4 border-b border-gray-700">
          <h1 className={`font-bold ${sidebarOpen ? 'text-lg' : 'text-xs text-center'}`}>
            {sidebarOpen ? brandName : '◉'}
          </h1>
        </div>
```

with:

```tsx
      <div className={`${sidebarOpen ? 'w-64' : 'w-20'} bg-brand-dark text-white transition-all duration-200 flex flex-col`}>
        <div className="p-4 border-b border-white/15 flex items-center justify-center h-16">
          {sidebarOpen ? (
            <img
              src={logoUrl || stadlerLogo}
              alt={brandName}
              className="h-7 w-auto max-w-full object-contain"
              style={logoUrl ? undefined : { filter: 'brightness(0) invert(1)' }}
            />
          ) : (
            <img
              src={logoUrl || stadlerLogo}
              alt={brandName}
              className="h-6 w-6 object-contain object-left"
              style={logoUrl ? undefined : { filter: 'brightness(0) invert(1)' }}
            />
          )}
        </div>
```

- [ ] **Step 3: Restyle the nav items (active = Stadler blue + yellow accent bar)**

Replace the nav `<button>` className expression:

```tsx
              className={`w-full flex items-center space-x-3 px-3 py-2 rounded-lg transition ${location.pathname === item.path ? 'bg-blue-600' : 'hover:bg-gray-800'}`}
```

with:

```tsx
              className={`w-full flex items-center space-x-3 px-3 py-2 rounded-lg border-l-4 transition ${location.pathname === item.path ? 'bg-blue-600 border-brand-accent' : 'border-transparent hover:bg-white/10'}`}
```

- [ ] **Step 4: Fix the bottom control hover states (gray → translucent white)**

Replace the two occurrences of `hover:bg-gray-800` in the bottom control buttons (collapse toggle and logout) with `hover:bg-white/10`. Leave the logout's `text-red-400` as-is.

- [ ] **Step 5: Add a yellow underline rule to the page title**

In the top bar, replace:

```tsx
          <h2 className="text-2xl font-bold">{getPageTitle()}</h2>
```

with:

```tsx
          <h2 className="text-2xl font-bold text-brand-dark border-b-2 border-brand-accent pb-1">{getPageTitle()}</h2>
```

- [ ] **Step 6: Verify the build**

Run: `npm run build`
Expected: completes with no errors (watch for unused-import errors — `stadlerLogo` and `logoUrl` are both used).

- [ ] **Step 7: Commit**

```bash
git add src/components/layout/AdminLayout.tsx
git commit -m "feat(frontend): Stadler chrome for admin sidebar and header"
```

---

### Task 6: Creator sidebar + header chrome

**Files:**
- Modify: `frontend/src/components/layout/CreatorLayout.tsx`

- [ ] **Step 1: Import the logo and capture the white-label logo URL**

Add after the existing imports:

```tsx
import stadlerLogo from '@/assets/stadler-logo.png'
```

Update state:

```tsx
  const [brandName, setBrandName] = useState('Stadler')
  const [logoUrl, setLogoUrl] = useState('')
```

Update the fetch chain to capture the logo:

```tsx
    fetch(API_BASE + '/api/whitelabel/preview')
      .then(r => r.ok ? r.json() : null)
      .then(d => {
        if (d) {
          setBrandName(d.brand_name || 'Stadler')
          setLogoUrl(d.logo_url || '')
        }
      })
      .catch(() => {})
```

- [ ] **Step 2: Replace the sidebar container + logo header**

Replace:

```tsx
      <div className={`${sidebarOpen ? 'w-64' : 'w-20'} bg-gray-900 text-white transition-all duration-200 flex flex-col`}>
        <div className="p-4 border-b border-gray-700">
          <h1 className={`font-bold ${sidebarOpen ? 'text-lg' : 'text-xs text-center'}`}>
            {sidebarOpen ? brandName : '◉'}
          </h1>
        </div>
```

with:

```tsx
      <div className={`${sidebarOpen ? 'w-64' : 'w-20'} bg-brand-dark text-white transition-all duration-200 flex flex-col`}>
        <div className="p-4 border-b border-white/15 flex items-center justify-center h-16">
          <img
            src={logoUrl || stadlerLogo}
            alt={brandName}
            className={`${sidebarOpen ? 'h-7' : 'h-6 w-6 object-left'} w-auto max-w-full object-contain`}
            style={logoUrl ? undefined : { filter: 'brightness(0) invert(1)' }}
          />
        </div>
```

- [ ] **Step 3: Restyle the nav items**

Replace:

```tsx
              className={`w-full flex items-center space-x-3 px-3 py-2 rounded-lg transition ${location.pathname === item.path ? 'bg-blue-600' : 'hover:bg-gray-800'}`}
```

with:

```tsx
              className={`w-full flex items-center space-x-3 px-3 py-2 rounded-lg border-l-4 transition ${location.pathname === item.path ? 'bg-blue-600 border-brand-accent' : 'border-transparent hover:bg-white/10'}`}
```

- [ ] **Step 4: Fix bottom control hover states**

Replace both `hover:bg-gray-800` occurrences (collapse toggle and logout) with `hover:bg-white/10`.

- [ ] **Step 5: Fix the avatar colour and add the title underline**

Replace the avatar `bg-indigo-600`:

```tsx
                <div className="w-10 h-10 rounded-full bg-indigo-600 text-white flex items-center justify-center font-bold">
```

with:

```tsx
                <div className="w-10 h-10 rounded-full bg-blue-600 text-white flex items-center justify-center font-bold">
```

Replace the page title:

```tsx
          <h2 className="text-2xl font-bold">{getPageTitle()}</h2>
```

with:

```tsx
          <h2 className="text-2xl font-bold text-brand-dark border-b-2 border-brand-accent pb-1">{getPageTitle()}</h2>
```

- [ ] **Step 6: Verify the build**

Run: `npm run build`
Expected: completes with no errors.

- [ ] **Step 7: Commit**

```bash
git add src/components/layout/CreatorLayout.tsx
git commit -m "feat(frontend): Stadler chrome for creator sidebar and header"
```

---

### Task 7: Login screen — Stadler gradient panel + logo

**Files:**
- Modify: `frontend/src/pages/LoginPage.tsx`

- [ ] **Step 1: Import the logo and extend the brand config type**

Add after the existing imports:

```tsx
import stadlerLogo from '@/assets/stadler-logo.png'
```

Add `logo_url` to the `BrandConfig` interface:

```tsx
interface BrandConfig {
  brand_name: string
  primary_color?: string
  secondary_color?: string
  accent_color?: string
  bg_color?: string
  text_color?: string
  font_family?: string
  heading_font?: string
  border_radius?: number
  logo_url?: string
}
```

Change the default brand name:

```tsx
  const [brandConfig, setBrandConfig] = useState<BrandConfig>({ brand_name: 'SRSUK Learning Portal' })
```

- [ ] **Step 2: Replace the outer layout with a two-column gradient layout**

Replace the entire `return ( ... )` block with the following. The sign-in form, MFA flow, and error handling are preserved exactly — only the surrounding layout changes:

```tsx
  return (
    <div className="min-h-screen flex flex-col md:flex-row">
      {/* Brand panel */}
      <div className="bg-brand-gradient text-white md:w-1/2 flex flex-col justify-center items-start p-10 md:p-16">
        <img
          src={brandConfig.logo_url || stadlerLogo}
          alt={brandConfig.brand_name}
          className="h-10 w-auto mb-8"
          style={brandConfig.logo_url ? undefined : { filter: 'brightness(0) invert(1)' }}
        />
        <h1 className="text-3xl md:text-4xl font-bold uppercase tracking-wide">
          {brandConfig.brand_name}
        </h1>
        <div className="w-16 h-1 bg-brand-accent my-5" />
        <p className="text-white/80 max-w-sm">
          People Manager training and learning, aligned to the Stadler corporate standard.
        </p>
      </div>

      {/* Sign-in panel */}
      <div className="md:w-1/2 flex items-center justify-center p-6 bg-brand-surface">
        <Card className="w-full max-w-md">
          <div className="p-8">
            <div className="text-center mb-8">
              <h2 className="text-2xl font-bold mb-2 text-brand-dark">Sign in</h2>
              <p className="text-gray-600">Welcome back. Please enter your details.</p>
            </div>

            <form onSubmit={handleLogin}>
              {!requiresMfa ? (
                <>
                  <Input
                    type="text"
                    label="Username"
                    placeholder="Enter your username"
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    required
                  />
                  <Input
                    type="password"
                    label="Password"
                    placeholder="Enter your password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                  />
                </>
              ) : (
                <Input
                  type="text"
                  label="MFA Code"
                  placeholder="Enter 6-digit code"
                  value={mfaCode}
                  onChange={(e) => setMfaCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                  maxLength={6}
                  required
                />
              )}

              {error && (
                <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded text-red-700 text-sm">
                  {error}
                </div>
              )}

              <Button
                type="submit"
                fullWidth
                disabled={isLoading}
              >
                {isLoading ? '⏳ Processing...' : (requiresMfa ? 'Verify MFA' : 'Sign In')}
              </Button>

              {requiresMfa && (
                <Button
                  type="button"
                  variant="ghost"
                  fullWidth
                  onClick={() => {
                    setRequiresMfa(false)
                    setMfaCode('')
                    setPassword('')
                  }}
                  className="mt-2"
                >
                  Back to Login
                </Button>
              )}
            </form>
          </div>
        </Card>
      </div>
    </div>
  )
```

- [ ] **Step 3: Verify the build**

Run: `npm run build`
Expected: completes with no errors. (`applyTheme` is still called from the effect and remains used.)

- [ ] **Step 4: Commit**

```bash
git add src/pages/LoginPage.tsx
git commit -m "feat(frontend): Stadler gradient login screen with logo"
```

---

### Task 8: Learner navigation — logo + Stadler hover states

**Files:**
- Modify: `frontend/src/components/layout/LearnerLayout.tsx`

- [ ] **Step 1: Import the logo**

Add after the existing imports:

```tsx
import stadlerLogo from '@/assets/stadler-logo.png'
```

- [ ] **Step 2: Replace the brand wordmark with the logo and brand the hover**

Replace:

```tsx
            <span
              className="text-lg font-bold text-gray-900 cursor-pointer"
              onClick={() => navigate('/learn')}
            >
              LMS Course Builder
            </span>
```

with:

```tsx
            <img
              src={stadlerLogo}
              alt="SRSUK Learning Portal"
              className="h-7 w-auto cursor-pointer"
              onClick={() => navigate('/learn')}
            />
```

Replace the logout button className:

```tsx
                className="text-sm text-gray-600 hover:text-gray-900 px-3 py-1 rounded border border-gray-300 hover:border-gray-400 transition-colors"
```

with:

```tsx
                className="text-sm text-gray-600 hover:text-brand px-3 py-1 rounded border border-gray-300 hover:border-brand transition-colors"
```

- [ ] **Step 3: Verify the build**

Run: `npm run build`
Expected: completes with no errors.

- [ ] **Step 4: Commit**

```bash
git add src/components/layout/LearnerLayout.tsx
git commit -m "feat(frontend): Stadler logo and hover states in learner nav"
```

---

### Task 9: White-label default config → Stadler

**Files:**
- Modify: `frontend/src/pages/admin/WhiteLabelPage.tsx:25-38` (`DEFAULT_CONFIG`)

- [ ] **Step 1: Replace `DEFAULT_CONFIG` with Stadler values**

Replace the `DEFAULT_CONFIG` object:

```tsx
const DEFAULT_CONFIG: WhiteLabelConfig = {
  brand_name: 'SRSUK Learning Portal',
  primary_color: '#1E5A9A',
  secondary_color: '#0B3F75',
  accent_color: '#FFBD00',
  bg_color: '#F0F7FE',
  text_color: '#0B3F75',
  font_family: 'Arial',
  heading_font: 'Arial',
  border_radius: 8,
  custom_css: '',
  logo_url: '',
  favicon_url: '',
}
```

Add `Arial` to both font `Select` option lists so the default value is selectable. In each `options={[ ... ]}` array (Font Family and Heading Font), add as the first entry:

```tsx
              { value: 'Arial', label: 'Arial (Stadler)' },
```

- [ ] **Step 2: Verify the build**

Run: `npm run build`
Expected: completes with no errors.

- [ ] **Step 3: Commit**

```bash
git add src/pages/admin/WhiteLabelPage.tsx
git commit -m "feat(frontend): default white-label config to Stadler brand"
```

---

### Task 10: Full verification — build, tests, browser walkthrough

**Files:** none (verification only)

- [ ] **Step 1: Run the unit test suite**

Run: `npm run test:unit`
Expected: all tests pass, including the new `Button.test.tsx`.

- [ ] **Step 2: Run the production build**

Run: `npm run build`
Expected: `tsc -b` and `vite build` both succeed; `dist/` is written.

- [ ] **Step 3: Browser walkthrough**

Run: `npm run dev` (serves at `http://localhost:5173/lms/`).

Visit and visually confirm Stadler styling on each surface:
- `/lms/login` — gradient brand panel on the left with the **white** Stadler logo, yellow accent rule, sign-in card on Stadler off-white. Buttons are Stadler blue.
- `/lms/admin` (log in as admin) — dark-blue sidebar, white logo at top, active nav item is Stadler blue with a yellow left bar, page title has a yellow underline.
- `/lms/creator` — same sidebar treatment; the user avatar is Stadler blue (not purple/indigo).
- `/lms/learn` — Stadler logo in the nav; logout hover turns Stadler blue.
- `/lms/admin/whitelabel` — "Reset" returns the colour pickers to the Stadler palette and Arial.

Expected: no generic indigo/purple brand colour remains in the chrome; everything reads Stadler blue + Arial with sparing yellow accents. (The `/api` proxy targets `localhost:8000`; if the backend is not running, the white-label fetch fails gracefully and the bundled Stadler defaults are used — chrome styling is still verifiable.)

- [ ] **Step 4: Final commit (only if any fixes were made during verification)**

```bash
git add -A
git commit -m "fix(frontend): Stadler rebrand verification fixes"
```

---

## Self-Review

**Spec coverage** (against `docs/superpowers/specs/2026-05-21-stadler-lms-rebrand-design.md`):
- Tailwind tokens (blue remap, brand aliases, Arial, gradient) → Task 1 ✓
- `globals.css` defaults → Task 2 ✓
- Logo asset + `index.html` title/favicon → Task 3 ✓
- Button accent variant → Task 4 ✓
- Admin sidebar/header → Task 5 ✓
- Creator sidebar/header + avatar fix → Task 6 ✓
- Login gradient panel + logo → Task 7 ✓
- Learner nav → Task 8 ✓
- White-label `DEFAULT_CONFIG` → Task 9 ✓
- Build/test/browser success criteria → Task 10 ✓

**Placeholder scan:** no TBD/TODO; every code step shows complete code; commands have expected output.

**Type consistency:** the logo import path `@/assets/stadler-logo.png` is identical in Tasks 5–8; `bg-brand-dark`, `bg-brand-gradient`, `bg-brand-accent`, `text-brand-dark`, `border-brand-accent`, `bg-brand-surface`, `hover:text-brand` all resolve to tokens defined in Task 1; `logo_url` field added to `BrandConfig` (Task 7) matches the white-label `logo_url` field; the `accent` variant name matches between the test (Task 4 Step 1) and implementation (Task 4 Step 3).
