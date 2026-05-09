import React from 'react'
import { api } from '@/services/api'
import type { CanvasBlock } from '@/store/slideEditorStore'

const BLOCK_TYPES = [
  { type: 'heading', label: 'Heading', icon: 'H' },
  { type: 'text', label: 'Text', icon: 'T' },
  { type: 'image', label: 'Image', icon: '🖼' },
  { type: 'video_embed', label: 'Video', icon: '▶' },
  { type: 'code', label: 'Code', icon: '</>' },
  { type: 'quote', label: 'Quote', icon: '"' },
  { type: 'list', label: 'List', icon: '≡' },
  { type: 'callout', label: 'Callout', icon: '!' },
  { type: 'divider', label: 'Divider', icon: '—' },
]

const BLOCK_DEFAULTS: Record<string, { w: number; h: number }> = {
  heading:     { w: 12, h: 2 },
  text:        { w: 8,  h: 4 },
  image:       { w: 6,  h: 5 },
  video_embed: { w: 8,  h: 5 },
  code:        { w: 8,  h: 6 },
  quote:       { w: 8,  h: 3 },
  list:        { w: 6,  h: 5 },
  callout:     { w: 12, h: 3 },
  divider:     { w: 12, h: 1 },
}

interface Props {
  slideId: number
  blockCount: number
  onBlockAdded: (block: CanvasBlock) => void
}

export function BlockLibraryPalette({ slideId, blockCount, onBlockAdded }: Props) {
  const handleAdd = async (blockType: string) => {
    const defaults = BLOCK_DEFAULTS[blockType]
    const res = await api.post(`/slides/${slideId}/blocks`, {
      type: blockType,
      content: {},
      grid_position: { x: 0, y: blockCount * 3, w: defaults.w, h: defaults.h },
      order_index: blockCount,
    })
    const newBlock = await res.json()
    onBlockAdded(newBlock)
  }

  return (
    <div className="flex flex-col gap-1 p-3">
      <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Blocks</p>
      {BLOCK_TYPES.map(({ type, label, icon }) => (
        <button
          key={type}
          data-testid={`palette-${type}-btn`}
          onClick={() => handleAdd(type)}
          className="flex items-center gap-2 px-3 py-2 text-sm text-left rounded hover:bg-blue-50 hover:text-blue-700"
        >
          <span className="w-6 text-center font-mono text-xs">{icon}</span>
          {label}
        </button>
      ))}
    </div>
  )
}
