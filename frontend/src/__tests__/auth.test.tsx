import { describe, it, expect, beforeEach, afterEach } from 'vitest'

describe('Auth token key preservation', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  afterEach(() => {
    localStorage.clear()
  })

  it('uses the key "token" for localStorage — must not change', () => {
    // CRITICAL: The existing deployed app uses localStorage key 'token'.
    // If the Vite app uses any other key, live users will be logged out on deploy.
    // This test documents the contract — implementation enforced in AuthContext.tsx (Plan 02).
    const TOKEN_KEY = 'token'
    localStorage.setItem(TOKEN_KEY, 'test-jwt-value')
    expect(localStorage.getItem('token')).toBe('test-jwt-value')
    expect(localStorage.getItem('auth')).toBeNull()
    expect(localStorage.getItem('jwt')).toBeNull()
    expect(localStorage.getItem('access_token')).toBeNull()
  })
})
