import { useSSEStream } from '../useSSEStream'

// AI-01: useSSEStream hook encapsulates fetch+ReadableStream+AbortController
// This import will fail at vitest collection until useSSEStream.ts is created (RED state)
describe('useSSEStream', () => {
  it('returns startStream, cancel, text, isStreaming', () => {
    expect(useSSEStream).toBeDefined()
  })
})
