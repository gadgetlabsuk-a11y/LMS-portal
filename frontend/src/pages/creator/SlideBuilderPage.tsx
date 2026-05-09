import React, { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { api } from '@/services/api'
import { VideoSlideStrip } from '@/components/slide/VideoSlideStrip'

interface Slide {
  id: number
  video_id: number
  title: string
  narration_script: string | null
  order_index: number
}

export function SlideBuilderPage() {
  const { id: courseId, videoId } = useParams<{ id: string; videoId: string }>()
  const navigate = useNavigate()
  const [slides, setSlides] = useState<Slide[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!videoId) return
    api
      .get(`/videos/${videoId}/slides`)
      .then((r) => r.json())
      .then((data: Slide[]) => setSlides(data))
      .finally(() => setLoading(false))
  }, [videoId])

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
            data-testid="add-slide-btn"
            onClick={handleAddSlide}
            className="px-3 py-1.5 bg-blue-600 text-white text-sm rounded hover:bg-blue-700"
          >
            + Add Slide
          </button>
          <button
            data-testid="bulk-narration-btn"
            disabled
            title="Audio generation available in a future update"
            className="px-3 py-1.5 bg-gray-100 text-gray-400 text-sm rounded cursor-not-allowed"
          >
            Generate Narration
          </button>
        </div>
      </div>

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
    </div>
  )
}
