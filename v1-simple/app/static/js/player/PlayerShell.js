// Learner-facing course player
function PlayerShell({ courseId, userId }) {
  const [course, setCourse] = React.useState(null);
  const [allSlides, setAllSlides] = React.useState([]);
  const [currentIdx, setCurrentIdx] = React.useState(0);
  const [slide, setSlide] = React.useState(null);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState('');

  React.useEffect(() => {
    loadCourse();
  }, [courseId]);

  async function loadCourse() {
    setLoading(true);
    try {
      const data = await LmsApi.apiFetch(`/api/courses/${courseId}`);
      setCourse(data);

      // Flatten slides
      const slides = [];
      for (const mod of data.modules || []) {
        for (const lesson of mod.lessons || []) {
          for (const s of lesson.slides || []) {
            slides.push({ ...s, lessonTitle: lesson.title, moduleTitle: mod.title });
          }
        }
      }
      setAllSlides(slides);

      if (slides.length > 0) {
        await loadSlide(slides[0], 0);
      }
    } catch (e) {
      setError('Failed to load course: ' + e.message);
    } finally {
      setLoading(false);
    }
  }

  async function loadSlide(slideRef, idx) {
    try {
      const full = await LmsApi.apiFetch(`/api/slides/${slideRef.id}`);
      setSlide(full);
      setCurrentIdx(idx);
    } catch (e) {
      setError('Failed to load slide: ' + e.message);
    }
  }

  function goNext() {
    const next = currentIdx + 1;
    if (next < allSlides.length) loadSlide(allSlides[next], next);
  }

  function goPrev() {
    const prev = currentIdx - 1;
    if (prev >= 0) loadSlide(allSlides[prev], prev);
  }

  if (loading) return React.createElement('div', { 'aria-busy': 'true', className: 'player-loading' }, 'Loading course…');
  if (error) return React.createElement('div', { role: 'alert', className: 'player-error' }, error);
  if (!course) return null;

  return React.createElement('div', { className: 'player-shell' },
    React.createElement('a', { href: '#main-slide', className: 'skip-link' }, 'Skip to slide content'),
    React.createElement('header', { className: 'player-header' },
      React.createElement('span', { className: 'player-course-title' }, course.title),
      React.createElement('span', { className: 'player-counter', 'aria-label': `Slide ${currentIdx + 1} of ${allSlides.length}` },
        `${currentIdx + 1} / ${allSlides.length}`
      )
    ),
    React.createElement('main', {
      id: 'main-slide',
      className: 'player-slide',
      tabIndex: -1,
      'aria-label': slide?.title || `Slide ${currentIdx + 1}`,
      'aria-live': 'polite',
    },
      slide && React.createElement(BlockViewer, { blocks: slide.blocks || [] })
    ),
    React.createElement('nav', { className: 'player-nav', 'aria-label': 'Slide navigation' },
      React.createElement('button', {
        onClick: goPrev,
        disabled: currentIdx === 0,
        'aria-label': 'Previous slide',
        className: 'player-btn',
      }, '← Prev'),
      React.createElement('div', { className: 'player-progress' },
        React.createElement('div', {
          className: 'player-progress-bar',
          role: 'progressbar',
          'aria-valuenow': currentIdx + 1,
          'aria-valuemin': 1,
          'aria-valuemax': allSlides.length,
          style: { width: `${((currentIdx + 1) / allSlides.length) * 100}%` },
        })
      ),
      React.createElement('button', {
        onClick: goNext,
        disabled: currentIdx === allSlides.length - 1,
        'aria-label': 'Next slide',
        className: 'player-btn',
      }, 'Next →')
    )
  );
}
