import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { GenerateFromContentWizard } from '../GenerateFromContentWizard'
import { useGenerateStore } from '@/store/generateFromContentStore'

vi.mock('@/services/api', () => ({
  api: { postForm: vi.fn() },
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

  it('rejects an unsupported file type with a message', () => {
    render(<GenerateFromContentWizard open onClose={() => {}} onCreated={() => {}} />)
    const input = screen.getByTestId('content-file-input') as HTMLInputElement
    const bad = new File(['x'], 'notes.txt', { type: 'text/plain' })
    fireEvent.change(input, { target: { files: [bad] } })
    expect(screen.getByTestId('upload-error')).toBeInTheDocument()
    expect(useGenerateStore.getState().files).toHaveLength(0)
  })

  it('accepts a .pdf and advances to settings', async () => {
    render(<GenerateFromContentWizard open onClose={() => {}} onCreated={() => {}} />)
    const input = screen.getByTestId('content-file-input') as HTMLInputElement
    const good = new File(['x'], 'deck.pdf', { type: 'application/pdf' })
    fireEvent.change(input, { target: { files: [good] } })
    expect(useGenerateStore.getState().files).toHaveLength(1)
    await userEvent.click(screen.getByTestId('to-settings-btn'))
    expect(useGenerateStore.getState().step).toBe('settings')
  })

  it('closing during fill resets the wizard store', () => {
    const onClose = vi.fn()
    useGenerateStore.setState({ step: 'filling', files: [new File(['x'], 'a.pdf')] })
    render(<GenerateFromContentWizard open onClose={onClose} onCreated={() => {}} />)
    fireEvent.click(screen.getByTestId('wizard-close-btn'))
    expect(onClose).toHaveBeenCalled()
    expect(useGenerateStore.getState().step).toBe('upload')
    expect(useGenerateStore.getState().files).toHaveLength(0)
  })
})
