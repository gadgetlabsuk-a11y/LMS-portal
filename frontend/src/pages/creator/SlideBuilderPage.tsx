import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { api } from '@/services/api'
import { VideoSlideStrip } from '@/components/slide/VideoSlideStrip'
import { SlideOutlineWizard } from '@/components/slide/SlideOutlineWizard'

interface Slide {
  id: number
  video_id: number
  title: string
  narration_script: string | null
  narration_audio_url?: string | null
  order_index: number
}

export function SlideBuilderPage() {
  const { id: courseId, videoId } = useParams<{ id: string; videoId: string }>()
  const navigate = useNavigate()
  const [slides, setSlides] = useState<Slide[]>([])
  const [loading, setLoading] = useState(true)
  const [wizardOpen, setWizardOpen] = useState(false)
  const [bulkGenerating, setBulkGenerating] = useState(false)
  const [bulkResult, setBulkResult] = useState<{ generated: number; skipped_no_script: number; skipped_cached: number; errors: number } | null>(null)

  const fetchSlides = () => {
    if (!videoId) return
    api
      .get(`/videos/${videoId}/slides`)
      .then((r) => r.json())
      .then((data: Slide[]) => setSlides(data))
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    fetchSlides()
  }, [videoId])

  const handleBulkGenerate = async () => {
    if (!videoId) return
    setBulkGenerating(true)
    setBulkResult(null)
    try {
      const res = await api.post(`/videos/${videoId}/tts/bulk-generate`, {
        voice_id: '21m00Tcm4TlvDq8ikWAM',
      })
      const data = await res.json()
      setBulkResult(data)
    } catch {
      // Silent error — creator will see 0 generated
    } finally {
      setBulkGenerating(false)
    }
  }

  const handleAddSlide = async () => {
    const res = await api.post(`/videos/${videoId}/slides`, {
      title: `Slide ${slides.length + 1}`,
      order_index: slides.length,
    })
    const newSlide = await res.json()
    setSlides((prev) => [...prev, newSlide])
  }

  return (
    <div data-testid="slide-builder-page" className="flex flex-col h-full">
      <div className="flex items-center justify-between px-6 py-3 border-b bg-white">
        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate(`/creator/courses/${courseId}/builder`)}
            className="text-sm text-gray-500 hover:text-gray-800"
          >
            &larr; Back
          </button>
          <h1 className="text-lg font-semibold">Slide Builder</h1>
        </div>
        <div className="flex items-center gap-2">
          <button
            data-testid="ai-outline-btn"
            onClick={() => setWizardOpen(true)}
            className="px-3 py-1.5 bg-purple-600 text-white text-sm rounded hover:bg-purple-700"
          >
            AI Outline
          </button>
          <button
            data-testid="add-slide-btn"
            onClick={handleAddSlide}
            className="px-3 py-1.5 bg-blue-600 text-white text-sm rounded hover:bg-blue-700"
          >
            + Add Slide
          </button>
          <button
            data-testid="bulk-narration-btn"
            onClick={handleBulkGenerate}
            disabled={bulkGenerating}
            className="px-3 py-1.5 bg-indigo-600 text-white text-sm rounded hover:bg-indigo-700 disabled:opacity-50"
          >
            {bulkGenerating ? 'Generating...' : 'Generate Narration'}
          </button>
        </div>
      </div>

      {bulkResult && (
        <div data-testid="bulk-result-banner" className="px-6 py-2 bg-green-50 border-b text-sm text-green-800">
          Generated {bulkResult.generated} audio file{bulkResult.generated !== 1 ? 's' : ''}.
          {bulkResult.skipped_no_script > 0 && ` Skipped ${bulkResult.skipped_no_script} (no script).`}
          {bulkResult.skipped_cached > 0 && ` Cached ${bulkResult.skipped_cached} (unchanged).`}
          {bulkResult.errors > 0 && ` ${bulkResult.errors} error(s).`}
        </div>
      )}

      <div className="flex flex-1 overflow-hidden">
        <div className="w-72 border-r bg-gray-50 p-4 overflow-y-auto">
          {loading ? (
            <p className="text-sm text-gray-500">Loading slides...</p>
          ) : (
            <VideoSlideStrip
              slides={slides}
              videoId={Number(videoId)}
              courseId={Number(courseId)}
              onSlidesChange={setSlides}
            />
          )}
        </div>
        <div className="flex-1 flex items-center justify-center text-gray-400">
          <p>Select a slide to edit</p>
        </div>
      </div>
      <SlideOutlineWizard
        open={wizardOpen}
        videoId={Number(videoId)}
        anchorSlideId={slides.length > 0 ? slides[slides.length - 1].id : 0}
        onClose={() => setWizardOpen(false)}
        onCommitted={() => {
          setWizardOpen(false)
          fetchSlides()
        }}
      />
    </div>
  )
}
