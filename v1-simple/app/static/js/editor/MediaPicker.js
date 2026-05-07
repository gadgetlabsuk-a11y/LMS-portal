// Media picker — upload + Unsplash search + Lucide icon picker
function MediaPicker({ courseId, onSelect }) {
  const [tab, setTab] = React.useState('upload');
  const [assets, setAssets] = React.useState([]);
  const [unsplashQ, setUnsplashQ] = React.useState('');
  const [unsplashResults, setUnsplashResults] = React.useState([]);
  const [lucideQ, setLucideQ] = React.useState('');
  const [lucideResults, setLucideResults] = React.useState([]);
  const [uploading, setUploading] = React.useState(false);
  const [status, setStatus] = React.useState('');

  React.useEffect(() => {
    if (tab === 'upload') loadAssets();
    if (tab === 'lucide' && lucideResults.length === 0) searchLucide('');
  }, [tab]);

  async function loadAssets() {
    try {
      const list = await LmsApi.apiFetch(`/api/courses/${courseId}/media`);
      setAssets(list);
    } catch (e) { setStatus(e.message); }
  }

  async function handleUpload(e) {
    const file = e.target.files?.[0];
    if (!file) return;
    const fd = new FormData();
    fd.append('file', file);
    const altText = file.type.startsWith('image/') ? prompt('Alt text for this image (required):') : '';
    if (file.type.startsWith('image/') && !altText) { setStatus('Alt text is required for images'); return; }
    if (altText) fd.append('alt_text', altText);
    setUploading(true);
    try {
      const asset = await LmsApi.apiUpload(`/api/courses/${courseId}/media`, fd);
      setStatus('Uploaded!');
      setAssets(prev => [asset, ...prev]);
    } catch (e) { setStatus('Upload failed: ' + e.message); }
    finally { setUploading(false); }
  }

  async function searchUnsplash() {
    if (!unsplashQ) return;
    try {
      const data = await LmsApi.apiFetch(`/api/media/unsplash/search?q=${encodeURIComponent(unsplashQ)}`);
      setUnsplashResults(data.results || []);
    } catch (e) { setStatus('Unsplash: ' + e.message); }
  }

  async function importUnsplash(photo) {
    try {
      const asset = await LmsApi.apiFetch(`/api/courses/${courseId}/media/from-unsplash`, {
        method: 'POST',
        body: JSON.stringify({
          unsplash_id: photo.id,
          download_url: photo.urls.regular,
          alt_text: photo.alt_description || photo.description || '',
          thumb_url: photo.urls.thumb,
        }),
      });
      onSelect?.(asset);
      setStatus('Imported!');
    } catch (e) { setStatus('Import failed: ' + e.message); }
  }

  async function searchLucide(q) {
    setLucideQ(q);
    try {
      const data = await LmsApi.apiFetch(`/api/media/lucide/search?q=${encodeURIComponent(q)}&limit=40`);
      setLucideResults(data);
    } catch (e) {}
  }

  const tabs = [
    { id: 'upload', label: 'Library' },
    { id: 'unsplash', label: 'Unsplash' },
    { id: 'lucide', label: 'Icons' },
  ];

  return React.createElement('div', { className: 'media-picker' },
    React.createElement('div', { className: 'picker-tabs', role: 'tablist' },
      tabs.map(t => React.createElement('button', {
        key: t.id,
        role: 'tab',
        'aria-selected': tab === t.id,
        className: 'tab-btn' + (tab === t.id ? ' active' : ''),
        onClick: () => setTab(t.id),
      }, t.label))
    ),

    status && React.createElement('p', { role: 'alert', className: 'picker-status' }, status),

    tab === 'upload' && React.createElement('div', { role: 'tabpanel', 'aria-label': 'Library' },
      React.createElement('label', { className: 'upload-btn' },
        uploading ? 'Uploading…' : 'Upload file',
        React.createElement('input', { type: 'file', hidden: true, onChange: handleUpload, accept: 'image/*,video/*,audio/*,.pdf' })
      ),
      React.createElement('div', { className: 'asset-grid' },
        assets.map(a => React.createElement('button', {
          key: a.id,
          className: 'asset-thumb',
          onClick: () => onSelect?.(a),
          'aria-label': a.filename,
        },
          a.kind === 'image'
            ? React.createElement('img', { src: a.url, alt: a.alt_text || a.filename, loading: 'lazy' })
            : React.createElement('span', { className: 'asset-icon' }, a.kind)
        ))
      )
    ),

    tab === 'unsplash' && React.createElement('div', { role: 'tabpanel', 'aria-label': 'Unsplash search' },
      React.createElement('div', { className: 'search-row' },
        React.createElement('input', {
          type: 'search',
          placeholder: 'Search Unsplash…',
          value: unsplashQ,
          onChange: e => setUnsplashQ(e.target.value),
          onKeyDown: e => e.key === 'Enter' && searchUnsplash(),
          'aria-label': 'Search Unsplash photos',
        }),
        React.createElement('button', { onClick: searchUnsplash }, 'Search')
      ),
      React.createElement('div', { className: 'asset-grid' },
        unsplashResults.map(photo => React.createElement('button', {
          key: photo.id,
          className: 'asset-thumb',
          onClick: () => importUnsplash(photo),
          'aria-label': photo.alt_description || 'Unsplash photo',
        },
          React.createElement('img', { src: photo.urls.thumb, alt: photo.alt_description || '', loading: 'lazy' })
        ))
      )
    ),

    tab === 'lucide' && React.createElement('div', { role: 'tabpanel', 'aria-label': 'Lucide icon search' },
      React.createElement('input', {
        type: 'search',
        placeholder: 'Search icons…',
        value: lucideQ,
        onChange: e => searchLucide(e.target.value),
        'aria-label': 'Search Lucide icons',
      }),
      React.createElement('div', { className: 'icon-grid' },
        lucideResults.map(icon => React.createElement('button', {
          key: icon.name,
          className: 'icon-btn',
          onClick: () => onSelect?.({ kind: 'lucide', name: icon.name }),
          title: icon.name,
          'aria-label': icon.name,
        }, icon.name))
      )
    )
  );
}
