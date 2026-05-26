import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { CoursePreviewPage } from '../CoursePreviewPage'
import { coursePlayerApi } from '@/services/coursePlayerApi'

vi.mock('@/services/api', () => ({
  API_BASE: 'http://localhost:8000',
}))

vi.mock('@/context/AuthContext', () => ({
  useAuth: () => ({ user: { id: 1, role: 'creator' }, isAuthenticated: true }),
}))

// CoursePreviewPage now mounts the React CoursePlayer (mode="preview"),
// which loads its data via coursePlayerApi.getPreviewTree. Mock it so the
// player mounts without hitting the network.
vi.mock('@/services/coursePlayerApi', () => ({
  coursePlayerApi: {
    getPreviewTree: vi.fn(),
    getLearnerPlayer: vi.fn(),
    postProgress: vi.fn(),
    getQuiz: vi.fn(),
    submitAttempt: vi.fn(),
  },
}))
const mocked = coursePlayerApi as unknown as Record<string, ReturnType<typeof vi.fn>>

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
  beforeEach(() => {
    vi.clearAllMocks()
    mocked.getPreviewTree.mockResolvedValue({
      id: 1,
      title: 'C',
      progress: 0,
      completed: false,
      modules: [],
    })
  })

  it('renders draft watermark banner (PREVIEW-01)', async () => {
    renderPreview()
    const watermark = await screen.findByTestId('preview-watermark')
    expect(watermark).toBeInTheDocument()
    expect(watermark).toHaveTextContent('Preview Mode — Draft')
  })

  it('exit preview button navigates to returnTo (PREVIEW-03)', async () => {
    renderPreview('/custom/return')
    const exitBtn = await screen.findByTestId('exit-preview-btn')
    expect(exitBtn).toBeInTheDocument()
    exitBtn.click()
    expect(await screen.findByText('Custom Return')).toBeInTheDocument()
  })

  it('renders the React CoursePlayer in preview mode (PREVIEW-02)', async () => {
    renderPreview()
    // The React player replaces the old backend iframe. In preview mode it must
    // pull the read-only preview tree, never the learner player endpoint.
    await screen.findByTestId('preview-watermark')
    expect(mocked.getPreviewTree).toHaveBeenCalledWith(1)
    expect(mocked.getLearnerPlayer).not.toHaveBeenCalled()
  })
})
