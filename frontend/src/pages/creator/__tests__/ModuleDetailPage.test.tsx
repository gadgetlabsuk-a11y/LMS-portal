import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { ModuleDetailPage } from '../ModuleDetailPage'

vi.mock('@/services/api', () => ({
  api: {
    get: vi.fn().mockResolvedValue({
      json: async () => ({
        id: 2,
        course_id: 1,
        title: 'Test Module',
        description: null,
        learning_objectives: null,
        estimated_duration_minutes: null,
        unlock_rule: 'immediate',
        status: 'draft',
      }),
    }),
    put: vi.fn().mockResolvedValue({ ok: true }),
  },
  API_BASE: 'http://localhost:8000',
}))

describe('ModuleDetailPage', () => {
  const renderPage = () =>
    render(
      <MemoryRouter initialEntries={['/creator/courses/1/modules/2']}>
        <Routes>
          <Route path="/creator/courses/:id/modules/:moduleId" element={<ModuleDetailPage />} />
        </Routes>
      </MemoryRouter>
    )

  it('renders form fields for module editing', () => {
    renderPage()
    expect(screen.getByTestId('module-title-input')).toBeInTheDocument()
    expect(screen.getByTestId('module-description-textarea')).toBeInTheDocument()
    expect(screen.getByTestId('module-duration-input')).toBeInTheDocument()
    expect(screen.getByTestId('module-unlock-rule-select')).toBeInTheDocument()
  })

  it('renders AI generate description button', () => {
    renderPage()
    expect(screen.getByTestId('ai-generate-description-btn')).toBeInTheDocument()
  })
})
