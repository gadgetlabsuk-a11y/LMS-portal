import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { MyTraining } from '../MyTraining'
import { api } from '@/services/api'

vi.mock('@/services/api', () => ({ api: { get: vi.fn() } }))
vi.mock('@/context/ToastContext', () => ({ useToast: () => ({ showToast: vi.fn() }) }))

const mockedApi = api as unknown as Record<string, ReturnType<typeof vi.fn>>
const ok = (data: unknown) => Promise.resolve({ ok: true, json: async () => data } as Response)

function renderPage() {
  return render(<MemoryRouter><MyTraining /></MemoryRouter>)
}

describe('MyTraining', () => {
  beforeEach(() => vi.clearAllMocks())

  it('lists required training with status', async () => {
    mockedApi.get.mockReturnValue(ok([
      { content_type: 'course', course_id: 3, broadcast_id: null, title: 'Fire Safety', is_podcast: false, due_date: '2020-01-01T00:00:00', status: 'overdue' },
      { content_type: 'broadcast', course_id: null, broadcast_id: 9, title: 'Policy Update', is_podcast: true, due_date: null, status: 'not_started' },
    ]))
    renderPage()
    expect(await screen.findByText('Fire Safety')).toBeInTheDocument()
    expect(screen.getByText('Policy Update')).toBeInTheDocument()
    expect(screen.getByText(/overdue/i)).toBeInTheDocument()
    expect(mockedApi.get).toHaveBeenCalledWith('/learn/required-training')
  })

  it('shows an all-clear message when nothing is required', async () => {
    mockedApi.get.mockReturnValue(ok([]))
    renderPage()
    expect(await screen.findByText(/no mandatory training/i)).toBeInTheDocument()
  })
})
