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
})
