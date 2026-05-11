import { api } from '@/services/api'
import type { CanvasBlock } from '@/store/slideEditorStore'

const LAYOUT_PRESETS: Record<string, Array<{ type: string; grid_position: { x: number; y: number; w: number; h: number } }>> = {
  blank: [],
  'title-only': [
    { type: 'heading', grid_position: { x: 1, y: 3, w: 10, h: 3 } },
  ],
  'title-content': [
    { type: 'heading', grid_position: { x: 0, y: 0, w: 12, h: 2 } },
    { type: 'text',    grid_position: { x: 0, y: 2, w: 12, h: 6 } },
  ],
  'two-column': [
    { type: 'text',  grid_position: { x: 0, y: 0, w: 6, h: 8 } },
    { type: 'image', grid_position: { x: 6, y: 0, w: 6, h: 8 } },
  ],
  'full-bleed-image': [
    { type: 'image',   grid_position: { x: 0, y: 0, w: 12, h: 8 } },
    { type: 'heading', grid_position: { x: 1, y: 8, w: 10, h: 2 } },
  ],
  'code-slide': [
    { type: 'heading', grid_position: { x: 0, y: 0, w: 12, h: 2 } },
    { type: 'code',    grid_position: { x: 0, y: 2, w: 12, h: 7 } },
  ],
}

const PRESET_LABELS: Record<string, string> = {
  blank: 'Blank',
  'title-only': 'Title Only',
  'title-content': 'Title + Content',
  'two-column': 'Two Column',
  'full-bleed-image': 'Full Image',
  'code-slide': 'Code Slide',
}

interface Props {
  slideId: number
  currentBlocks: CanvasBlock[]
  onBlocksReplaced: (blocks: CanvasBlock[]) => void
}

export function LayoutPresetPicker({ slideId, currentBlocks, onBlocksReplaced }: Props) {
  const applyPreset = async (presetKey: string) => {
    // Delete all existing blocks
    for (const block of currentBlocks) {
      await api.delete(`/blocks/${block.id}`)
    }
    // Create new blocks from preset
    const preset = LAYOUT_PRESETS[presetKey]
    const newBlocks: CanvasBlock[] = []
    for (let i = 0; i < preset.length; i++) {
      const item = preset[i]
      const res = await api.post(`/slides/${slideId}/blocks`, {
        type: item.type,
        content: {},
        grid_position: item.grid_position,
        order_index: i,
      })
      newBlocks.push(await res.json())
    }
    onBlocksReplaced(newBlocks)
  }

  return (
    <div className="flex flex-col gap-2 p-3">
      <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">Layout Presets</p>
      {Object.entries(PRESET_LABELS).map(([key, label]) => (
        <button
          key={key}
          data-testid={`preset-${key}-btn`}
          onClick={() => applyPreset(key)}
          className="px-3 py-2 text-sm text-left rounded border hover:border-blue-400 hover:text-blue-700"
        >
          {label}
        </button>
      ))}
    </div>
  )
}
