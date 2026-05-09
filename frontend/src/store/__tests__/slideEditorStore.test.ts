import { describe, it, expect, beforeEach } from 'vitest'
import { act } from 'react'
import { useSlideEditorStore } from '../slideEditorStore'

const sampleBlock = {
  id: 1, type: 'text', content: { text: 'Hello' },
  grid_position: { x: 0, y: 0, w: 6, h: 4 }, order_index: 0,
}

describe('slideEditorStore', () => {
  beforeEach(() => {
    useSlideEditorStore.setState({ blocks: [], isDirty: false, narrationScript: '', slideTitle: '' })
    useSlideEditorStore.temporal.getState().clear()
  })

  it('SLIDE-07: addBlock sets isDirty true', () => {
    act(() => useSlideEditorStore.getState().addBlock(sampleBlock))
    expect(useSlideEditorStore.getState().isDirty).toBe(true)
    expect(useSlideEditorStore.getState().blocks).toHaveLength(1)
  })

  it('SLIDE-07: undo/redo restores previous state', () => {
    act(() => useSlideEditorStore.getState().addBlock(sampleBlock))
    act(() => useSlideEditorStore.getState().addBlock({ ...sampleBlock, id: 2 }))
    expect(useSlideEditorStore.getState().blocks).toHaveLength(2)

    act(() => useSlideEditorStore.temporal.getState().undo())
    expect(useSlideEditorStore.getState().blocks).toHaveLength(1)

    act(() => useSlideEditorStore.temporal.getState().redo())
    expect(useSlideEditorStore.getState().blocks).toHaveLength(2)
  })

  it('SLIDE-07: temporal store limit is 20', () => {
    // Add 25 blocks to exceed limit
    for (let i = 0; i < 25; i++) {
      act(() => useSlideEditorStore.getState().addBlock({ ...sampleBlock, id: i + 10 }))
    }
    const { pastStates } = useSlideEditorStore.temporal.getState()
    expect(pastStates.length).toBeLessThanOrEqual(20)
  })

  it('setBlocks marks isDirty false', () => {
    act(() => useSlideEditorStore.getState().setBlocks([sampleBlock]))
    expect(useSlideEditorStore.getState().isDirty).toBe(false)
  })

  it('deleteBlock removes block and sets isDirty', () => {
    act(() => useSlideEditorStore.getState().setBlocks([sampleBlock]))
    act(() => useSlideEditorStore.getState().deleteBlock(1))
    expect(useSlideEditorStore.getState().blocks).toHaveLength(0)
    expect(useSlideEditorStore.getState().isDirty).toBe(true)
  })
})
