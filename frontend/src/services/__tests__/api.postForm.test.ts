import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { api } from '../api'

describe('api.postForm', () => {
  beforeEach(() => {
    localStorage.setItem('token', 'tok123')
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, status: 200 }))
  })
  afterEach(() => {
    vi.unstubAllGlobals()
    localStorage.clear()
  })

  it('posts FormData with auth header and no JSON content-type', async () => {
    const fd = new FormData()
    fd.append('x', 'y')
    await api.postForm('/courses/from-outline', fd)
    const [url, init] = (fetch as unknown as ReturnType<typeof vi.fn>).mock.calls[0]
    expect(url).toContain('/api/courses/from-outline')
    expect(init.method).toBe('POST')
    expect(init.body).toBe(fd)
    expect(init.headers.Authorization).toBe('Bearer tok123')
    expect(init.headers['Content-Type']).toBeUndefined()
  })
})
