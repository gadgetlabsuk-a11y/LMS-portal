// Apply theme tokens as CSS variables
function applyThemeTokens(tokens, overrides = {}) {
  const merged = deepMerge(tokens, overrides);
  const root = document.documentElement;
  const c = merged.colors || {};
  const t = merged.typography || {};
  const s = merged.spacing || {};
  const r = merged.radius || {};

  if (c.primary)   root.style.setProperty('--color-primary', c.primary);
  if (c.secondary) root.style.setProperty('--color-secondary', c.secondary);
  if (c.accent)    root.style.setProperty('--color-accent', c.accent);
  if (c.bg)        root.style.setProperty('--color-bg', c.bg);
  if (c.text)      root.style.setProperty('--color-text', c.text);
  if (c.muted)     root.style.setProperty('--color-muted', c.muted);
  if (t.body_family)    root.style.setProperty('--font-body', t.body_family);
  if (t.heading_family) root.style.setProperty('--font-heading', t.heading_family);
  if (s.slide_padding)  root.style.setProperty('--slide-padding', s.slide_padding + 'px');
  if (r.md)        root.style.setProperty('--radius-md', r.md + 'px');
}

function deepMerge(base, override) {
  if (!override) return base;
  const result = { ...base };
  for (const key of Object.keys(override || {})) {
    if (typeof override[key] === 'object' && !Array.isArray(override[key])) {
      result[key] = deepMerge(base[key] || {}, override[key]);
    } else {
      result[key] = override[key];
    }
  }
  return result;
}

window.LmsTokens = { applyThemeTokens };
