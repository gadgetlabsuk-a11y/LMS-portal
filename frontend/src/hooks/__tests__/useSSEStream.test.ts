import { renderHook, act } from '@testing-library/react'
import { vi, describe, it, expect, beforeEach } from 'vitest'
import { useSSEStream } from '../useSSEStream'

beforeEach(() => {
  vi.resetAllMocks()
})

describe('useSSEStream', () => {
  it('starts in idle state', () => {
    const { result } = renderHook(() => useSSEStream())
    expect(result.current.text).toBe('')
    expect(result.current.isStreaming).toBe(false)
  })

  it('calls fetch with correct URL and Authorization header', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      body: {
        getReader: () => ({
          read: vi.fn()
            .mockResolvedValueOnce({ done: false, value: new TextEncoder().encode('data: hello\n') })
            .mockResolvedValueOnce({ done: true, value: undefined }),
        }),
      },
    })
    vi.stubGlobal('fetch', mockFetch)
    localStorage.setItem('token', 'test-token')

    const { result } = renderHook(() => useSSEStream())
    await act(async () => {
      await result.current.startStream({ url: '/api/test', body: { prompt: 'hi' } })
    })

    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/test'),
      expect.objectContaining({
        headers: expect.objectContaining({ Authorization: 'Bearer test-token' }),
      })
    )
    expect(result.current.text).toBe('hello')
  })

  it('calls onToken callback for each token', async () => {
    const tokens: string[] = []
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      body: {
        getReader: () => ({
          read: vi.fn()
            .mockResolvedValueOnce({ done: false, value: new TextEncoder().encode('data: foo\ndata: bar\n') })
            .mockResolvedValueOnce({ done: true, value: undefined }),
        }),
      },
    })
    vi.stubGlobal('fetch', mockFetch)

    const { result } = renderHook(() => useSSEStream())
    await act(async () => {
      await result.current.startStream({ url: '/api/test', body: {}, onToken: t => tokens.push(t) })
    })

    expect(tokens).toEqual(['foo', 'bar'])
  })

  it('cancel() aborts the fetch', async () => {
    let abortCalled = false
    const mockAbortController = {
      abort: vi.fn(() => { abortCalled = true }),
      signal: {},
    }
    vi.stubGlobal('AbortController', vi.fn(() => mockAbortController))
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true,
      body: { getReader: () => ({ read: vi.fn().mockResolvedValue({ done: true }) }) },
    }))

    const { result } = renderHook(() => useSSEStream())
    act(() => { result.current.cancel() })
    expect(abortCalled).toBe(true)
  })
})
