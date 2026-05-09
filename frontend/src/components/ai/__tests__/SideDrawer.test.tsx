import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { SideDrawer } from '../SideDrawer'
import { StreamingTextOutput } from '../StreamingTextOutput'

describe('SideDrawer', () => {
  it('renders title and children when isOpen=true', () => {
    render(
      <SideDrawer isOpen={true} onClose={() => {}} title="Generate Description">
        <p>drawer content</p>
      </SideDrawer>
    )
    expect(screen.getByTestId('side-drawer')).toBeInTheDocument()
    expect(screen.getByText('Generate Description')).toBeInTheDocument()
    expect(screen.getByText('drawer content')).toBeInTheDocument()
  })

  it('returns null when isOpen=false', () => {
    render(<SideDrawer isOpen={false} onClose={() => {}} title="Test"><p>content</p></SideDrawer>)
    expect(screen.queryByTestId('side-drawer')).not.toBeInTheDocument()
  })

  it('calls onClose when overlay is clicked', () => {
    const onClose = vi.fn()
    render(<SideDrawer isOpen={true} onClose={onClose} title="Test"><span /></SideDrawer>)
    fireEvent.click(screen.getByTestId('side-drawer-overlay'))
    expect(onClose).toHaveBeenCalledOnce()
  })

  it('calls onClose when Escape key is pressed', () => {
    const onClose = vi.fn()
    render(<SideDrawer isOpen={true} onClose={onClose} title="Test"><span /></SideDrawer>)
    fireEvent.keyDown(document, { key: 'Escape' })
    expect(onClose).toHaveBeenCalledOnce()
  })
})

describe('StreamingTextOutput', () => {
  it('shows text content', () => {
    render(<StreamingTextOutput text="Hello world" isStreaming={false} />)
    expect(screen.getByText('Hello world')).toBeInTheDocument()
  })

  it('shows streaming cursor when isStreaming=true', () => {
    render(<StreamingTextOutput text="partial" isStreaming={true} />)
    expect(screen.getByTestId('streaming-cursor')).toBeInTheDocument()
  })

  it('hides cursor when isStreaming=false', () => {
    render(<StreamingTextOutput text="done" isStreaming={false} />)
    expect(screen.queryByTestId('streaming-cursor')).not.toBeInTheDocument()
  })
})
