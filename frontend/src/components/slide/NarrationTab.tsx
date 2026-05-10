import React, { useState, useEffect, useRef } from 'react'
import { api } from '@/services/api'
import { useSlideEditorStore } from '@/store/slideEditorStore'
import { useSSEStream } from '@/hooks/useSSEStream'
import { SideDrawer } from '@/components/ai/SideDrawer'
import { StreamingTextOutput } from '@/components/ai/StreamingTextOutput'

interface Props {
  slideId: number
  courseId: number
}

export function NarrationTab({ slideId, courseId }: Props) {
  const narrationScript = useSlideEditorStore(s => s.narrationScript)
  const setNarration = useSlideEditorStore(s => s.setNarration)
  const [error, setError] = useState<string | null>(null)
  const [tonePreset, setTonePreset] = useState('professional')
  const [drawerOpen, setDrawerOpen] = useState(false)
  const { startStream, isStreaming: generating } = useSSEStream()
  const accumulatedRef = useRef('')

  useEffect(() => {
    if (!courseId) return
    api.get(`/courses/${courseId}`)
      .then(res => res.json())
      .then((course: { ai_tone_preset?: string }) => {
        setTonePreset(course.ai_tone_preset || 'professional')
      })
      .catch(() => {})
  }, [courseId])

  const handleSaveScript = async () => {
    await api.put(`/slides/${slideId}`, { narration_script: narrationScript })
  }

  const handleGenerate = async () => {
    setError(null)
    setNarration('')
    accumulatedRef.current = ''
    await startStream({
      url: `/api/slides/${slideId}/ai/generate-narration`,
      body: { tone_preset: tonePreset },
      onToken: t => {
        accumulatedRef.current += t
        setNarration(accumulatedRef.current)
      },
    })
  }

  const handleOpenDrawer = () => {
    setDrawerOpen(true)
    handleGenerate()
  }

  return (
    <div className="flex flex-col h-full p-3 gap-3">
      <SideDrawer
        isOpen={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        title="Generate Narration"
      >
        <div className="flex flex-col gap-3">
          <StreamingTextOutput
            text={narrationScript}
            isStreaming={generating}
            placeholder="AI narration will stream here..."
          />
          {!generating && (
            <button
              onClick={handleGenerate}
              className="text-sm px-3 py-1.5 bg-blue-600 text-white rounded hover:bg-blue-700"
            >
              Regenerate
            </button>
          )}
          <p className="text-xs text-gray-400">
            Close this drawer to edit the narration script directly.
          </p>
        </div>
      </SideDrawer>

      <div className="flex items-center justify-between">
        <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Narration Script</p>
        <button
          data-testid="generate-narration-btn"
          onClick={handleOpenDrawer}
          disabled={generating}
          className="text-xs px-2 py-1 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
        >
          {generating ? 'Generating...' : 'Generate'}
        </button>
      </div>

      {error && <p className="text-xs text-red-500">{error}</p>}

      <textarea
        data-testid="narration-script-textarea"
        value={narrationScript}
        onChange={(e) => setNarration(e.target.value)}
        onBlur={handleSaveScript}
        placeholder="Write the narration script for this slide, or click Generate to create one with AI..."
        className="flex-1 resize-none text-sm p-2 border rounded font-sans leading-relaxed"
      />

      <button
        onClick={handleSaveScript}
        className="text-xs px-3 py-1.5 border rounded text-gray-600 hover:text-gray-900"
      >
        Save script
      </button>
    </div>
  )
}
