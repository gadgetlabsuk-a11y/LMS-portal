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
  it('submits and shows pass result', async () => {
    mocked.submitAttempt.mockResolvedValue({ score: 100, passed: true, attempts_remaining: 2, feedback: null })
    render(<QuizRunner quiz={quiz} onPassed={vi.fn()} />)
    await userEvent.click(screen.getByLabelText('4'))
    await userEvent.click(screen.getByText('Submit'))
    expect(await screen.findByText(/Passed/i)).toBeInTheDocument()
    expect(mocked.submitAttempt).toHaveBeenCalledWith(1, { '9': 1 })
  })
})
