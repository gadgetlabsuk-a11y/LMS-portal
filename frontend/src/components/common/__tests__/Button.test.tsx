import { render, screen } from '@testing-library/react'
import { Button } from '../Button'

describe('Button', () => {
  it('applies Stadler yellow classes for the accent variant', () => {
    render(<Button variant="accent">Save</Button>)
    const btn = screen.getByRole('button', { name: 'Save' })
    expect(btn.className).toContain('bg-brand-accent')
    expect(btn.className).toContain('text-brand-dark')
  })

  it('still defaults to the primary (Stadler blue) variant', () => {
    render(<Button>Go</Button>)
    const btn = screen.getByRole('button', { name: 'Go' })
    expect(btn.className).toContain('bg-blue-600')
  })
})
