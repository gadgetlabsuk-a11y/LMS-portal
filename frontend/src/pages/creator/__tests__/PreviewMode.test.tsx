import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
// This import does not exist yet — vitest fails at collection (RED state)
import { CoursePreviewPage } from '../CoursePreviewPage'

vi.mock('@/services/api', () => ({
  api: {
    get: vi.fn().mockResolvedValue({ data: { id: 1, title: 'Test Course', modules: [] } }),
  },
}))

vi.mock('@/context/AuthContext', () => ({
  useAuth: () => ({ user: { id: 1, role: 'creator' }, isAuthenticated: true }),
}))

describe('CoursePreviewPage', () => {
  it('renders draft watermark (PREVIEW-01)', () => {
    // stub — fails at collection before implementation
    expect(true).toBe(false)
  })

  it('shows exit preview button that navigates to returnTo (PREVIEW-03)', () => {
    // stub — fails at collection before implementation
    expect(true).toBe(false)
  })

  it('displays course modules and content (PREVIEW-02)', () => {
    // stub — fails at collection before implementation
    expect(true).toBe(false)
  })
})
