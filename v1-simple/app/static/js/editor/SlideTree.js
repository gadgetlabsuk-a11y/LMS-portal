// Slide Tree — left nav showing course > module > lesson > slides
function SlideTree({ courseId, selectedSlideId, onSelectSlide, onRefresh }) {
  const [tree, setTree] = React.useState(null);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState('');

  React.useEffect(() => {
    loadTree();
  }, [courseId]);

  async function loadTree() {
    setLoading(true);
    try {
      const course = await LmsApi.apiFetch(`/api/courses/${courseId}`);
      setTree(course);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  async function addModule() {
    const title = prompt('Module title:');
    if (!title) return;
    await LmsApi.apiFetch(`/api/courses/${courseId}/modules`, {
      method: 'POST',
      body: JSON.stringify({ title, position: (tree?.modules?.length || 0) }),
    });
    loadTree();
  }

  async function addLesson(moduleId, position) {
    const title = prompt('Lesson title:');
    if (!title) return;
    await LmsApi.apiFetch(`/api/modules/${moduleId}/lessons`, {
      method: 'POST',
      body: JSON.stringify({ title, position }),
    });
    loadTree();
  }

  async function addSlide(lessonId, position) {
    await LmsApi.apiFetch(`/api/lessons/${lessonId}/slides`, {
      method: 'POST',
      body: JSON.stringify({ layout: 'single-column', position }),
    });
    loadTree();
  }

  if (loading) return React.createElement('div', { className: 'slide-tree loading', 'aria-busy': 'true' }, 'Loading…');
  if (error) return React.createElement('div', { className: 'slide-tree error', role: 'alert' }, error);
  if (!tree) return null;

  return React.createElement('nav', { className: 'slide-tree', 'aria-label': 'Course structure' },
    React.createElement('div', { className: 'tree-header' },
      React.createElement('strong', null, tree.title),
      React.createElement('button', { onClick: addModule, 'aria-label': 'Add module', className: 'btn-sm' }, '+ Module')
    ),
    (tree.modules || []).map(mod =>
      React.createElement('div', { key: mod.id, className: 'tree-module' },
        React.createElement('div', { className: 'tree-module-title' },
          React.createElement('span', null, mod.title),
          React.createElement('button', {
            onClick: () => addLesson(mod.id, (mod.lessons?.length || 0)),
            'aria-label': `Add lesson to ${mod.title}`,
            className: 'btn-sm',
          }, '+ Lesson')
        ),
        (mod.lessons || []).map(lesson =>
          React.createElement('div', { key: lesson.id, className: 'tree-lesson' },
            React.createElement('div', { className: 'tree-lesson-title' },
              React.createElement('span', null, lesson.title),
              React.createElement('button', {
                onClick: () => addSlide(lesson.id, (lesson.slides?.length || 0)),
                'aria-label': `Add slide to ${lesson.title}`,
                className: 'btn-sm',
              }, '+ Slide')
            ),
            (lesson.slides || []).map((slide, si) =>
              React.createElement('button', {
                key: slide.id,
                className: 'tree-slide' + (slide.id === selectedSlideId ? ' selected' : ''),
                onClick: () => onSelectSlide(slide),
                'aria-current': slide.id === selectedSlideId ? 'true' : undefined,
                'aria-label': `Slide ${si + 1}${slide.title ? ': ' + slide.title : ''}`,
              }, `Slide ${si + 1}` + (slide.title ? ` — ${slide.title}` : ''))
            )
          )
        )
      )
    )
  );
}
