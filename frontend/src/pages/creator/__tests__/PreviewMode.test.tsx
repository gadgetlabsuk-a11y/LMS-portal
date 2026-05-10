import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { CoursePreviewPage } from '../CoursePreviewPage'

vi.mock('@/services/api', () => ({
  API_BASE: 'http://localhost:8000',
}))

vi.mock('@/context/AuthContext', () => ({
  useAuth: () => ({ user: { id: 1, role: 'creator' }, isAuthenticated: true }),
}))

function renderPreview(returnTo?: string) {
  const url = returnTo
    ? `/creator/courses/1/preview?returnTo=${encodeURIComponent(returnTo)}`
    : '/creator/courses/1/preview'
  return render(
    <MemoryRouter initialEntries={[url]}>
      <Routes>
        <Route path="/creator/courses/:id/preview" element={<CoursePreviewPage />} />
        <Route path="/creator/courses/:id/builder" element={<div>Builder</div>} />
        <Route path="/custom/return" element={<div>Custom Return</div>} />
      </Routes>
    </MemoryRouter>
  )
}

describe('CoursePreviewPage', () => {
  it('renders draft watermark banner (PREVIEW-01)', () => {
    renderPreview()
    const watermark = screen.getByTestId('preview-watermark')
    expect(watermark).toBeInTheDocument()
    expect(watermark).toHaveTextContent('Preview Mode — Draft')
  })

  it('exit preview button navigates to returnTo (PREVIEW-03)', async () => {
    renderPreview('/custom/return')
    const exitBtn = screen.getByTestId('exit-preview-btn')
    expect(exitBtn).toBeInTheDocument()
    exitBtn.click()
    expect(await screen.findByText('Custom Return')).toBeInTheDocument()
  })

  it('renders learner player iframe for full block/quiz rendering (PREVIEW-02)', () => {
    renderPreview()
    const iframe = screen.getByTitle('Course Preview')
    expect(iframe).toBeInTheDocument()
    expect((iframe as HTMLIFrameElement).src).toContain('/api/courses/1/player')
  })
})
