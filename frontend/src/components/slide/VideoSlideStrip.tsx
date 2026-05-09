import React from 'react'
import {
  DndContext,
  closestCenter,
  DragEndEvent,
  KeyboardSensor,
  PointerSensor,
  useSensors,
  useSensor,
} from '@dnd-kit/core'
import {
  SortableContext,
  verticalListSortingStrategy,
  arrayMove,
  useSortable,
} from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import { useNavigate } from 'react-router-dom'
import { api } from '@/services/api'

interface Slide {
  id: number
  video_id: number
  title: string
  narration_script: string | null
  order_index: number
}

interface Props {
  slides: Slide[]
  videoId: number
  courseId: number
  onSlidesChange: (slides: Slide[]) => void
}

function SortableSlideThumb({
  slide,
  courseId,
  videoId,
  onDuplicate,
  onDelete,
}: {
  slide: Slide
  courseId: number
  videoId: number
  onDuplicate: (slide: Slide) => void
  onDelete: (id: number) => void
}) {
  const { attributes, listeners, setNodeRef, transform, transition } = useSortable({ id: slide.id })
  const navigate = useNavigate()
  const style = { transform: CSS.Transform.toString(transform), transition }

  return (
    <div
      ref={setNodeRef}
      style={style}
      data-testid={`slide-thumb-${slide.id}`}
      className="flex items-center gap-2 p-3 bg-white border rounded-lg cursor-pointer hover:border-blue-400 group"
    >
      <div {...attributes} {...listeners} className="cursor-grab text-gray-400 select-none">
        ⠿
      </div>
      <div
        className="flex-1 min-w-0"
        onClick={() =>
          navigate(`/creator/courses/${courseId}/videos/${videoId}/slides/${slide.id}/editor`)
        }
      >
        <p className="text-sm font-medium truncate">{slide.title || `Slide ${slide.order_index + 1}`}</p>
        {slide.narration_script && (
          <p className="text-xs text-green-600 truncate">Script written</p>
        )}
      </div>
      <div className="flex gap-1 opacity-0 group-hover:opacity-100">
        <button
          data-testid={`duplicate-slide-${slide.id}`}
          onClick={(e) => {
            e.stopPropagation()
            onDuplicate(slide)
          }}
          className="text-xs px-2 py-1 text-gray-600 hover:text-blue-600"
          title="Duplicate slide"
        >
          ⧉
        </button>
        <button
          data-testid={`delete-slide-${slide.id}`}
          onClick={(e) => {
            e.stopPropagation()
            onDelete(slide.id)
          }}
          className="text-xs px-2 py-1 text-gray-600 hover:text-red-600"
          title="Delete slide"
        >
          ✕
        </button>
      </div>
    </div>
  )
}

export function VideoSlideStrip({ slides, videoId, courseId, onSlidesChange }: Props) {
  const sensors = useSensors(useSensor(PointerSensor), useSensor(KeyboardSensor))

  const handleDragEnd = async (event: DragEndEvent) => {
    const { active, over } = event
    if (!over || active.id === over.id) return
    const oldIndex = slides.findIndex((s) => s.id === active.id)
    const newIndex = slides.findIndex((s) => s.id === over.id)
    const newOrder = arrayMove(slides, oldIndex, newIndex)
    onSlidesChange(newOrder)
    await api.post(`/videos/${videoId}/slides/reorder`, {
      slide_ids: newOrder.map((s) => s.id),
    })
  }

  const handleDuplicate = async (slide: Slide) => {
    const res = await api.post(`/videos/${videoId}/slides`, {
      title: `${slide.title} (copy)`,
      narration_script: slide.narration_script,
      order_index: slides.length,
    })
    const newSlide = await res.json()
    onSlidesChange([...slides, newSlide])
  }

  const handleDelete = async (id: number) => {
    await api.delete(`/slides/${id}`)
    onSlidesChange(slides.filter((s) => s.id !== id))
  }

  return (
    <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
      <SortableContext items={slides.map((s) => s.id)} strategy={verticalListSortingStrategy}>
        <div className="flex flex-col gap-2">
          {slides.map((slide) => (
            <SortableSlideThumb
              key={slide.id}
              slide={slide}
              courseId={courseId}
              videoId={videoId}
              onDuplicate={handleDuplicate}
              onDelete={handleDelete}
            />
          ))}
        </div>
      </SortableContext>
    </DndContext>
  )
}
