import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import App from '../App'

describe('Route stubs', () => {
  it('renders login route', () => {
    render(
      <MemoryRouter initialEntries={['/login']}>
        <App />
      </MemoryRouter>
    )
    expect(screen.getByText(/LoginPage/i)).toBeInTheDocument()
  })

  it('renders admin route', () => {
    render(
      <MemoryRouter initialEntries={['/admin']}>
        <App />
      </MemoryRouter>
    )
    expect(screen.getByText(/AdminDashboard/i)).toBeInTheDocument()
  })

  it('renders learn route', () => {
    render(
      <MemoryRouter initialEntries={['/learn']}>
        <App />
      </MemoryRouter>
    )
    expect(screen.getByText(/LearnerCatalogue/i)).toBeInTheDocument()
  })
})
