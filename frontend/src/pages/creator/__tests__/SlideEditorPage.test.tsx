import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { createMemoryRouter, RouterProvider } from 'react-router-dom'
import { SlideEditorPage } from '../SlideEditorPage'
import { useSlideEditorStore } from '@/store/slideEditorStore'

vi.mock('@/services/api', () => ({
  api: {
    get: vi.fn().mockResolvedValue({ json: async () => [] }),
    post: vi.fn().mockResolvedValue({
      json: async () => ({
        id: 99, type: 'text', content: {},
        grid_position: { x: 0, y: 0, w: 8, h: 4 }, order_index: 0,
      }),
    }),
    put: vi.fn().mockResolvedValue({ ok: true }),
    delete: vi.fn().mockResolvedValue({ ok: true }),
  },
  API_BASE: 'http://localhost:8000',
}))

// Mock react-grid-layout — jsdom cannot handle CSS transforms
vi.mock('react-grid-layout', () => ({
  default: ({ children }: { children: React.ReactNode }) => <div data-testid="grid-layout">{children}</div>,
}))

describe('SlideEditorPage', () => {
  beforeEach(() => {
    useSlideEditorStore.setState({ blocks: [], isDirty: false })
  })

  const renderPage = () => {
    const router = createMemoryRouter(
      [
        {
          path: '/creator/courses/:id/videos/:videoId/slides/:slideId/editor',
          element: <SlideEditorPage />,
        },
      ],
      {
        initialEntries: ['/creator/courses/1/videos/10/slides/5/editor'],
      }
    )
    return render(<RouterProvider router={router} />)
  }

  it('SLIDE-04: renders slide editor page', () => {
    renderPage()
    expect(screen.getByTestId('slide-editor-page')).toBeInTheDocument()
  })

  it('SLIDE-07: renders undo and redo buttons', () => {
    renderPage()
    expect(screen.getByTestId('undo-btn')).toBeInTheDocument()
    expect(screen.getByTestId('redo-btn')).toBeInTheDocument()
  })

  it('SLIDE-05: palette renders block type buttons', () => {
    renderPage()
    expect(screen.getByTestId('palette-text-btn')).toBeInTheDocument()
    expect(screen.getByTestId('palette-heading-btn')).toBeInTheDocument()
    expect(screen.getByTestId('palette-image-btn')).toBeInTheDocument()
  })
})
