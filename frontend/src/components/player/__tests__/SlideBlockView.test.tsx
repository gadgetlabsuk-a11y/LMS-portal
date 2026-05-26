import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { SlideBlockView } from '../SlideBlockView'

describe('SlideBlockView', () => {
  it('renders heading html', () => {
    render(<SlideBlockView block={{ id: 1, type: 'heading', content: { html: '<h1>Hello</h1>' }, order_index: 0 }} />)
    expect(screen.getByText('Hello')).toBeInTheDocument()
  })
  it('renders image url', () => {
    render(<SlideBlockView block={{ id: 2, type: 'image', content: { url: 'http://x/y.png' }, order_index: 0 }} />)
    expect(screen.getByRole('img')).toHaveAttribute('src', 'http://x/y.png')
  })
  it('renders unknown type as text without crashing', () => {
    render(<SlideBlockView block={{ id: 3, type: 'callout', content: { text: 'Note!' }, order_index: 0 }} />)
    expect(screen.getByText('Note!')).toBeInTheDocument()
  })
})
