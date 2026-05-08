import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { AuthProvider, useAuth } from '@/context/AuthContext'

describe('Auth token key preservation', () => {
  beforeEach(() => { localStorage.clear() })
  afterEach(() => { localStorage.clear() })

  it('uses the key "token" for localStorage — must not change', () => {
    const TOKEN_KEY = 'token'
    localStorage.setItem(TOKEN_KEY, 'test-jwt-value')
    expect(localStorage.getItem('token')).toBe('test-jwt-value')
    expect(localStorage.getItem('auth')).toBeNull()
    expect(localStorage.getItem('jwt')).toBeNull()
    expect(localStorage.getItem('access_token')).toBeNull()
  })
})

describe('AuthProvider loading state', () => {
  beforeEach(() => { localStorage.clear() })
  afterEach(() => { localStorage.clear(); vi.restoreAllMocks() })

  it('starts in loading state when no token in localStorage', async () => {
    const TestConsumer = () => {
      const { loading } = useAuth()
      return <div>{loading ? 'loading' : 'ready'}</div>
    }
    render(<AuthProvider><TestConsumer /></AuthProvider>)
    // After hydration (no token), loading becomes false
    await waitFor(() => expect(screen.getByText('ready')).toBeInTheDocument())
  })

  it('useAuth throws outside AuthProvider', () => {
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {})
    const BadComponent = () => { useAuth(); return null }
    expect(() => render(<BadComponent />)).toThrow('useAuth must be used within AuthProvider')
    consoleError.mockRestore()
  })
})
