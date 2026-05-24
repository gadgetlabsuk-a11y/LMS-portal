import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { RemindersPage } from '../RemindersPage'
import { api } from '@/services/api'

vi.mock('@/services/api', () => ({ api: { get: vi.fn() } }))
vi.mock('@/context/ToastContext', () => ({ useToast: () => ({ showToast: vi.fn() }) }))

const mockedApi = api as unknown as Record<string, ReturnType<typeof vi.fn>>
const ok = (data: unknown) => Promise.resolve({ ok: true, json: async () => data } as Response)

function renderPage() {
  return render(<MemoryRouter><RemindersPage /></MemoryRouter>)
}

describe('RemindersPage', () => {
  beforeEach(() => vi.clearAllMocks())

  it('lists people who are overdue / due soon', async () => {
    mockedApi.get.mockReturnValue(ok([
      { user_id: 5, username: 'alice', email: 'alice@x.com', content_type: 'course', course_id: 3, broadcast_id: null, title: 'Fire Safety', due_date: '2020-01-01T00:00:00', status: 'overdue' },
      { user_id: 6, username: 'bob', email: 'bob@x.com', content_type: 'broadcast', course_id: null, broadcast_id: 9, title: 'Policy Update', due_date: '2026-12-31T00:00:00', status: 'not_started' },
    ]))
    renderPage()
    expect(await screen.findByText('alice')).toBeInTheDocument()
    expect(screen.getByText('Fire Safety')).toBeInTheDocument()
    expect(screen.getByText('bob')).toBeInTheDocument()
    expect(screen.getByText(/overdue/i)).toBeInTheDocument()
    expect(mockedApi.get).toHaveBeenCalledWith(expect.stringContaining('/departments/reminders'))
  })

  it('shows an all-clear message when nobody is behind', async () => {
    mockedApi.get.mockReturnValue(ok([]))
    renderPage()
    expect(await screen.findByText(/no one is overdue/i)).toBeInTheDocument()
  })
})
