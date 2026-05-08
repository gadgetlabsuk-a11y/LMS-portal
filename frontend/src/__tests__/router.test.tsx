import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { AuthProvider } from '../context/AuthContext'
import { ToastProvider } from '../context/ToastContext'
import App from '../App'

function renderWithProviders(initialPath: string) {
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <AuthProvider>
        <ToastProvider>
          <App />
        </ToastProvider>
      </AuthProvider>
    </MemoryRouter>
  )
}

describe('Route rendering', () => {
  it('renders login page at /login', () => {
    renderWithProviders('/login')
    // LoginPage renders an email input or a login form heading
    expect(screen.getByRole('button', { name: /log in|sign in|login/i })).toBeInTheDocument()
  })

  it('unauthenticated user on /admin is redirected to /login', () => {
    renderWithProviders('/admin')
    // ProtectedRoute redirects to /login when no token present
    expect(screen.getByRole('button', { name: /log in|sign in|login/i })).toBeInTheDocument()
  })

  it('unauthenticated user on /learn is redirected to /login', () => {
    renderWithProviders('/learn')
    // ProtectedRoute redirects to /login when no token present
    expect(screen.getByRole('button', { name: /log in|sign in|login/i })).toBeInTheDocument()
  })
})
