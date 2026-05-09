import { useState, useRef } from 'react'
import { API_BASE } from '@/services/api'

interface StartStreamOptions {
  url: string
  body: Record<string, unknown>
  onToken?: (token: string) => void
}

export function useSSEStream() {
  const [text, setText] = useState('')
  const [isStreaming, setIsStreaming] = useState(false)
  const abortRef = useRef<AbortController | null>(null)

  const startStream = async ({ url, body, onToken }: StartStreamOptions) => {
    abortRef.current?.abort()
    const controller = new AbortController()
    abortRef.current = controller
    setIsStreaming(true)
    setText('')

    try {
      const token = localStorage.getItem('token')
      const res = await fetch(`${API_BASE}${url}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(body),
        signal: controller.signal,
      })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const reader = res.body!.getReader()
      const decoder = new TextDecoder()
      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        const chunk = decoder.decode(value)
        for (const line of chunk.split('\n')) {
          if (line.startsWith('data: ')) {
            const t = line.slice(6)
            setText(prev => prev + t)
            onToken?.(t)
          }
        }
      }
    } catch (e: unknown) {
      if (e instanceof Error && e.name !== 'AbortError') {
        console.error('SSE stream error:', e)
      }
    } finally {
      setIsStreaming(false)
    }
  }

  const cancel = () => {
    abortRef.current?.abort()
  }

  const reset = () => {
    setText('')
  }

  return { text, isStreaming, startStream, cancel, reset, setText }
}
