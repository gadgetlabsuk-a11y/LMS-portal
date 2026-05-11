import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { AISuggestionsRail } from '../AISuggestionsRail'
import type { BuilderModule } from '@/components/builder/types'

const makeModule = (overrides: Partial<BuilderModule> = {}): BuilderModule => ({
  id: 1,
  order_index: 0,
  title: 'Module 1',
  description: 'Has a description',
  status: 'draft',
  ...overrides,
})

describe('AISuggestionsRail', () => {
  it('shows no-modules nudge when modules array is empty', () => {
    render(<AISuggestionsRail modules={[]} videos={{}} quizzes={{}} />)
    expect(screen.getByTestId('suggestion-no-modules')).toBeInTheDocument()
  })

  it('shows missing-description nudge for module with empty description', () => {
    const mod = makeModule({ id: 2, title: 'Empty Desc', description: '' })
    render(<AISuggestionsRail modules={[mod]} videos={{ 2: [{ id: 10, module_id: 2, order_index: 0, title: 'V1', status: 'draft' }] }} quizzes={{}} />)
    expect(screen.getByTestId('suggestion-missing-description-2')).toBeInTheDocument()
  })

  it('shows missing-description nudge for module with null description', () => {
    const mod = makeModule({ id: 3, description: null })
    render(<AISuggestionsRail modules={[mod]} videos={{ 3: [{ id: 11, module_id: 3, order_index: 0, title: 'V2', status: 'draft' }] }} quizzes={{}} />)
    expect(screen.getByTestId('suggestion-missing-description-3')).toBeInTheDocument()
  })

  it('does NOT show missing-description nudge when description is present', () => {
    const mod = makeModule({ id: 4, description: 'A real description' })
    render(<AISuggestionsRail modules={[mod]} videos={{ 4: [{ id: 12, module_id: 4, order_index: 0, title: 'V3', status: 'draft' }] }} quizzes={{}} />)
    expect(screen.queryByTestId('suggestion-missing-description-4')).not.toBeInTheDocument()
  })

  it('shows empty-module nudge when module has no videos and no quizzes', () => {
    const mod = makeModule({ id: 5, description: 'Has description' })
    render(<AISuggestionsRail modules={[mod]} videos={{}} quizzes={{}} />)
    expect(screen.getByTestId('suggestion-empty-module-5')).toBeInTheDocument()
  })

  it('does NOT show empty-module nudge when module has a video', () => {
    const mod = makeModule({ id: 6, description: 'Has desc' })
    render(<AISuggestionsRail modules={[mod]} videos={{ 6: [{ id: 13, module_id: 6, order_index: 0, title: 'V4', status: 'draft' }] }} quizzes={{}} />)
    expect(screen.queryByTestId('suggestion-empty-module-6')).not.toBeInTheDocument()
  })

  it('shows no nudges when all modules have descriptions and content', () => {
    const mod = makeModule({ id: 7, description: 'All good' })
    render(<AISuggestionsRail modules={[mod]} videos={{ 7: [{ id: 14, module_id: 7, order_index: 0, title: 'V5', status: 'draft' }] }} quizzes={{}} />)
    expect(screen.queryByTestId(/^suggestion-/)).not.toBeInTheDocument()
  })
})
