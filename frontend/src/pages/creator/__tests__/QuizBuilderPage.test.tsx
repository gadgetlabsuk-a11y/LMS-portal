import React from 'react'
import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { QuizBuilderPage } from '../QuizBuilderPage'

vi.mock('@/services/api', () => ({
  api: {
    get: vi.fn().mockImplementation((url: string) => {
      if (url.includes('/questions')) {
        return Promise.resolve({ json: () => Promise.resolve([]) })
      }
      return Promise.resolve({
        json: () => Promise.resolve({
          id: 1, title: 'Test Quiz', pass_rate: 80,
          attempts_allowed: 3, show_feedback: 'immediate', status: 'draft',
        })
      })
    }),
    put: vi.fn().mockResolvedValue({ json: () => Promise.resolve({}) }),
    post: vi.fn().mockResolvedValue({ json: () => Promise.resolve({}) }),
    delete: vi.fn().mockResolvedValue({}),
  },
}))

vi.mock('@/context/AuthContext', () => ({
  useAuth: () => ({ user: { role: 'creator' }, isAuthenticated: true }),
}))

vi.mock('@/hooks/useSSEStream', () => ({
  useSSEStream: () => ({
    text: '',
    isStreaming: false,
    startStream: vi.fn(),
    cancel: vi.fn(),
    reset: vi.fn(),
    setText: vi.fn(),
  }),
}))

vi.mock('@dnd-kit/sortable', () => ({
  SortableContext: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  useSortable: () => ({
    attributes: {},
    listeners: {},
    setNodeRef: vi.fn(),
    transform: null,
    transition: undefined,
    isDragging: false,
  }),
  arrayMove: vi.fn((arr: unknown[], from: number, to: number) => {
    const result = [...(arr as unknown[])]
    const [removed] = result.splice(from, 1)
    result.splice(to, 0, removed)
    return result
  }),
  sortableKeyboardCoordinates: vi.fn(),
  verticalListSortingStrategy: 'vertical',
}))

vi.mock('@dnd-kit/core', () => ({
  DndContext: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  PointerSensor: class {},
  KeyboardSensor: class {},
  useSensor: vi.fn(),
  useSensors: vi.fn(() => []),
}))

const renderPage = () =>
  render(
    <MemoryRouter initialEntries={['/creator/courses/1/quizzes/1']}>
      <Routes>
        <Route path="/creator/courses/:id/quizzes/:quizId" element={<QuizBuilderPage />} />
      </Routes>
    </MemoryRouter>
  )

describe('QuizBuilderPage', () => {
  beforeEach(() => vi.clearAllMocks())

  it('renders quiz settings form with pass_rate and attempts_allowed fields', async () => {
    renderPage()
    expect(await screen.findByTestId('quiz-settings')).toBeDefined()
    expect(screen.getByTestId('pass-rate-input')).toBeDefined()
    expect(screen.getByTestId('attempts-allowed-input')).toBeDefined()
    expect(screen.getByTestId('show-feedback-select')).toBeDefined()
  })

  it('renders question list section with Add Question button', async () => {
    renderPage()
    expect(await screen.findByTestId('questions-section')).toBeDefined()
    expect(screen.getByTestId('add-question-btn')).toBeDefined()
  })

  it('renders AI Generate Questions button', async () => {
    renderPage()
    expect(await screen.findByTestId('ai-generate-btn')).toBeDefined()
  })

  it('opens SideDrawer when AI Generate button is clicked', async () => {
    renderPage()
    await screen.findByTestId('ai-generate-btn')
    // SideDrawer not shown yet (isOpen=false returns null per SideDrawer contract)
    expect(screen.queryByTestId('side-drawer')).toBeNull()
    screen.getByTestId('ai-generate-btn').click()
    expect(await screen.findByTestId('side-drawer')).toBeDefined()
    expect(screen.getByTestId('generate-questions-btn')).toBeDefined()
  })
})
