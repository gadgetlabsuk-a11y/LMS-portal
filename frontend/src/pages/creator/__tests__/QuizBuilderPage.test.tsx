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
})
