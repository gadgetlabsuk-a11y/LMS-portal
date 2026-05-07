// Learner report table — shows enrolment status for a user or course
function ReportTable({ userId, courseId }) {
  const [rows, setRows] = React.useState([]);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState('');

  React.useEffect(() => {
    load();
  }, [userId, courseId]);

  async function load() {
    setLoading(true);
    try {
      let data;
      if (userId) {
        data = await LmsApi.apiFetch(`/api/reports/learner/${userId}`);
        setRows(data);
      } else if (courseId) {
        const resp = await LmsApi.apiFetch(`/api/reports/course/${courseId}`);
        setRows(resp.learners || []);
      }
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  async function downloadCsv() {
    const url = userId
      ? `/api/reports/learner/${userId}.csv`
      : `/api/reports/course/${courseId}.csv`;
    const uid = localStorage.getItem('lms_user_id') || 'system';
    const resp = await fetch(url, { headers: { 'X-User-ID': uid } });
    const blob = await resp.blob();
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = 'report.csv';
    a.click();
  }

  if (loading) return React.createElement('p', { 'aria-busy': 'true' }, 'Loading report…');
  if (error) return React.createElement('p', { role: 'alert' }, error);

  const isLearner = !!userId;
  const headers = isLearner
    ? ['Course', 'Enrolled', 'Completed', 'Progress', 'Score', 'Due', 'Status']
    : ['Learner', 'Enrolled', 'Completed', 'Progress', 'Score', 'Status'];

  return React.createElement('div', { className: 'report-wrap' },
    React.createElement('div', { className: 'report-toolbar' },
      React.createElement('button', { onClick: downloadCsv, className: 'btn-download', 'aria-label': 'Download CSV report' }, 'Download CSV')
    ),
    React.createElement('div', { className: 'table-scroll' },
      React.createElement('table', { className: 'report-table' },
        React.createElement('thead', null,
          React.createElement('tr', null,
            headers.map(h => React.createElement('th', { key: h, scope: 'col' }, h))
          )
        ),
        React.createElement('tbody', null,
          rows.length === 0
            ? React.createElement('tr', null,
                React.createElement('td', { colSpan: headers.length, style: { textAlign: 'center', padding: '24px', color: '#6b7280' } }, 'No data')
              )
            : rows.map((row, i) =>
                React.createElement('tr', { key: i },
                  isLearner ? [
                    React.createElement('td', { key: 'ct' }, row.course_title),
                    React.createElement('td', { key: 'ea' }, row.enrolled_at ? new Date(row.enrolled_at).toLocaleDateString('en-GB') : '—'),
                    React.createElement('td', { key: 'ca' }, row.completed_at ? new Date(row.completed_at).toLocaleDateString('en-GB') : '—'),
                    React.createElement('td', { key: 'pp' }, row.progress_pct != null ? `${row.progress_pct}%` : '—'),
                    React.createElement('td', { key: 'sc' }, row.score != null ? `${row.score}%` : '—'),
                    React.createElement('td', { key: 'dd' }, row.due_date ? new Date(row.due_date).toLocaleDateString('en-GB') : '—'),
                    React.createElement('td', { key: 'st' }, React.createElement('span', { className: `status-badge status-${row.status}` }, row.status)),
                  ] : [
                    React.createElement('td', { key: 'uid' }, row.user_id),
                    React.createElement('td', { key: 'ea' }, row.enrolled_at ? new Date(row.enrolled_at).toLocaleDateString('en-GB') : '—'),
                    React.createElement('td', { key: 'ca' }, row.completed_at ? new Date(row.completed_at).toLocaleDateString('en-GB') : '—'),
                    React.createElement('td', { key: 'pp' }, row.progress_pct != null ? `${row.progress_pct}%` : '—'),
                    React.createElement('td', { key: 'sc' }, row.score != null ? `${row.score}%` : '—'),
                    React.createElement('td', { key: 'st' }, React.createElement('span', { className: `status-badge status-${row.status}` }, row.status)),
                  ]
                )
              )
        )
      )
    )
  );
}
