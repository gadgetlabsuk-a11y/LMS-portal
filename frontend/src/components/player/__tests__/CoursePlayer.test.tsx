import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { CoursePlayer } from '../CoursePlayer'
import { coursePlayerApi } from '@/services/coursePlayerApi'

vi.mock('@/services/api', () => ({ API_BASE: '' }))
vi.mock('@/services/coursePlayerApi', () => ({ coursePlayerApi: { getLearnerPlayer: vi.fn(), getPreviewTree: vi.fn(), postProgress: vi.fn().mockResolvedValue({ progress: 100, completed: true }) } }))
const mocked = coursePlayerApi as unknown as Record<string, ReturnType<typeof vi.fn>>

const course = { id: 1, title: 'C', progress: 0, completed: false, modules: [
  { id: 1, title: 'M', order_index: 0, videos: [
    { id: 1, title: 'V', order_index: 0, quizzes: [], slides: [
      { id: 10, order_index: 0, narration_audio_url: null, duration_seconds: null, blocks: [{ id: 1, type: 'heading', content: { html: '<h2>Slide A</h2>' }, order_index: 0 }] },
      { id: 11, order_index: 1, narration_audio_url: null, duration_seconds: null, blocks: [{ id: 2, type: 'text', content: { html: '<p>Slide B</p>' }, order_index: 0 }] },
    ] },
  ] },
] }

// A course where a quiz sits between two slides, and the quiz has no attempts left.
const exhaustedQuiz = { id: 7, title: 'Gate', pass_rate: 80, attempts_allowed: 3, attempts_remaining: 0, attempts_used: 3, passed: false, last_score: 40,
  questions: [{ id: 70, type: 'mcq_single', prompt: 'q?', options: ['a', 'b'], points: 1, order_index: 0 }] }
const courseWithQuiz = { id: 2, title: 'CQ', progress: 0, completed: false, modules: [
  { id: 1, title: 'M', order_index: 0, videos: [
    { id: 1, title: 'V', order_index: 0, quizzes: [exhaustedQuiz], slides: [
      { id: 20, order_index: 0, narration_audio_url: null, duration_seconds: null, blocks: [{ id: 1, type: 'heading', content: { html: '<h2>Before Quiz</h2>' }, order_index: 0 }] },
    ] },
    { id: 2, title: 'V2', order_index: 1, quizzes: [], slides: [
      { id: 21, order_index: 0, narration_audio_url: null, duration_seconds: null, blocks: [{ id: 2, type: 'text', content: { html: '<p>After Quiz</p>' }, order_index: 0 }] },
    ] },
  ] },
] }

describe('CoursePlayer', () => {
  beforeEach(() => vi.clearAllMocks())
  it('renders first slide and advances on Next', async () => {
    mocked.getLearnerPlayer.mockResolvedValue(course)
    render(<CoursePlayer courseId={1} mode="learner" />)
    expect(await screen.findByText('Slide A')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: /next/i }))
    expect(await screen.findByText('Slide B')).toBeInTheDocument()
  })
  it('preview mode never posts progress', async () => {
    mocked.getPreviewTree.mockResolvedValue(course)
    render(<CoursePlayer courseId={1} mode="preview" />)
    await screen.findByText('Slide A')
    await userEvent.click(screen.getByRole('button', { name: /next/i }))
    await screen.findByText('Slide B')
    expect(mocked.postProgress).not.toHaveBeenCalled()
  })
  it('learner is NOT trapped on a quiz whose attempts are exhausted', async () => {
    mocked.getLearnerPlayer.mockResolvedValue(courseWithQuiz)
    render(<CoursePlayer courseId={2} mode="learner" />)
    await screen.findByText('Before Quiz')
    // Advance to the quiz step.
    await userEvent.click(screen.getByRole('button', { name: /next/i }))
    await screen.findByText('Gate')
    // Next must be enabled (not gated) because attempts_remaining === 0.
    const next = screen.getByRole('button', { name: /next/i })
    expect(next).not.toBeDisabled()
    await userEvent.click(next)
    expect(await screen.findByText('After Quiz')).toBeInTheDocument()
  })
  it('preview mode lets Next through a quiz step', async () => {
    mocked.getPreviewTree.mockResolvedValue(courseWithQuiz)
    render(<CoursePlayer courseId={2} mode="preview" />)
    await screen.findByText('Before Quiz')
    await userEvent.click(screen.getByRole('button', { name: /next/i }))
    await screen.findByText('Gate')
    const next = screen.getByRole('button', { name: /next/i })
    expect(next).not.toBeDisabled()
    await userEvent.click(next)
    expect(await screen.findByText('After Quiz')).toBeInTheDocument()
  })
})
