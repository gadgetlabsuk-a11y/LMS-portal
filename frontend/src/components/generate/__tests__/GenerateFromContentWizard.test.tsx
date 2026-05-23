import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { GenerateFromContentWizard } from '../GenerateFromContentWizard'
import { useGenerateStore } from '@/store/generateFromContentStore'

vi.mock('@/services/api', () => ({
  api: {
    postForm: vi.fn(),
  },
  API_BASE: '',
}))

describe('GenerateFromContentWizard', () => {
  beforeEach(() => {
    useGenerateStore.getState().reset()
    vi.clearAllMocks()
  })

  it('does not render when closed', () => {
    render(<GenerateFromContentWizard open={false} onClose={() => {}} onCreated={() => {}} />)
    expect(screen.queryByTestId('generate-content-wizard')).not.toBeInTheDocument()
  })

  it('renders the upload step when open', () => {
    render(<GenerateFromContentWizard open onClose={() => {}} onCreated={() => {}} />)
    expect(screen.getByTestId('generate-content-wizard')).toBeInTheDocument()
    expect(screen.getByTestId('content-file-input')).toBeInTheDocument()
  })

  it('rejects an unsupported file type with a message', async () => {
    render(<GenerateFromContentWizard open onClose={() => {}} onCreated={() => {}} />)
    const input = screen.getByTestId('content-file-input') as HTMLInputElement
    const bad = new File(['x'], 'notes.txt', { type: 'text/plain' })
    await userEvent.upload(input, bad)
    expect(screen.getByTestId('upload-error')).toBeInTheDocument()
    expect(useGenerateStore.getState().files).toHaveLength(0)
  })

  it('accepts a .pdf and advances to settings', async () => {
    render(<GenerateFromContentWizard open onClose={() => {}} onCreated={() => {}} />)
    const input = screen.getByTestId('content-file-input') as HTMLInputElement
    const good = new File(['x'], 'deck.pdf', { type: 'application/pdf' })
    await userEvent.upload(input, good)
    expect(useGenerateStore.getState().files).toHaveLength(1)
    await userEvent.click(screen.getByTestId('to-settings-btn'))
    expect(useGenerateStore.getState().step).toBe('settings')
  })
})
