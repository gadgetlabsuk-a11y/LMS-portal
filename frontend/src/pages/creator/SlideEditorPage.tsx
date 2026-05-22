import { useEffect, useState, useCallback, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { api } from '@/services/api'
import { useSlideEditorStore } from '@/store/slideEditorStore'
import { SlideCanvas } from '@/components/slide/SlideCanvas'
import { BlockLibraryPalette } from '@/components/slide/BlockLibraryPalette'
import { LayoutPresetPicker } from '@/components/slide/LayoutPresetPicker'
import { NarrationTab } from '@/components/slide/NarrationTab'
import type { CanvasBlock } from '@/store/slideEditorStore'

type RightTab = 'blocks' | 'layout' | 'narration'

export function SlideEditorPage() {
  const { id: courseId, videoId, slideId } = useParams<{
    id: string; videoId: string; slideId: string
  }>()
  const navigate = useNavigate()

  const blocks = useSlideEditorStore(s => s.blocks)
  const isDirty = useSlideEditorStore(s => s.isDirty)
  const setBlocks = useSlideEditorStore(s => s.setBlocks)
  const addBlock = useSlideEditorStore(s => s.addBlock)
  const updateBlock = useSlideEditorStore(s => s.updateBlock)
  const deleteBlock = useSlideEditorStore(s => s.deleteBlock)
  const markClean = useSlideEditorStore(s => s.markClean)
  const { undo, redo, pastStates, futureStates } = useSlideEditorStore.temporal.getState()

  const [activeTab, setActiveTab] = useState<RightTab>('blocks')
  const [saveStatus, setSaveStatus] = useState<'saved' | 'saving' | 'idle'>('idle')
  const [loading, setLoading] = useState(true)
  const saveTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  // Load slide blocks on mount
  useEffect(() => {
    if (!slideId) return
    api.get(`/slides/${slideId}/blocks`)
      .then(r => r.json())
      .then((data: CanvasBlock[]) => setBlocks(data))
      .finally(() => setLoading(false))
  }, [slideId])

  // Debounced autosave (500ms) — fires on content changes only
  // Grid position is saved immediately on onDragStop/onResizeStop in SlideCanvas
  const flushSave = useCallback(async () => {
    if (!isDirty) return
    setSaveStatus('saving')
    // Content changes — PUT each block's content (grid_position is saved by canvas directly)
    for (const block of blocks) {
      await api.put(`/blocks/${block.id}`, { content: block.content })
    }
    markClean()
    setSaveStatus('saved')
  }, [blocks, isDirty, markClean])

  useEffect(() => {
    if (!isDirty) return
    setSaveStatus('saving')
    if (saveTimerRef.current) clearTimeout(saveTimerRef.current)
    saveTimerRef.current = setTimeout(() => {
      flushSave()
    }, 500)
    return () => {
      if (saveTimerRef.current) clearTimeout(saveTimerRef.current)
    }
  }, [blocks, isDirty])

  // Flush any pending save when leaving the editor. (We previously used
  // react-router's useBlocker here, but that hook only works inside a data
  // router — under the app's <BrowserRouter> it throws and white-screens the
  // editor. Content is already persisted by the 500ms debounced autosave; this
  // unmount-only flush covers the trailing edit without re-running on changes.)
  const flushRef = useRef(flushSave)
  flushRef.current = flushSave
  useEffect(() => {
    return () => {
      void flushRef.current()
    }
  }, [])

  // Keyboard shortcuts for undo/redo
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'z') {
        e.preventDefault()
        if (e.shiftKey) {
          redo()
        } else {
          undo()
        }
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [undo, redo])

  const handleDeleteBlock = async (id: number) => {
    deleteBlock(id)
    await api.delete(`/blocks/${id}`)
  }

  const handleBlocksReplaced = (newBlocks: CanvasBlock[]) => {
    setBlocks(newBlocks)
  }

  return (
    <div data-testid="slide-editor-page" className="flex flex-col h-full">
      {/* Toolbar */}
      <div className="flex items-center justify-between px-6 py-3 border-b bg-white">
        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate(`/creator/courses/${courseId}/videos/${videoId}/slides`)}
            className="text-sm text-gray-500 hover:text-gray-800"
          >
            ← Slides
          </button>
          <h1 className="text-lg font-semibold">Slide Editor</h1>
        </div>
        <div className="flex items-center gap-2">
          <button
            data-testid="undo-btn"
            onClick={() => undo()}
            disabled={pastStates.length === 0}
            className="px-2 py-1 text-sm border rounded disabled:opacity-40"
            title="Undo (Cmd+Z)"
          >
            ↩ Undo
          </button>
          <button
            data-testid="redo-btn"
            onClick={() => redo()}
            disabled={futureStates.length === 0}
            className="px-2 py-1 text-sm border rounded disabled:opacity-40"
            title="Redo (Cmd+Shift+Z)"
          >
            ↪ Redo
          </button>
          <span
            data-testid="save-status"
            className={`text-xs px-2 py-1 rounded ${
              saveStatus === 'saved'
                ? 'text-green-600 bg-green-50'
                : saveStatus === 'saving'
                ? 'text-yellow-600 bg-yellow-50'
                : 'text-gray-400'
            }`}
          >
            {saveStatus === 'saved' ? 'Saved' : saveStatus === 'saving' ? 'Saving...' : ''}
          </span>
        </div>
      </div>

      {/* Main editor area */}
      <div className="flex flex-1 overflow-hidden">
        {/* Canvas area */}
        <div className="flex-1 p-6 overflow-auto bg-gray-100">
          {loading ? (
            <p className="text-sm text-gray-500">Loading...</p>
          ) : (
            <SlideCanvas
              blocks={blocks}
              slideId={Number(slideId)}
              onUpdateBlock={updateBlock}
              onDeleteBlock={handleDeleteBlock}
            />
          )}
        </div>

        {/* Right panel */}
        <div className="w-64 border-l bg-white flex flex-col">
          {/* Tabs */}
          <div className="flex border-b">
            {(['blocks', 'layout', 'narration'] as RightTab[]).map(tab => (
              <button
                key={tab}
                data-testid={`tab-${tab}`}
                onClick={() => setActiveTab(tab)}
                className={`flex-1 py-2 text-xs capitalize ${
                  activeTab === tab
                    ? 'border-b-2 border-blue-500 text-blue-600 font-medium'
                    : 'text-gray-500 hover:text-gray-700'
                }`}
              >
                {tab}
              </button>
            ))}
          </div>

          {/* Tab content */}
          <div className="flex-1 overflow-y-auto">
            {activeTab === 'blocks' && (
              <BlockLibraryPalette
                slideId={Number(slideId)}
                blockCount={blocks.length}
                onBlockAdded={addBlock}
              />
            )}
            {activeTab === 'layout' && (
              <LayoutPresetPicker
                slideId={Number(slideId)}
                currentBlocks={blocks}
                onBlocksReplaced={handleBlocksReplaced}
              />
            )}
            {activeTab === 'narration' && (
              <NarrationTab slideId={Number(slideId)} courseId={Number(courseId)} />
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
