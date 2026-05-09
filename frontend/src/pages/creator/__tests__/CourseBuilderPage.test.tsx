import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { CourseBuilderPage } from '../CourseBuilderPage'

// STUB — fails at import until CourseBuilderPage.tsx is created
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

  it('renders left-rail tree with module titles', () => {
    renderPage()
    // Will fail until implementation — tree rail not yet rendered
    expect(screen.getByTestId('course-tree-rail')).toBeInTheDocument()
  })

  it('renders status pill for each module', () => {
    renderPage()
    // Will fail until implementation
    expect(screen.getByTestId('module-status-pill')).toBeInTheDocument()
  })

  it('renders module overview list', () => {
    renderPage()
    expect(screen.getByTestId('module-overview-list')).toBeInTheDocument()
  })
})
