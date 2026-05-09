import {
  DndContext, closestCenter, KeyboardSensor, PointerSensor,
  useSensor, useSensors,
} from '@dnd-kit/core'
import type { DragEndEvent } from '@dnd-kit/core'
import {
  SortableContext, sortableKeyboardCoordinates, verticalListSortingStrategy,
  useSortable, arrayMove,
} from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import { Badge } from '@/components/common/Badge'
import { api } from '@/services/api'
import type { BuilderModule as Module, BuilderVideo as Video, BuilderQuiz as Quiz } from './types'

interface ModuleOverviewListProps {
  courseId: number
  modules: Module[]
  videos: Record<number, Video[]>
  quizzes: Record<number, Quiz[]>
  onModulesReorder: (reordered: Module[]) => void
  onVideosReorder: (moduleId: number, reordered: Video[]) => void
}

function SortableVideoRow({
  video,
  statusVariant,
}: {
  video: Video
  statusVariant: (s: string | null) => 'success' | 'info'
}) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } =
    useSortable({ id: `video-${video.id}` })
  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  }

  return (
    <div ref={setNodeRef} style={style} data-testid="sortable-video-row">
      <div
        style={{
          display: 'flex', alignItems: 'center', gap: '8px',
          padding: '8px 12px', background: 'white',
          border: '1px solid #f3f4f6', borderRadius: '6px', marginBottom: '2px',
        }}
      >
        <span
          {...attributes}
          {...listeners}
          data-testid="video-drag-handle"
          style={{ cursor: 'grab', color: '#d1d5db', fontSize: '14px', userSelect: 'none' }}
        >
          ⠿
        </span>
        <span style={{ flex: 1, fontSize: '13px', color: '#374151' }}>{video.title}</span>
        <Badge variant={statusVariant(video.status)}>
          {video.status || 'draft'}
        </Badge>
      </div>
    </div>
  )
}

function SortableModuleRow({
  module, courseId, videos, quizzes, onVideosReorder,
}: {
  module: Module
  courseId: number
  videos: Video[]
  quizzes: Quiz[]
  onVideosReorder: (moduleId: number, reordered: Video[]) => void
}) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } =
    useSortable({ id: `module-${module.id}` })
  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  }

  // Per-module video sensors — separate DndContext per module prevents cross-module drag
  const videoSensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 8 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }),
  )

  const handleVideoDragEnd = async (event: DragEndEvent) => {
    const { active, over } = event
    if (!over || active.id === over.id) return
    const oldIdx = videos.findIndex((v) => `video-${v.id}` === active.id)
    const newIdx = videos.findIndex((v) => `video-${v.id}` === over.id)
    if (oldIdx === -1 || newIdx === -1) return
    const reordered = arrayMove(videos, oldIdx, newIdx)
    onVideosReorder(module.id, reordered)
    await api.post(`/modules/${module.id}/videos/reorder`, {
      video_ids: reordered.map((v) => v.id),
    })
  }

  const statusVariant = (status: string | null): 'success' | 'info' =>
    status === 'published' ? 'success' : 'info'

  // courseId is used by parent caller; suppress unused-var lint
  void courseId

  return (
    <div ref={setNodeRef} style={style} data-testid="sortable-module-row">
      {/* Module header row */}
      <div
        style={{
          display: 'flex', alignItems: 'center', gap: '10px',
          padding: '12px 16px', background: 'white',
          border: '1px solid #e5e7eb', borderRadius: '8px', marginBottom: '4px',
        }}
      >
        {/* Drag handle */}
        <span
          {...attributes}
          {...listeners}
          data-testid="module-drag-handle"
          style={{ cursor: 'grab', color: '#9ca3af', fontSize: '16px', userSelect: 'none' }}
          title="Drag to reorder"
        >
          ⠿
        </span>
        <span style={{ flex: 1, fontWeight: 600, fontSize: '14px', color: '#111827' }}>
          {module.title}
        </span>
        <Badge variant={statusVariant(module.status)}>
          {module.status || 'draft'}
        </Badge>
      </div>

      {/* Videos under this module — separate DndContext (scoped to module) */}
      {videos.length > 0 && (
        <DndContext
          sensors={videoSensors}
          collisionDetection={closestCenter}
          onDragEnd={handleVideoDragEnd}
        >
          <SortableContext
            items={videos.map((v) => `video-${v.id}`)}
            strategy={verticalListSortingStrategy}
          >
            <div style={{ paddingLeft: '28px', marginBottom: '4px' }}>
              {videos.map((vid) => (
                <SortableVideoRow key={vid.id} video={vid} statusVariant={statusVariant} />
              ))}
            </div>
          </SortableContext>
        </DndContext>
      )}

      {/* Quizzes — non-draggable (Phase 16) */}
      {(quizzes || []).length > 0 && (
        <div style={{ paddingLeft: '28px', marginBottom: '8px' }}>
          {quizzes.map((quiz) => (
            <div
              key={quiz.id}
              data-testid="quiz-non-draggable-row"
              style={{
                display: 'flex', alignItems: 'center', gap: '8px',
                padding: '6px 12px', background: '#f3f4f6',
                border: '1px dashed #d1d5db', borderRadius: '6px', marginBottom: '2px',
              }}
            >
              <span style={{ fontSize: '11px', color: '#9ca3af' }}>Quiz</span>
              <span style={{ fontSize: '13px', color: '#6b7280' }}>{quiz.title}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export function ModuleOverviewList({
  courseId, modules, videos, quizzes, onModulesReorder, onVideosReorder,
}: ModuleOverviewListProps) {
  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 8 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }),
  )

  const handleModuleDragEnd = async (event: DragEndEvent) => {
    const { active, over } = event
    if (!over || active.id === over.id) return
    const oldIdx = modules.findIndex((m) => `module-${m.id}` === active.id)
    const newIdx = modules.findIndex((m) => `module-${m.id}` === over.id)
    if (oldIdx === -1 || newIdx === -1) return
    const reordered = arrayMove(modules, oldIdx, newIdx)
    onModulesReorder(reordered) // optimistic update in parent
    await api.post(`/courses/${courseId}/modules/reorder`, {
      module_ids: reordered.map((m) => m.id),
    })
  }

  return (
    <div data-testid="module-overview-list">
      {modules.length === 0 && (
        <p style={{ color: '#9ca3af', textAlign: 'center', marginTop: '48px' }}>
          No modules yet. Use the Course Structure wizard to scaffold modules.
        </p>
      )}
      <DndContext
        sensors={sensors}
        collisionDetection={closestCenter}
        onDragEnd={handleModuleDragEnd}
      >
        <SortableContext
          items={modules.map((m) => `module-${m.id}`)}
          strategy={verticalListSortingStrategy}
        >
          {modules.map((mod) => (
            <SortableModuleRow
              key={mod.id}
              module={mod}
              courseId={courseId}
              videos={videos[mod.id] || []}
              quizzes={quizzes[mod.id] || []}
              onVideosReorder={onVideosReorder}
            />
          ))}
        </SortableContext>
      </DndContext>
    </div>
  )
}
