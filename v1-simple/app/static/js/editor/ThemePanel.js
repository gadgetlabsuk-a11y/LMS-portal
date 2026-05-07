// Theme picker and per-course token overrides
function ThemePanel({ courseId }) {
  const [themes, setThemes] = React.useState([]);
  const [courseTheme, setCourseTheme] = React.useState(null);
  const [primaryOverride, setPrimaryOverride] = React.useState('');
  const [saving, setSaving] = React.useState(false);
  const [status, setStatus] = React.useState('');

  React.useEffect(() => {
    LmsApi.apiFetch('/api/themes').then(setThemes).catch(() => {});
    LmsApi.apiFetch(`/api/courses/${courseId}/theme`).then(ct => {
      setCourseTheme(ct);
      setPrimaryOverride(ct?.overrides?.colors?.primary || '');
    }).catch(() => {});
  }, [courseId]);

  async function applyTheme(themeId) {
    setSaving(true);
    try {
      const overrides = primaryOverride ? { colors: { primary: primaryOverride } } : null;
      await LmsApi.apiFetch(`/api/courses/${courseId}/theme`, {
        method: 'PUT',
        body: JSON.stringify({ theme_id: themeId, overrides }),
      });
      setStatus('Theme saved');
      const ct = await LmsApi.apiFetch(`/api/courses/${courseId}/theme`);
      setCourseTheme(ct);
      if (window.LmsTokens) LmsTokens.applyThemeTokens(ct.tokens, ct.overrides);
    } catch (e) {
      setStatus('Error: ' + e.message);
    } finally {
      setSaving(false);
      setTimeout(() => setStatus(''), 3000);
    }
  }

  return React.createElement('div', { className: 'theme-panel' },
    React.createElement('h3', null, 'Theme'),
    React.createElement('div', { className: 'theme-grid' },
      themes.map(t =>
        React.createElement('button', {
          key: t.id,
          className: 'theme-card' + (courseTheme?.theme_id === t.id ? ' active' : ''),
          onClick: () => applyTheme(t.id),
          'aria-pressed': courseTheme?.theme_id === t.id,
          style: { borderColor: t.tokens?.colors?.primary || '#ccc' },
        },
          React.createElement('span', {
            className: 'theme-swatch',
            style: { background: t.tokens?.colors?.primary || '#ccc' },
            'aria-hidden': 'true',
          }),
          t.name
        )
      )
    ),
    React.createElement('label', { className: 'field' },
      'Primary colour override',
      React.createElement('input', {
        type: 'color',
        value: primaryOverride || '#1f3a5f',
        onChange: e => setPrimaryOverride(e.target.value),
        'aria-label': 'Override primary colour',
      })
    ),
    React.createElement('button', {
      onClick: () => courseTheme && applyTheme(courseTheme.theme_id),
      disabled: !courseTheme || saving,
      className: 'btn-primary',
    }, saving ? 'Saving…' : 'Apply override'),
    status && React.createElement('p', { role: 'status', 'aria-live': 'polite', className: 'status-msg' }, status)
  );
}
