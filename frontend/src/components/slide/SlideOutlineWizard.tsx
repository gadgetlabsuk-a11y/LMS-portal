import React, { useState } from 'react'
import { useAuth } from '@/context/AuthContext'
import { api, API_BASE } from '@/services/api'

type WizardStep = 1 | 2 | 3 | 4

interface SlideOutlineBlock {
  type: string
  content: Record<string, unknown>
}

interface SlideOutlineItem {
  title: string
  blocks: SlideOutlineBlock[]
}

interface Props {
  open: boolean
  videoId: number
  anchorSlideId: number
  onClose: () => void
  onCommitted: () => void
}

export function SlideOutlineWizard({ open, videoId, anchorSlideId, onClose, onCommitted }: Props) {
  const { token } = useAuth()
  const [step, setStep] = useState<WizardStep>(1)
  const [sourcePrompt, setSourcePrompt] = useState('')
  const [slideCount, setSlideCount] = useState(5)
  const [tonePreset, setTonePreset] = useState('professional')
  const [outline, setOutline] = useState<SlideOutlineItem[]>([])
  const [generating, setGenerating] = useState(false)
  const [parseError, setParseError] = useState<string | null>(null)
  const [committing, setCommitting] = useState(false)

  if (!open) return null

  const handleGenerate = async () => {
    setGenerating(true)
    setParseError(null)
    try {
      const res = await fetch(`${API_BASE}/api/slides/${anchorSlideId}/ai/generate-outline`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ prompt: sourcePrompt, slide_count: slideCount, tone_preset: tonePreset }),
      })
      if (!res.ok) {
        setParseError('Generation failed. Please try again.')
        setGenerating(false)
        return
      }
      const reader = res.body!.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        for (const line of decoder.decode(value).split('\n')) {
          if (line.startsWith('data: ')) buffer += line.slice(6)
        }
      }
      // Only parse after stream is complete (research pitfall #7)
      const parsed: SlideOutlineItem[] = JSON.parse(buffer)
      setOutline(parsed)
      setStep(4)
    } catch (err) {
      setParseError('Failed to parse AI response. Try again.')
    } finally {
      setGenerating(false)
    }
  }

  const handleCommit = async () => {
    setCommitting(true)
    for (let i = 0; i < outline.length; i++) {
      const item = outline[i]
      const slideRes = await api.post(`/videos/${videoId}/slides`, {
        title: item.title,
        order_index: i,
      })
      const newSlide = await slideRes.json()
      for (let j = 0; j < (item.blocks || []).length; j++) {
        const block = item.blocks[j]
        await api.post(`/slides/${newSlide.id}/blocks`, {
          type: block.type,
          content: block.content || {},
          grid_position: { x: 0, y: j * 4, w: 12, h: 4 },
          order_index: j,
        })
      }
    }
    setCommitting(false)
    onCommitted()
    onClose()
    // Reset wizard
    setStep(1)
    setSourcePrompt('')
    setOutline([])
  }

  return (
    <div
      data-testid="outline-wizard"
      className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <div className="bg-white rounded-xl shadow-2xl w-[640px] max-h-[80vh] flex flex-col overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b">
          <h2 className="text-lg font-semibold">AI Slide Outline Wizard</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-700 text-xl">&#x2715;</button>
        </div>

        {/* Step indicator */}
        <div className="flex items-center gap-2 px-6 py-3 border-b text-xs">
          {[1, 2, 3, 4].map(n => (
            <React.Fragment key={n}>
              <span className={`w-6 h-6 rounded-full flex items-center justify-center font-medium ${
                step === n ? 'bg-blue-600 text-white' : step > n ? 'bg-green-500 text-white' : 'bg-gray-200 text-gray-500'
              }`}>{n}</span>
              {n < 4 && <div className="flex-1 h-px bg-gray-200" />}
            </React.Fragment>
          ))}
        </div>

        {/* Step content */}
        <div className="flex-1 overflow-y-auto p-6">
          {/* Step 1: Source */}
          {step === 1 && (
            <div data-testid="wizard-step-1" className="flex flex-col gap-4">
              <div>
                <label className="block text-sm font-medium mb-1">What is this video about?</label>
                <textarea
                  data-testid="wizard-source-prompt"
                  value={sourcePrompt}
                  onChange={(e) => setSourcePrompt(e.target.value)}
                  placeholder="Describe the topic for the slide outline..."
                  rows={4}
                  className="w-full border rounded p-3 text-sm resize-none"
                />
              </div>
            </div>
          )}

          {/* Step 2: Config */}
          {step === 2 && (
            <div data-testid="wizard-step-2" className="flex flex-col gap-4">
              <div>
                <label className="block text-sm font-medium mb-1">Number of slides</label>
                <input
                  type="number"
                  min={1}
                  max={20}
                  value={slideCount}
                  onChange={(e) => setSlideCount(parseInt(e.target.value) || 5)}
                  className="border rounded px-3 py-2 text-sm w-32"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Tone</label>
                <select
                  value={tonePreset}
                  onChange={(e) => setTonePreset(e.target.value)}
                  className="border rounded px-3 py-2 text-sm"
                >
                  <option value="professional">Professional</option>
                  <option value="casual">Casual</option>
                  <option value="academic">Academic</option>
                </select>
              </div>
            </div>
          )}

          {/* Step 3: Generation */}
          {step === 3 && (
            <div data-testid="wizard-step-3" className="flex flex-col items-center gap-4 py-8">
              {!generating && !parseError && (
                <button
                  data-testid="wizard-generate-btn"
                  onClick={handleGenerate}
                  className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-medium"
                >
                  Generate outline
                </button>
              )}
              {generating && (
                <div className="flex flex-col items-center gap-2">
                  <div className="animate-spin w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full" />
                  <p className="text-sm text-gray-500">Generating slide outline...</p>
                </div>
              )}
              {parseError && (
                <p className="text-sm text-red-500">{parseError}</p>
              )}
            </div>
          )}

          {/* Step 4: Commit */}
          {step === 4 && (
            <div data-testid="wizard-step-4" className="flex flex-col gap-3">
              <p className="text-sm text-gray-600">{outline.length} slides ready to add:</p>
              <ul className="space-y-1">
                {outline.map((item, i) => (
                  <li key={i} className="flex items-center gap-2 text-sm">
                    <span className="text-gray-400 w-5 text-right text-xs">{i + 1}.</span>
                    <span>{item.title}</span>
                    <span className="text-xs text-gray-400">
                      ({(item.blocks || []).length} blocks)
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>

        {/* Footer actions */}
        <div className="flex items-center justify-between px-6 py-4 border-t bg-gray-50">
          <button
            onClick={() => { if (step > 1) setStep((s) => (s - 1) as WizardStep) }}
            disabled={step === 1 || generating}
            className="px-4 py-2 text-sm border rounded disabled:opacity-40"
          >
            Back
          </button>
          <div className="flex gap-2">
            <button
              onClick={onClose}
              className="px-4 py-2 text-sm border rounded text-gray-600"
            >
              Cancel
            </button>
            {step < 3 && (
              <button
                data-testid="wizard-next-btn"
                onClick={() => setStep((s) => (s + 1) as WizardStep)}
                disabled={step === 1 && !sourcePrompt.trim()}
                className="px-4 py-2 text-sm bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-40"
              >
                Next
              </button>
            )}
            {step === 4 && (
              <button
                data-testid="wizard-commit-btn"
                onClick={handleCommit}
                disabled={committing}
                className="px-4 py-2 text-sm bg-green-600 text-white rounded hover:bg-green-700 disabled:opacity-50"
              >
                {committing ? 'Adding slides...' : `Add ${outline.length} slides`}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
