// Shared API client with auth header injection
const BASE = '';

async function apiFetch(path, options = {}) {
  const userId = localStorage.getItem('lms_user_id') || 'system';
  const headers = {
    'Content-Type': 'application/json',
    'X-User-ID': userId,
    ...(options.headers || {}),
  };
  const resp = await fetch(BASE + path, { ...options, headers });
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({ detail: resp.statusText }));
    throw new Error(err.detail || `HTTP ${resp.status}`);
  }
  if (resp.status === 204) return null;
  return resp.json();
}

async function apiUpload(path, formData) {
  const userId = localStorage.getItem('lms_user_id') || 'system';
  const resp = await fetch(BASE + path, {
    method: 'POST',
    headers: { 'X-User-ID': userId },
    body: formData,
  });
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({ detail: resp.statusText }));
    throw new Error(err.detail || `HTTP ${resp.status}`);
  }
  return resp.json();
}

window.LmsApi = { apiFetch, apiUpload };
