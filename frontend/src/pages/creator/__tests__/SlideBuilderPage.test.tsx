import { describe, it, expect, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { SlideBuilderPage } from '../SlideBuilderPage'

const mockSlides = [
  { id: 1, video_id: 10, title: 'Intro Slide', narration_script: null, order_index: 0 },
  { id: 2, video_id: 10, title: 'Content Slide', narration_script: 'Hello world', order_index: 1 },
]

vi.mock('@/context/AuthContext', () => ({
  useAuth: () => ({ token: 'test-token' }),
}))

vi.mock('@/services/api', () => ({
  api: {
    get: vi.fn().mockResolvedValue({ json: async () => mockSlides }),
    post: vi.fn().mockResolvedValue({
      json: async () => ({ id: 3, video_id: 10, title: 'Slide 3', narration_script: null, order_index: 2 }),
    }),
    put: vi.fn().mockResolvedValue({ ok: true }),
    delete: vi.fn().mockResolvedValue({ ok: true }),
  },
  API_BASE: 'http://localhost:8000',
}))

describe('SlideBuilderPage', () => {
  const renderPage = () =>
    render(
      <MemoryRouter initialEntries={['/creator/courses/1/videos/10/slides']}>
        <Routes>
          <Route
            path="/creator/courses/:id/videos/:videoId/slides"
            element={<SlideBuilderPage />}
          />
        </Routes>
      </MemoryRouter>
    )

  it('SLIDE-01: renders slide builder page with slide thumbnails', async () => {
    renderPage()
    expect(screen.getByTestId('slide-builder-page')).toBeInTheDocument()
    await screen.findByTestId('slide-thumb-1')
    expect(screen.getByTestId('slide-thumb-2')).toBeInTheDocument()
  })

  it('SLIDE-02: add slide button calls POST /videos/{id}/slides', async () => {
    const { api } = await import('@/services/api')
    renderPage()
    await screen.findByTestId('slide-thumb-1')
    await userEvent.click(screen.getByTestId('add-slide-btn'))
    expect(api.post).toHaveBeenCalledWith(
      expect.stringContaining('/videos/10/slides'),
      expect.objectContaining({ title: expect.any(String) })
    )
  })

  it('SLIDE-03: bulk narration button is enabled and wired', async () => {
    renderPage()
    await screen.findByTestId('slide-thumb-1')
    const btn = screen.getByTestId('bulk-narration-btn')
    expect(btn).not.toBeDisabled()
  })
})
