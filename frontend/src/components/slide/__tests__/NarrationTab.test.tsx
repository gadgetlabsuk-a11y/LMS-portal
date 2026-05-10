import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { NarrationTab } from '../NarrationTab'
import { useSlideEditorStore } from '@/store/slideEditorStore'

vi.mock('@/services/api', () => ({
  api: {
    get: vi.fn().mockResolvedValue({ json: async () => ({}) }),
    put: vi.fn().mockResolvedValue({ ok: true }),
    post: vi.fn().mockResolvedValue({ json: async () => ({ audio_url: '/uploads/audio/slide_5.mp3' }) }),
  },
  API_BASE: 'http://localhost:8000',
}))

vi.mock('@/context/AuthContext', () => ({
  useAuth: () => ({ token: 'test-token' }),
}))

describe('NarrationTab', () => {
  beforeEach(() => {
    useSlideEditorStore.setState({ narrationScript: '', isDirty: false })
  })

  it('SLIDE-10: renders narration script textarea', () => {
    render(<NarrationTab slideId={5} courseId={1} />)
    expect(screen.getByTestId('narration-script-textarea')).toBeInTheDocument()
  })

  it('SLIDE-10: textarea value reflects Zustand narrationScript state', () => {
    useSlideEditorStore.setState({ narrationScript: 'Hello world' })
    render(<NarrationTab slideId={5} courseId={1} />)
    expect(screen.getByTestId('narration-script-textarea')).toHaveValue('Hello world')
  })

  it('SLIDE-11: generate narration button is present', () => {
    render(<NarrationTab slideId={5} courseId={1} />)
    expect(screen.getByTestId('generate-narration-btn')).toBeInTheDocument()
  })

  it('TTS-01: renders generate-audio-btn button', () => {
    useSlideEditorStore.setState({ narrationScript: 'Hello world' })
    render(<NarrationTab slideId={5} courseId={1} />)
    expect(screen.getByTestId('generate-audio-btn')).toBeInTheDocument()
  })

  it('TTS-01: narration-audio-player appears after clicking generate-audio-btn', async () => {
    useSlideEditorStore.setState({ narrationScript: 'Hello world' })
    render(<NarrationTab slideId={5} courseId={1} />)
    await userEvent.click(screen.getByTestId('generate-audio-btn'))
    expect(await screen.findByTestId('narration-audio-player')).toBeInTheDocument()
  })
})
