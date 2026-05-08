import { createContext, useContext, useState, useEffect, useCallback } from 'react'
import { api } from '@/services/api'

// CRITICAL: key must remain 'token' — matches the existing deployed app.
// Changing this key would log out all active users on deploy.
const TOKEN_KEY = 'token'

export interface User {
  id: number
  username: string
  email: string
  role: 'admin' | 'creator' | 'trainee'
  is_active: boolean
}

interface LoginResult {
  success: boolean
  requiresMfa?: boolean
  token?: string
  error?: string
}

interface AuthContextValue {
  auth: string | null
  user: User | null
  loading: boolean
  login: (username: string, password: string, mfaCode?: string) => Promise<LoginResult>
  logout: () => void
}

const AuthContext = createContext<AuthContextValue | null>(null)

const fetchUserProfile = async (token: string): Promise<User | null> => {
  try {
    const res = await fetch(
      (import.meta.env.PROD ? '/lms' : '') + '/api/auth/me',
      { headers: { Authorization: `Bearer ${token}` } }
    )
    if (res.ok) return res.json()
  } catch (err) {
    console.error('Failed to fetch user profile:', err)
  }
  return null
}

export const AuthProvider = ({ children }: { children: React.ReactNode }) => {
  const [auth, setAuth] = useState<string | null>(null)
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const token = localStorage.getItem(TOKEN_KEY)
    if (token) {
      setAuth(token)
      fetchUserProfile(token)
        .then(u => setUser(u))
        .finally(() => setLoading(false))
    } else {
      setLoading(false)
    }
  }, [])

  const login = useCallback(async (
    username: string,
    password: string,
    mfaCode?: string
  ): Promise<LoginResult> => {
    try {
      const body: Record<string, string> = { username, password }
      if (mfaCode) body.mfa_code = mfaCode

      const res = await api.post('/auth/login', body)
      const data = await res.json()

      if (res.status === 200 && data.access_token) {
        localStorage.setItem(TOKEN_KEY, data.access_token)
        setAuth(data.access_token)
        const profile = await fetchUserProfile(data.access_token)
        setUser(profile)
        return { success: true, token: data.access_token }
      }

      if (res.status === 202 && data.mfa_required) {
        return { success: false, requiresMfa: true }
      }

      return { success: false, error: data.detail ?? 'Login failed' }
    } catch (err) {
      return { success: false, error: 'Network error' }
    }
  }, [])

  const logout = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY)
    setAuth(null)
    setUser(null)
  }, [])

  return (
    <AuthContext.Provider value={{ auth, user, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = (): AuthContextValue => {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
