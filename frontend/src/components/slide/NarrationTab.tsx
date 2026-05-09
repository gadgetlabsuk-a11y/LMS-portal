import React, { useState } from 'react'
import { useAuth } from '@/context/AuthContext'
import { api, API_BASE } from '@/services/api'
import { useSlideEditorStore } from '@/store/slideEditorStore'

interface Props {
  slideId: number
}

export function NarrationTab({ slideId }: Props) {
  const { token } = useAuth()
  const narrationScript = useSlideEditorStore(s => s.narrationScript)
  const setNarration = useSlideEditorStore(s => s.setNarration)
  const [generating, setGenerating] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSaveScript = async () => {
    await api.put(`/slides/${slideId}`, { narration_script: narrationScript })
  }

  const handleGenerate = async () => {
    setGenerating(true)
    setError(null)
    setNarration('')
    try {
      const res = await fetch(`${API_BASE}/api/slides/${slideId}/ai/generate-narration`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ tone_preset: 'professional' }),
      })
      if (!res.ok) {
        setError('Generation failed. Please try again.')
        return
      }
      const reader = res.body!.getReader()
      const decoder = new TextDecoder()
      let accumulated = ''
      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        for (const line of decoder.decode(value).split('\n')) {
          if (line.startsWith('data: ')) {
            accumulated += line.slice(6)
            setNarration(accumulated)
          }
        }
      }
    } catch (err) {
      setError('Connection error during generation.')
    } finally {
      setGenerating(false)
    }
  }

  return (
    <div className="flex flex-col h-full p-3 gap-3">
      <div className="flex items-center justify-between">
        <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Narration Script</p>
        <button
          data-testid="generate-narration-btn"
          onClick={handleGenerate}
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
