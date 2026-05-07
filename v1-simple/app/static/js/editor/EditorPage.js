// Editor page — top-level component wiring SlideTree + BlockEditor + ThemePanel
function EditorPage({ courseId }) {
  const [selectedSlide, setSelectedSlide] = React.useState(null);
  const [showTheme, setShowTheme] = React.useState(false);
  const [showMedia, setShowMedia] = React.useState(false);
  const [slide, setSlide] = React.useState(null);

  async function loadSlide(slideRef) {
    try {
      const full = await LmsApi.apiFetch(`/api/slides/${slideRef.id}`);
      setSlide(full);
      setSelectedSlide(slideRef);
    } catch (e) {
      console.error('Failed to load slide', e);
    }
  }

  return React.createElement('div', { className: 'editor-page' },
    React.createElement('aside', { className: 'editor-sidebar', 'aria-label': 'Course navigation' },
      React.createElement(SlideTree, {
        courseId,
        selectedSlideId: selectedSlide?.id,
        onSelectSlide: loadSlide,
      })
    ),
    React.createElement('main', { className: 'editor-main', id: 'main-content', tabIndex: -1 },
      React.createElement('div', { className: 'editor-toolbar' },
        React.createElement('button', {
          onClick: () => setShowTheme(t => !t),
          'aria-expanded': showTheme,
          'aria-controls': 'theme-panel',
          className: showTheme ? 'active' : '',
        }, 'Theme'),
        React.createElement('button', {
          onClick: () => setShowMedia(m => !m),
          'aria-expanded': showMedia,
          'aria-controls': 'media-panel',
        }, 'Media')
      ),
      showTheme && React.createElement('div', { id: 'theme-panel' },
        React.createElement(ThemePanel, { courseId })
      ),
      showMedia && React.createElement('div', { id: 'media-panel' },
        React.createElement(MediaPicker, { courseId, onSelect: (asset) => console.log('Selected:', asset) })
      ),
      React.createElement(BlockEditor, { courseId, slide, onSave: () => {} })
    )
  );
}
