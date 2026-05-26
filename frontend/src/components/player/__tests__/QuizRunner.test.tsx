import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QuizRunner } from '../QuizRunner'
import { coursePlayerApi } from '@/services/coursePlayerApi'

vi.mock('@/services/coursePlayerApi', () => ({ coursePlayerApi: { submitAttempt: vi.fn() } }))
const mocked = coursePlayerApi as unknown as Record<string, ReturnType<typeof vi.fn>>

const quiz = { id: 1, title: 'Q', pass_rate: 50, attempts_allowed: 3, attempts_remaining: 3, attempts_used: 0, passed: false, last_score: null,
  questions: [{ id: 9, type: 'mcq_single', prompt: '2+2?', options: ['3', '4'], points: 1, order_index: 0 }] }

describe('QuizRunner', () => {
  it('submits and shows pass result, calls onResolved(true)', async () => {
    mocked.submitAttempt.mockResolvedValue({ score: 100, passed: true, attempts_remaining: 2, feedback: null })
    const onResolved = vi.fn()
    render(<QuizRunner quiz={quiz} mode="learner" onResolved={onResolved} />)
    await userEvent.click(screen.getByLabelText('4'))
    await userEvent.click(screen.getByText('Submit'))
    expect(await screen.findByText(/Passed/i)).toBeInTheDocument()
    expect(mocked.submitAttempt).toHaveBeenCalledWith(1, { '9': 1 })
    expect(onResolved).toHaveBeenCalledWith(true)
  })

  it('calls onResolved(false) when a failing submit exhausts attempts', async () => {
    mocked.submitAttempt.mockResolvedValue({ score: 0, passed: false, attempts_remaining: 0, feedback: null })
    const onResolved = vi.fn()
    render(<QuizRunner quiz={quiz} mode="learner" onResolved={onResolved} />)
    await userEvent.click(screen.getByLabelText('3'))
    await userEvent.click(screen.getByText('Submit'))
    expect(await screen.findByText(/No attempts remaining/i)).toBeInTheDocument()
    expect(onResolved).toHaveBeenCalledWith(false)
  })

  it('does NOT call onResolved on a failing submit while retries remain', async () => {
    mocked.submitAttempt.mockResolvedValue({ score: 0, passed: false, attempts_remaining: 1, feedback: null })
    const onResolved = vi.fn()
    render(<QuizRunner quiz={quiz} mode="learner" onResolved={onResolved} />)
    await userEvent.click(screen.getByLabelText('3'))
    await userEvent.click(screen.getByText('Submit'))
    expect(await screen.findByText(/Retake/i)).toBeInTheDocument()
    expect(onResolved).not.toHaveBeenCalled()
  })

  it('preview mode renders questions but no Submit and never submits', async () => {
    mocked.submitAttempt.mockClear()
    render(<QuizRunner quiz={quiz} mode="preview" onResolved={vi.fn()} />)
    expect(screen.getByText('2+2?')).toBeInTheDocument()
    expect(screen.queryByText('Submit')).not.toBeInTheDocument()
    expect(screen.getByText(/Preview/i)).toBeInTheDocument()
    expect(mocked.submitAttempt).not.toHaveBeenCalled()
  })

  it('renders a text input for short_answer and submits the typed string', async () => {
    mocked.submitAttempt.mockResolvedValue({ score: 100, passed: true, attempts_remaining: 2, feedback: null })
    const saQuiz = { ...quiz, questions: [{ id: 12, type: 'short_answer', prompt: 'Capital of France?', options: null, points: 1, order_index: 0 }] }
    render(<QuizRunner quiz={saQuiz} mode="learner" onResolved={vi.fn()} />)
    const input = screen.getByLabelText('Capital of France?')
    await userEvent.type(input, 'Paris')
    await userEvent.click(screen.getByText('Submit'))
    expect(mocked.submitAttempt).toHaveBeenCalledWith(1, { '12': 'Paris' })
  })
})
