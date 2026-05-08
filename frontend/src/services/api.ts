// API_BASE: empty string in dev (Vite proxy forwards /api to localhost:8000)
// In prod: '/lms' prefix — Traefik strips /lms before forwarding to FastAPI,
// so FastAPI receives /api/... unchanged. This matches the monolith behaviour exactly.
export const API_BASE = import.meta.env.PROD ? '/lms' : ''

// Singleton navigate function — set once from within the React Router tree.
// Required because api.ts is a plain module (not a hook) and cannot call useNavigate directly.
// Pattern from: frontend/index.html.monolith.bak lines 356–359
let navigateFn: ((to: string) => void) | null = null

export const setNavigate = (fn: (to: string) => void): void => {
  navigateFn = fn
}

const handle401 = (): void => {
  localStorage.removeItem('token')
  navigateFn?.('/login')
}

const authHeaders = (): Record<string, string> => {
  const token = localStorage.getItem('token')
  return {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  }
}

export const api = {
  get: async (path: string, options: RequestInit = {}): Promise<Response> => {
    const res = await fetch(`${API_BASE}/api${path}`, {
      ...options,
      headers: { ...authHeaders(), ...((options.headers as Record<string, string>) ?? {}) },
    })
    if (res.status === 401) handle401()
    return res
  },

  post: async (path: string, body: unknown, options: RequestInit = {}): Promise<Response> => {
    const res = await fetch(`${API_BASE}/api${path}`, {
      method: 'POST',
      ...options,
      headers: { ...authHeaders(), ...((options.headers as Record<string, string>) ?? {}) },
      body: JSON.stringify(body),
    })
    if (res.status === 401) handle401()
    return res
  },

  put: async (path: string, body: unknown, options: RequestInit = {}): Promise<Response> => {
    const res = await fetch(`${API_BASE}/api${path}`, {
      method: 'PUT',
      ...options,
      headers: { ...authHeaders(), ...((options.headers as Record<string, string>) ?? {}) },
      body: JSON.stringify(body),
    })
    if (res.status === 401) handle401()
    return res
  },

  delete: async (path: string, options: RequestInit = {}): Promise<Response> => {
    const res = await fetch(`${API_BASE}/api${path}`, {
      method: 'DELETE',
      ...options,
      headers: { ...authHeaders(), ...((options.headers as Record<string, string>) ?? {}) },
    })
    if (res.status === 401) handle401()
    return res
  },
}
