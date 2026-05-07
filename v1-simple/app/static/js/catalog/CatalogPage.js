// Catalog page — browse and enrol in courses
function CatalogPage() {
  const [courses, setCourses] = React.useState([]);
  const [q, setQ] = React.useState('');
  const [loading, setLoading] = React.useState(true);
  const [status, setStatus] = React.useState('');

  React.useEffect(() => { loadCatalog(); }, []);

  async function loadCatalog(query = '') {
    setLoading(true);
    try {
      const data = await LmsApi.apiFetch(`/api/catalog?q=${encodeURIComponent(query)}&limit=20`);
      setCourses(data);
    } catch (e) {
      setStatus('Failed to load catalog: ' + e.message);
    } finally {
      setLoading(false);
    }
  }

  async function enrol(courseId) {
    try {
      await LmsApi.apiFetch(`/api/catalog/${courseId}/enrol`, { method: 'POST' });
      setStatus('Enrolled! Opening course…');
      setTimeout(() => {
        window.location.hash = `#/learn/${courseId}`;
      }, 1000);
    } catch (e) {
      setStatus('Enrolment failed: ' + e.message);
    }
  }

  return React.createElement('div', { className: 'catalog-page' },
    React.createElement('h1', null, 'Course Catalogue'),
    React.createElement('div', { className: 'catalog-search' },
      React.createElement('label', { htmlFor: 'catalog-search-input', className: 'sr-only' }, 'Search courses'),
      React.createElement('input', {
        id: 'catalog-search-input',
        type: 'search',
        placeholder: 'Search courses…',
        value: q,
        onChange: e => setQ(e.target.value),
        onKeyDown: e => e.key === 'Enter' && loadCatalog(q),
        'aria-label': 'Search courses',
      }),
      React.createElement('button', { onClick: () => loadCatalog(q), 'aria-label': 'Search' }, 'Search')
    ),
    status && React.createElement('p', { role: 'alert', 'aria-live': 'assertive', className: 'catalog-status' }, status),
    loading
      ? React.createElement('p', { 'aria-busy': 'true' }, 'Loading…')
      : courses.length === 0
        ? React.createElement('p', null, 'No courses found.')
        : React.createElement('div', { className: 'catalog-grid' },
            courses.map(c => React.createElement(CatalogCard, { key: c.id, course: c, onEnrol: enrol }))
          )
  );
}

function CatalogCard({ course, onEnrol }) {
  const price = course.price_pence > 0
    ? `£${(course.price_pence / 100).toFixed(2)}`
    : 'Free';

  return React.createElement('article', { className: 'catalog-card' },
    React.createElement('div', { className: 'card-body' },
      React.createElement('h2', { className: 'card-title' }, course.title),
      React.createElement('p', { className: 'card-desc' }, course.description),
      React.createElement('div', { className: 'card-meta' },
        course.estimated_minutes && React.createElement('span', null, `${course.estimated_minutes} min`),
        React.createElement('span', null, `${course.enrolment_count || 0} enrolled`),
      ),
    ),
    React.createElement('div', { className: 'card-footer' },
      React.createElement('span', { className: 'card-price' }, price),
      course.self_enrol_enabled
        ? React.createElement('button', {
            className: 'btn-enrol',
            onClick: () => onEnrol(course.id),
            'aria-label': `Enrol in ${course.title}`,
          }, price === 'Free' ? 'Enrol free' : `Pay ${price}`)
        : React.createElement('span', { className: 'card-tag' }, 'Admin enrol only')
    )
  );
}
