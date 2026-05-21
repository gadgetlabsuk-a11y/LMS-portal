# Stadler Corporate Rebrand — LMS Frontend

**Date:** 2026-05-21
**Author:** Stuart Roberts (with Claude)
**Status:** Approved design, pending implementation plan

## Objective

Restyle the LMS web frontend to comply with the Stadler corporate design system, as
extracted from the Stadler Design Guidelines (June 2016) and the SRSUK Absence Management
design brief. The deliverable is a visually on-brand LMS — not a slide deck. Slide-deck
specific artifacts (swim lanes, donut charts, recap mechanics) are explicitly out of scope.

Chosen depth: **tokens + chrome upgrade**. Remap the colour palette and typography globally
(auto-rebrands all existing UI), then hand-upgrade the high-visibility chrome.

## Brand system (source of truth)

| Role | Name | Hex |
|------|------|-----|
| Primary | Stadler Blue | `#1E5A9A` |
| Secondary light | Light Blue | `#007BC0` |
| Secondary dark | Dark Blue | `#0B3F75` |
| Accent | Warm Yellow | `#FFBD00` |
| Surface | Cool Off-white | `#F0F7FE` |

- **Gradient:** `linear-gradient(-45deg, #007BC0, #0B3F75)` (light → dark blue, fixed −45°).
  Used for cover/hero surfaces only (login panel, sidebar).
- **Typography:** Arial throughout (system font, no webfont). Headings bold, often CAPS,
  Dark Blue on white / white on gradient.
- **Yellow:** used sparingly — thin accent rules (2–3px), active-state markers, optional
  highlight button. Never large fill blocks.
- **Logo:** Stadler wordmark. Primary blue on white; white (negative) version on gradient/dark.

## Current architecture (as found)

- **Stack:** Vite + React 18 + Tailwind 3 + react-router. 70 `.tsx` files.
- **Theming today is split across two pathways that don't agree:**
  1. `src/styles/globals.css` defines CSS vars (`--primary #2563eb`, `--secondary #7c3aed`,
     `--accent #f59e0b`, `--bg`, `--text`, `--font-family: Inter`) and a few utility classes
     (`.primary-bg`, `.primary-text`). Consumed only by `LoginPage` (inline styles) and the
     white-label preview.
  2. **Components mostly use hardcoded Tailwind classes** — `bg-blue-600` (18×),
     `bg-blue-700` (13×), `bg-blue-500`/`ring-blue-500`, `text-blue-600`, `bg-blue-50`,
     `bg-indigo-600` (creator avatar), plus neutral grays. `tailwind.config.js` theme is empty.
- A **white-label admin page** (`pages/admin/WhiteLabelPage.tsx`) writes config to the backend
  (`/whitelabel/config`, `/api/whitelabel/preview`) and applies it by setting CSS vars at
  runtime. `DEFAULT_CONFIG` is the generic blue/purple/Inter set. Layouts and LoginPage fetch
  this config (layouts only read `brand_name`).

**Implication:** the highest-leverage move is to remap Tailwind's `blue` scale to the Stadler
palette — every hardcoded `blue-*` usage rebrands with zero per-component edits — and align the
CSS-var defaults and white-label `DEFAULT_CONFIG` so both pathways reflect Stadler.

## Approach

Chosen: **Tailwind palette remap + CSS-variable defaults + targeted chrome upgrade.**

Rejected alternatives:
- *Semantic-token refactor* (replace every `blue-*` with `brand-*` across 24 files): correct
  long-term but high churn/risk for no visual gain now.
- *Fully wire components to live CSS vars*: enables runtime per-tenant theming, but a large
  refactor not needed for a single-brand Stadler LMS.

## Detailed changes

### 1. Design tokens — `frontend/tailwind.config.js`

Extend `theme`:
- **Remap `colors.blue` scale** so existing usages become Stadler:
  - `blue-50` = `#F0F7FE` (off-white panels / `bg-blue-50`, ghost hover)
  - `blue-500` = `#007BC0` (focus rings)
  - `blue-600` = `#1E5A9A` (primary — buttons, active nav, avatars)
  - `blue-700` = `#0B3F75` (hover / dark)
  - fill the remaining stops (100–400, 800–900) with a coherent Stadler-blue ramp.
- **Semantic aliases:** `brand` `#1E5A9A`, `brand-dark` `#0B3F75`, `brand-light` `#007BC0`,
  `brand-accent` `#FFBD00`, `brand-surface` `#F0F7FE`.
- **Font:** `fontFamily.sans = ['Arial', 'Helvetica', 'sans-serif']`.
- **Gradient utility:** `backgroundImage['brand-gradient'] = 'linear-gradient(-45deg, #007BC0, #0B3F75)'`
  (usable as `bg-brand-gradient`).

### 2. `frontend/src/styles/globals.css`

Update `:root` defaults to Stadler so the CSS-var / inline-style path agrees:
- `--primary: #1E5A9A`, `--secondary: #0B3F75`, `--accent: #FFBD00`,
  `--bg: #F0F7FE`, `--text: #0B3F75`, `--font-family: Arial, Helvetica, sans-serif`,
  `--heading-font: Arial, Helvetica, sans-serif`.
- Keep existing utility classes, animations, toast/badge styles. Update `.toast.info` /
  `.badge.info` / `.chart-bar` to read Stadler blue (they already use `var(--primary)` where applicable).

### 3. White-label default — `frontend/src/pages/admin/WhiteLabelPage.tsx`

Set `DEFAULT_CONFIG` to Stadler values (brand_name "Stadler" or "SRSUK", primary `#1E5A9A`,
secondary `#0B3F75`, accent `#FFBD00`, bg `#F0F7FE`, text `#0B3F75`, font Arial) so first-load
and "Reset" stay on-brand. Behaviour unchanged otherwise.

### 4. Logo asset

- Copy `~/Downloads/stalder logo.png` → `frontend/src/assets/stadler-logo.png`.
- Import in components; Vite handles hashing and the `/lms` prod base path.
- **On white surfaces** (login card, learner nav): use as-is (blue on white).
- **On dark-blue / gradient** (sidebars, login gradient panel): apply
  `filter: brightness(0) invert(1)` to render pure white (negative version).
- White-label `logo_url`, when set, overrides the bundled asset.

### 5. Chrome upgrades

- **Login** (`pages/LoginPage.tsx`): two-column layout. Left = full-bleed `bg-brand-gradient`
  with the white logo + brand name + a thin yellow accent rule. Right = existing sign-in card
  (white, blue logo optional). Collapses to single column on mobile. Keep MFA flow intact.
- **Admin sidebar** (`components/layout/AdminLayout.tsx`): `bg-gray-900` → `brand-dark`
  (`#0B3F75`). Active nav item = Stadler blue (`bg-blue-600`) with a yellow left-accent bar.
  White logo at top (replaces the `◉`/text). Avatar already `bg-blue-600` (now Stadler blue).
- **Creator sidebar** (`components/layout/CreatorLayout.tsx`): same sidebar treatment; fix
  avatar `bg-indigo-600` → `bg-blue-600` (brand).
- **Top bars / page headers** (both layouts): page title in Dark Blue, bold, with a thin
  yellow underline rule (the brand's signature accent).
- **Learner nav** (`components/layout/LearnerLayout.tsx`): brand logo/wordmark, Stadler-blue
  hover states.
- **Button** (`components/common/Button.tsx`): primary/ghost inherit the remapped blues
  automatically. Add an optional `accent` variant (`bg-brand-accent text-brand-dark`) for
  sparing yellow highlights per the guideline.
- **`frontend/index.html`**: `<title>` → Stadler/SRSUK; favicon updated to the Stadler mark.

## Out of scope

- Slide-deck artifacts (swim-lane diagrams, donut charts, recap reveal mechanics) — these
  belong to the PowerPoint deliverable in the brief, not the LMS UI.
- Course *content* slides authored inside the builder — authored content is left untouched.
- Backend changes beyond the white-label default value.
- Runtime per-tenant theme switching / wiring every component to live CSS vars.
- Akkurat Pro webfont (print-only per guidelines; Arial is mandated for internal/screen).

## Success criteria

- Every primary button, link, focus ring, active nav item, and avatar renders in Stadler blue.
- App font is Arial throughout.
- Login, both admin/creator sidebars, and the learner nav carry the Stadler logo and the
  gradient/dark-blue treatment with yellow accents.
- White-label admin "Reset" returns to the Stadler palette, not the old blue/purple.
- `npm run build` (tsc + vite) passes; the app renders correctly in the browser.
- No generic `indigo`/`purple` brand colour remains in the chrome.
