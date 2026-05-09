import { create } from 'zustand'
import { temporal } from 'zundo'

export interface CanvasBlock {
  id: number
  type: string
  content: Record<string, unknown>
  grid_position: { x: number; y: number; w: number; h: number }
  order_index: number
}

interface SlideEditorState {
  blocks: CanvasBlock[]
  isDirty: boolean
  narrationScript: string
  slideTitle: string
  addBlock: (block: CanvasBlock) => void
  updateBlock: (id: number, updates: Partial<CanvasBlock>) => void
  deleteBlock: (id: number) => void
  setBlocks: (blocks: CanvasBlock[]) => void
  setNarration: (script: string) => void
  setSlideTitle: (title: string) => void
  markClean: () => void
}

export const useSlideEditorStore = create<SlideEditorState>()(
  temporal(
    (set) => ({
      blocks: [],
      isDirty: false,
      narrationScript: '',
      slideTitle: '',
      addBlock: (block) =>
        set((s) => ({ blocks: [...s.blocks, block], isDirty: true })),
      updateBlock: (id, updates) =>
        set((s) => ({
          blocks: s.blocks.map((b) => (b.id === id ? { ...b, ...updates } : b)),
          isDirty: true,
        })),
      deleteBlock: (id) =>
        set((s) => ({
          blocks: s.blocks.filter((b) => b.id !== id),
          isDirty: true,
        })),
      setBlocks: (blocks) => set({ blocks, isDirty: false }),
      setNarration: (script) => set({ narrationScript: script, isDirty: true }),
      setSlideTitle: (title) => set({ slideTitle: title }),
      markClean: () => set({ isDirty: false }),
    }),
    { limit: 20 }
  )
)
