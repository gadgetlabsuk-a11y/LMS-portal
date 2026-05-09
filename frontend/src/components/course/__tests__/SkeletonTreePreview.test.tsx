/**
 * Phase 12 stub — SkeletonTreePreview (COURSE-04).
 * This test will fail with import error until 12-03 creates the component.
 */
import { describe, it, expect } from 'vitest'
import { render } from '@testing-library/react'
import { SkeletonTreePreview } from '../SkeletonTreePreview'

describe('SkeletonTreePreview', () => {
  it('renders skeleton tree nodes for given module and video counts', () => {
    const { getAllByRole } = render(
      <SkeletonTreePreview moduleCount={2} videosPerModule={2} quizPerModule={false} />
    )
    // 2 modules + 4 videos = 6 tree items
    expect(getAllByRole('listitem').length).toBe(6)
  })

  it('includes quiz nodes when quizPerModule is true', () => {
    const { getAllByText } = render(
      <SkeletonTreePreview moduleCount={1} videosPerModule={1} quizPerModule={true} />
    )
    expect(getAllByText(/Quiz/i).length).toBe(1)
  })
})
