import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { DepartmentsPage } from '../DepartmentsPage'
import { api } from '@/services/api'

vi.mock('@/services/api', () => ({
  api: { get: vi.fn(), post: vi.fn(), put: vi.fn(), delete: vi.fn() },
}))
vi.mock('@/context/ToastContext', () => ({ useToast: () => ({ showToast: vi.fn() }) }))

const mockedApi = api as unknown as Record<string, ReturnType<typeof vi.fn>>
const ok = (data: unknown) => Promise.resolve({ ok: true, json: async () => data } as Response)

function renderPage() {
  return render(<MemoryRouter><DepartmentsPage /></MemoryRouter>)
}

describe('DepartmentsPage', () => {
  beforeEach(() => vi.clearAllMocks())

  it('lists departments from the API', async () => {
    mockedApi.get.mockReturnValue(ok([
      { id: 1, name: 'Operations', description: 'Ops', is_active: true, member_count: 3, content_count: 2 },
    ]))
    renderPage()
    expect(await screen.findByText('Operations')).toBeInTheDocument()
    expect(screen.getByText(/3 members/)).toBeInTheDocument()
  })

  it('creates a department', async () => {
    mockedApi.get.mockReturnValue(ok([]))
    mockedApi.post.mockReturnValue(ok({ id: 9, name: 'Sales', description: null, is_active: true, member_count: 0, content_count: 0 }))
    renderPage()
    await userEvent.click(await screen.findByText('+ New Department'))
    await userEvent.type(screen.getByPlaceholderText(/e.g. Operations/i), 'Sales')
    await userEvent.click(screen.getByText('Create'))
    expect(mockedApi.post).toHaveBeenCalledWith('/departments', { name: 'Sales', description: '' })
  })
})
