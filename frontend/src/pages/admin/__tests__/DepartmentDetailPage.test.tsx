import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { DepartmentDetailPage } from '../DepartmentDetailPage'
import { api } from '@/services/api'

vi.mock('@/services/api', () => ({
  api: { get: vi.fn(), post: vi.fn(), put: vi.fn(), delete: vi.fn() },
}))
vi.mock('@/context/ToastContext', () => ({ useToast: () => ({ showToast: vi.fn() }) }))

const mockedApi = api as unknown as Record<string, ReturnType<typeof vi.fn>>
const ok = (data: unknown) => Promise.resolve({ ok: true, json: async () => data } as Response)

const detail = {
  id: 1, name: 'Operations', description: 'Ops', is_active: true,
  members: [{ id: 5, username: 'alice', email: 'alice@x.com', role: 'trainee' }],
  content: [{ id: 7, content_type: 'course', course_id: 3, broadcast_id: null, title: 'Fire Safety', is_podcast: false, mandatory: true, due_mode: 'fixed', due_date: '2026-06-30T00:00:00', due_days: null }],
}

function routeApi() {
  mockedApi.get.mockImplementation((path: string) => {
    if (path === '/departments/1') return ok(detail)
    if (path.startsWith('/departments/1/compliance')) return ok({ department_id: 1, items: [] })
    if (path.startsWith('/users')) return ok({ items: [{ id: 5, username: 'alice' }, { id: 6, username: 'bob' }] })
    if (path === '/courses') return ok([{ id: 3, title: 'Fire Safety' }, { id: 4, title: 'GDPR' }])
    if (path === '/ilb/broadcasts') return ok([{ id: 11, title: 'Company Brief', published: true }])
    return ok([])
  })
}

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/admin/departments/1']}>
      <Routes>
        <Route path="/admin/departments/:id" element={<DepartmentDetailPage />} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('DepartmentDetailPage', () => {
  beforeEach(() => { vi.clearAllMocks(); routeApi() })

  it('shows members and assigned content', async () => {
    renderPage()
    expect(await screen.findByText('alice')).toBeInTheDocument()
    expect(screen.getByText('Fire Safety')).toBeInTheDocument()
    expect(screen.getByText('Course')).toBeInTheDocument()
    expect(screen.getByText('Mandatory')).toBeInTheDocument()
  })

  it('assigns a standalone broadcast as mandatory with relative days', async () => {
    mockedApi.post.mockReturnValue(ok({ id: 8, content_type: 'broadcast', course_id: null, broadcast_id: 11, title: 'Company Brief', is_podcast: true, mandatory: true, due_mode: 'relative', due_date: null, due_days: 7 }))
    renderPage()
    await screen.findByText('Fire Safety')

    await userEvent.selectOptions(await screen.findByLabelText(/content to assign/i), 'broadcast:11')
    await userEvent.click(screen.getByLabelText(/mandatory/i))
    await userEvent.selectOptions(screen.getByLabelText(/deadline type/i), 'relative')
    await userEvent.type(screen.getByLabelText(/days to complete/i), '7')
    await userEvent.click(screen.getByText('Assign'))

    expect(mockedApi.post).toHaveBeenCalledWith(
      '/departments/1/content',
      expect.objectContaining({ broadcast_id: 11, mandatory: true, due_mode: 'relative', due_days: 7 }),
    )
  })
})
