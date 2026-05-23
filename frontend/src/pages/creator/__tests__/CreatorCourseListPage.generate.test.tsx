import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { CreatorCourseListPage } from '../CreatorCourseListPage'

vi.mock('@/context/AuthContext', () => ({ useAuth: () => ({ token: 't' }) }))
vi.mock('@/services/api', () => ({
  api: {
    get: vi.fn().mockResolvedValue({ ok: true, json: async () => [] }),
    post: vi.fn().mockResolvedValue({ ok: true, json: async () => ({ id: 1 }) }),
    postForm: vi.fn(),
  },
  API_BASE: '',
}))

describe('CreatorCourseListPage — generate from content', () => {
  beforeEach(() => vi.clearAllMocks())

  it('opens the generate-from-content wizard from the toolbar', async () => {
    render(<MemoryRouter><CreatorCourseListPage /></MemoryRouter>)
    await userEvent.click(screen.getByTestId('generate-from-content-btn'))
    expect(screen.getByTestId('generate-content-wizard')).toBeInTheDocument()
  })
})
