import { describe, it, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { SlideEditorPage } from '../SlideEditorPage'
import { useSlideEditorStore } from '@/store/slideEditorStore'

vi.mock('@/services/api', () => ({
  api: {
    get: vi.fn().mockResolvedValue({ json: async () => [] }),
    post: vi.fn().mockResolvedValue({ json: async () => ({}) }),
    put: vi.fn().mockResolvedValue({ ok: true }),
    delete: vi.fn().mockResolvedValue({ ok: true }),
  },
  API_BASE: '',
}))

/**
 * Regression: the editor must render under the app's real router, which is a
 * plain <BrowserRouter> (non-data router). It previously used useBlocker, which
 * only works inside a data router (createBrowserRouter/RouterProvider) and threw
 * under <BrowserRouter>, white-screening the editor in production. The original
 * editor test used createMemoryRouter (a data router) and so never caught it.
 */
describe('SlideEditorPage under a non-data router (BrowserRouter-style)', () => {
  beforeEach(() => {
    useSlideEditorStore.setState({ blocks: [], isDirty: false })
  })

  it('renders without throwing', () => {
    render(
      <MemoryRouter initialEntries={['/creator/courses/1/videos/1/slides/1/editor']}>
        <Routes>
          <Route
            path="/creator/courses/:id/videos/:videoId/slides/:slideId/editor"
            element={<SlideEditorPage />}
          />
        </Routes>
      </MemoryRouter>,
    )
    expect(screen.getByTestId('slide-editor-page')).toBeTruthy()
  })
})
