import { useSortable } from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'

interface SortableQuestionRowProps {
  id: number
  children: React.ReactNode
}

export function SortableQuestionRow({ id, children }: SortableQuestionRowProps) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id })

  return (
    <div
      ref={setNodeRef}
      style={{
        transform: CSS.Transform.toString(transform),
        transition,
        opacity: isDragging ? 0.5 : 1,
        position: 'relative',
      }}
    >
      {/* Drag handle — separate from interactive content so clicks on buttons/inputs don't drag */}
      <button
        data-testid={`drag-handle-${id}`}
        {...attributes}
        {...listeners}
        style={{
          position: 'absolute', left: '-24px', top: '50%', transform: 'translateY(-50%)',
          background: 'none', border: 'none', cursor: 'grab', color: '#9ca3af', fontSize: '16px',
          padding: '4px', lineHeight: 1,
        }}
        aria-label="Drag to reorder"
      >
        ⠿
      </button>
      {children}
    </div>
  )
}
