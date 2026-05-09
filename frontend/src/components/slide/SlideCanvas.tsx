import React from 'react'
import GridLayout, { Layout } from 'react-grid-layout'
import 'react-grid-layout/css/styles.css'
import { api } from '@/services/api'
import type { CanvasBlock } from '@/store/slideEditorStore'
import { BlockRenderer } from './blocks/BlockRenderer'

interface Props {
  blocks: CanvasBlock[]
  slideId: number
  onUpdateBlock: (id: number, updates: Partial<CanvasBlock>) => void
  onDeleteBlock: (id: number) => void
}

export function SlideCanvas({ blocks, slideId: _slideId, onUpdateBlock, onDeleteBlock }: Props) {
  const layout: Layout[] = blocks.map((b) => ({
    i: b.id.toString(),
    x: b.grid_position.x,
    y: b.grid_position.y,
    w: b.grid_position.w,
    h: b.grid_position.h,
  }))

  const handleDragStop = async (_layout: Layout[], _old: Layout, newItem: Layout) => {
    const blockId = parseInt(newItem.i)
    const grid_position = { x: newItem.x, y: newItem.y, w: newItem.w, h: newItem.h }
    onUpdateBlock(blockId, { grid_position })
    await api.put(`/blocks/${blockId}`, { grid_position })
  }

  const handleResizeStop = async (_layout: Layout[], _old: Layout, newItem: Layout) => {
    const blockId = parseInt(newItem.i)
    const grid_position = { x: newItem.x, y: newItem.y, w: newItem.w, h: newItem.h }
    onUpdateBlock(blockId, { grid_position })
    await api.put(`/blocks/${blockId}`, { grid_position })
  }

  return (
    <div className="relative bg-white border rounded-lg overflow-auto" style={{ width: 960, minHeight: 540 }}>
      <GridLayout
        className="slide-canvas"
        layout={layout}
        cols={12}
        rowHeight={40}
        width={960}
        onDragStop={handleDragStop}
        onResizeStop={handleResizeStop}
        isDraggable
        isResizable
        compactType={null}
        preventCollision={false}
      >
        {blocks.map((block) => (
          <div
            key={block.id.toString()}
            data-testid={`canvas-block-${block.id}`}
            className="bg-white border border-gray-200 rounded overflow-hidden group relative"
          >
            <button
              onClick={() => onDeleteBlock(block.id)}
              className="absolute top-1 right-1 z-10 opacity-0 group-hover:opacity-100 text-xs text-gray-400 hover:text-red-500"
              title="Remove block"
            >
              ✕
            </button>
            <BlockRenderer block={block} onUpdate={onUpdateBlock} />
          </div>
        ))}
      </GridLayout>
    </div>
  )
}
