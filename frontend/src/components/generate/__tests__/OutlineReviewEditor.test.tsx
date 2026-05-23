import { describe, it, expect, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { OutlineReviewEditor } from '../OutlineReviewEditor'
import { useGenerateStore, type OutlineModule } from '@/store/generateFromContentStore'

const outline: OutlineModule[] = [
  { title: 'Module One', description: '', videos: [
    { title: 'Video One', description: '', slides: [
      { title: 'Slide A', brief: 'b' }, { title: 'Slide B', brief: 'b' },
    ]},
  ]},
]

describe('OutlineReviewEditor', () => {
  beforeEach(() => {
    useGenerateStore.getState().reset()
    useGenerateStore.getState().setOutline(JSON.parse(JSON.stringify(outline)))
  })

  it('renders modules, videos and slides', () => {
    render(<OutlineReviewEditor />)
    expect(screen.getByDisplayValue('Module One')).toBeInTheDocument()
    expect(screen.getByDisplayValue('Video One')).toBeInTheDocument()
    expect(screen.getByDisplayValue('Slide A')).toBeInTheDocument()
  })

  it('removing a slide updates the store', async () => {
    render(<OutlineReviewEditor />)
    await userEvent.click(screen.getByTestId('remove-slide-0-0-0'))
    expect(useGenerateStore.getState().outline[0].videos[0].slides).toHaveLength(1)
  })

  it('editing a module title updates the store', async () => {
    render(<OutlineReviewEditor />)
    const input = screen.getByDisplayValue('Module One')
    await userEvent.clear(input)
    await userEvent.type(input, 'Renamed')
    expect(useGenerateStore.getState().outline[0].title).toBe('Renamed')
  })
})
