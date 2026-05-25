import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { ILBPlayerPage } from '../ILBPlayerPage'
import { ilbApi } from '@/services/ilbApi'

vi.mock('@/services/api', () => ({ API_BASE: '' }))

vi.mock('@/services/ilbApi', () => ({
  ilbApi: {
    getPodcast: vi.fn(),
    startSession: vi.fn(),
    ask: vi.fn(),
    complete: vi.fn(),
    transcribe: vi.fn(),
  },
}))

const mockedIlb = ilbApi as unknown as Record<string, ReturnType<typeof vi.fn>>

const publishedConfig = {
  course_id: 7,
  script: 'Intro segment.',
  host_persona: null,
  avatar_id: null,
  voice_id: null,
  segments: ['Intro segment.'],
  segment_audio: null,
  segment_video: null,
  published: true,
}

function renderPlayer() {
  return render(
    <MemoryRouter initialEntries={['/learn/7/broadcast']}>
      <Routes>
        <Route path="/learn/:id/broadcast" element={<ILBPlayerPage />} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('ILBPlayerPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('shows a not-available message when no published broadcast', async () => {
    mockedIlb.getPodcast.mockRejectedValue(new Error('404'))
    renderPlayer()
    expect(await screen.findByText(/have a published broadcast/i)).toBeInTheDocument()
  })

  it('renders the Start control once a published broadcast loads', async () => {
    mockedIlb.getPodcast.mockResolvedValue(publishedConfig)
    renderPlayer()
    expect(await screen.findByText('Start broadcast')).toBeInTheDocument()
  })

  it('starts a session and answers a typed question (grounded)', async () => {
    mockedIlb.getPodcast.mockResolvedValue(publishedConfig)
    mockedIlb.startSession.mockResolvedValue({
      session: { id: 1, enrollment_id: 1, mode: 'interrupt', completion_status: 'in_progress', started_at: '', completed_at: null, final_score: null },
      live: { provider: 'stub', avatar_id: 'demo', livekit_url: '', token: '', session_id: 's1' },
    })
    mockedIlb.ask.mockResolvedValue({
      answer: 'Grounded answer.', source_refs: ['a passage'], confidence: 0.9,
      covered: true, escalated: false, disclaimer: 'refer to brief', answer_audio_url: null,
    })

    renderPlayer()
    await userEvent.click(await screen.findByText('Start broadcast'))

    const input = await screen.findByPlaceholderText(/type a question/i)
    await userEvent.type(input, 'What is X?')
    await userEvent.click(screen.getByText('Ask now'))

    expect(await screen.findByText('Grounded answer.')).toBeInTheDocument()
    expect(mockedIlb.startSession).toHaveBeenCalledWith(7, 'interrupt')
    expect(mockedIlb.ask).toHaveBeenCalledWith(1, 'What is X?', 'text')
  })

  it('shows an escalated answer flagged as such', async () => {
    mockedIlb.getPodcast.mockResolvedValue(publishedConfig)
    mockedIlb.startSession.mockResolvedValue({
      session: { id: 2, enrollment_id: 1, mode: 'interrupt', completion_status: 'in_progress', started_at: '', completed_at: null, final_score: null },
      live: { provider: 'stub', avatar_id: 'demo', livekit_url: '', token: '', session_id: 's2' },
    })
    mockedIlb.ask.mockResolvedValue({
      answer: 'Flagged for a human.', source_refs: [], confidence: 0.1,
      covered: false, escalated: true, disclaimer: 'refer to brief', answer_audio_url: null,
    })

    renderPlayer()
    await userEvent.click(await screen.findByText('Start broadcast'))
    await userEvent.type(await screen.findByPlaceholderText(/type a question/i), 'Off-topic?')
    await userEvent.click(screen.getByText('Ask now'))

    expect(await screen.findByText('Flagged for a human.')).toBeInTheDocument()
    expect(screen.getByText(/escalated/i)).toBeInTheDocument()
  })

  it('plays an avatar video and auto-advances on ended', async () => {
    window.HTMLMediaElement.prototype.play = vi.fn().mockResolvedValue(undefined)
    window.HTMLMediaElement.prototype.pause = vi.fn()
    mockedIlb.getPodcast.mockResolvedValue({
      ...publishedConfig,
      segments: ['Seg one.', 'Seg two.'],
      segment_audio: null,
      segment_video: ['/api/media/video/a.mp4', '/api/media/video/b.mp4'],
    })
    mockedIlb.startSession.mockResolvedValue({
      session: { id: 1, enrollment_id: 1, mode: 'interrupt', completion_status: 'in_progress', started_at: '', completed_at: null, final_score: null },
      live: { provider: 'stub', avatar_id: 'demo', livekit_url: '', token: '', session_id: 's1' },
    })
    renderPlayer()
    await userEvent.click(await screen.findByText('Start broadcast'))
    const video = document.querySelector('video') as HTMLVideoElement
    expect(video).toBeTruthy()
    expect(video.getAttribute('src')).toContain('/api/media/video/a.mp4')
    video.dispatchEvent(new Event('ended'))
    expect(await screen.findByText(/Segment 2\/2/)).toBeInTheDocument()
  })
})
