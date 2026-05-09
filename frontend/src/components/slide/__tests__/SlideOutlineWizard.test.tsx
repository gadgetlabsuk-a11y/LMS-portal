import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { SlideOutlineWizard } from '../SlideOutlineWizard'

vi.mock('@/services/api', () => ({
  api: {
    post: vi.fn().mockResolvedValue({ json: async () => ({ id: 99, title: 'New Slide', order_index: 0 }) }),
  },
  API_BASE: 'http://localhost:8000',
}))

vi.mock('@/context/AuthContext', () => ({
  useAuth: () => ({ token: 'test-token' }),
}))

describe('SlideOutlineWizard', () => {
  const defaultProps = {
    open: true,
    videoId: 10,
    anchorSlideId: 5,
    onClose: vi.fn(),
    onCommitted: vi.fn(),
  }

  it('SLIDE-12: renders wizard when open=true', () => {
    render(<SlideOutlineWizard {...defaultProps} />)
    expect(screen.getByTestId('outline-wizard')).toBeInTheDocument()
  })

  it('SLIDE-12: does not render when open=false', () => {
    render(<SlideOutlineWizard {...defaultProps} open={false} />)
    expect(screen.queryByTestId('outline-wizard')).not.toBeInTheDocument()
  })

  it('SLIDE-12: step 1 renders source prompt textarea', () => {
    render(<SlideOutlineWizard {...defaultProps} />)
    expect(screen.getByTestId('wizard-step-1')).toBeInTheDocument()
    expect(screen.getByTestId('wizard-source-prompt')).toBeInTheDocument()
  })

  it('SLIDE-12: next button advances to step 2 after entering prompt', async () => {
    render(<SlideOutlineWizard {...defaultProps} />)
    await userEvent.type(screen.getByTestId('wizard-source-prompt'), 'Python tutorial')
    await userEvent.click(screen.getByTestId('wizard-next-btn'))
    expect(screen.getByTestId('wizard-step-2')).toBeInTheDocument()
  })
})
