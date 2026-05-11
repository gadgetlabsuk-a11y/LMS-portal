import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { PreflightModal } from '../PreflightModal'

const mockGet = vi.fn()
const mockPost = vi.fn()

vi.mock('@/services/api', () => ({
  api: {
    get: (...args: unknown[]) => mockGet(...args),
    post: (...args: unknown[]) => mockPost(...args),
  },
}))

const renderModal = (props = {}) =>
  render(
    <MemoryRouter>
      <PreflightModal
        open={true}
        courseId={1}
        onClose={vi.fn()}
        onPublished={vi.fn()}
        {...props}
      />
    </MemoryRouter>
  )

describe('PreflightModal', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('fetches preflight on open and renders result rows (PUBLISH-02)', async () => {
    mockGet.mockResolvedValue({
      json: async () => ({
        can_publish: true,
        results: [
          { rule: 'has_title', status: 'pass', message: 'Title set', fix_url: null },
          { rule: 'has_modules', status: 'warn', message: 'Add more modules', fix_url: '/modules' },
          { rule: 'has_content', status: 'fail', message: 'No content', fix_url: '/content' },
        ],
      }),
    })
    renderModal()
    expect(await screen.findByTestId('preflight-result-has_title')).toBeInTheDocument()
    expect(await screen.findByTestId('preflight-result-has_modules')).toBeInTheDocument()
    expect(await screen.findByTestId('preflight-result-has_content')).toBeInTheDocument()
  })

  it('shows Fix deep-link for failed results (PUBLISH-03, PUBLISH-04)', async () => {
    mockGet.mockResolvedValue({
      json: async () => ({
        can_publish: false,
        results: [
          { rule: 'has_content', status: 'fail', message: 'No content', fix_url: '/content' },
        ],
      }),
    })
    renderModal()
    expect(await screen.findByTestId('preflight-fix-has_content')).toBeInTheDocument()
  })

  it('Publish button disabled when can_publish=false', async () => {
    mockGet.mockResolvedValue({
      json: async () => ({
        can_publish: false,
        results: [
          { rule: 'has_content', status: 'fail', message: 'No content', fix_url: null },
        ],
      }),
    })
    renderModal()
    const publishBtn = await screen.findByTestId('preflight-publish-btn')
    expect(publishBtn).toBeDisabled()
  })

  it('Publish button enabled when can_publish=true', async () => {
    mockGet.mockResolvedValue({
      json: async () => ({
        can_publish: true,
        results: [
          { rule: 'has_title', status: 'pass', message: 'Title set', fix_url: null },
        ],
      }),
    })
    renderModal()
    const publishBtn = await screen.findByTestId('preflight-publish-btn')
    expect(publishBtn).not.toBeDisabled()
  })

  it('confirm-publish-btn calls POST /publish (PUBLISH-05, PUBLISH-06)', async () => {
    // First GET: initial load, second GET: re-fetch on Publish click
    mockGet.mockResolvedValue({
      json: async () => ({
        can_publish: true,
        results: [{ rule: 'has_title', status: 'pass', message: 'Title set', fix_url: null }],
      }),
    })
    mockPost.mockResolvedValue({ json: async () => ({}) })

    const onPublished = vi.fn()
    renderModal({ onPublished })

    const publishBtn = await screen.findByTestId('preflight-publish-btn')
    publishBtn.click()

    const confirmBtn = await screen.findByTestId('confirm-publish-btn')
    confirmBtn.click()

    await waitFor(() => {
      expect(mockPost).toHaveBeenCalledWith('/courses/1/publish', {})
      expect(onPublished).toHaveBeenCalled()
    })
  })
})
