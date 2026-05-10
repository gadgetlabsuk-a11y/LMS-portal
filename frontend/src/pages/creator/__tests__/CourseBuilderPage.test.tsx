import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { CourseBuilderPage } from '../CourseBuilderPage'

// Mock the api module so tests don't hit the network.
// Default: returns empty arrays (no modules).
// Override per-test via mockResolvedValueOnce when specific data is needed.
const mockGet = vi.fn()
vi.mock('@/services/api', () => ({
  api: {
    get: (...args: unknown[]) => mockGet(...args),
    post: vi.fn().mockResolvedValue({ json: async () => ({}) }),
  },
}))

// CourseBuilderPage integration tests
describe('CourseBuilderPage', () => {
  const renderPage = () =>
    render(
      <MemoryRouter initialEntries={['/creator/courses/1/builder']}>
        <Routes>
          <Route path="/creator/courses/:id/builder" element={<CourseBuilderPage />} />
          <Route path="/creator/courses/:id/modules/:moduleId" element={<div>Module Detail</div>} />
        </Routes>
      </MemoryRouter>
    )

  it('renders left-rail tree with module titles', async () => {
    mockGet.mockResolvedValue({ json: async () => [] })
    renderPage()
    // Wait for loading state to clear and tree rail to appear
    expect(await screen.findByTestId('course-tree-rail')).toBeInTheDocument()
  })

  it('renders status pill for each module', async () => {
    // Return one module from /courses/1/modules; empty arrays for videos and quizzes
    mockGet
      .mockResolvedValueOnce({
        json: async () => [{ id: 1, course_id: 1, order_index: 0, title: 'Intro', status: 'draft' }],
      })
      .mockResolvedValue({ json: async () => [] })
    renderPage()
    expect(await screen.findByTestId('module-status-pill')).toBeInTheDocument()
  })

  it('renders module overview list', async () => {
    mockGet.mockResolvedValue({ json: async () => [] })
    renderPage()
    expect(await screen.findByTestId('module-overview-list')).toBeInTheDocument()
  })

  it('renders preview button (PREVIEW-01)', async () => {
    mockGet.mockResolvedValue({ json: async () => [] })
    renderPage()
    expect(await screen.findByTestId('preview-mode-btn')).toBeInTheDocument()
  })
})
