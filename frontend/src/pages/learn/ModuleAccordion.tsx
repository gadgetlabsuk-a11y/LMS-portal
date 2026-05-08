import { useState } from 'react'

interface Lesson {
  title?: string
}

interface Module {
  title?: string
  lessons?: Lesson[]
}

interface ModuleAccordionProps {
  module: Module
  index: number
  onLessonClick?: (lessonId: number) => void
}

export const ModuleAccordion = ({ module, index, onLessonClick }: ModuleAccordionProps) => {
  const [open, setOpen] = useState(index === 0)
  const lessons = module.lessons || []

  return (
    <div className="border border-gray-200 rounded-lg overflow-hidden">
      <button
        onClick={() => setOpen(o => !o)}
        className="w-full flex items-center justify-between px-4 py-3 bg-gray-50 hover:bg-gray-100 text-left"
      >
        <span className="font-medium text-gray-800 text-sm">{module.title || `Module ${index + 1}`}</span>
        <span className="text-gray-500 text-xs ml-2">{open ? '▲' : '▼'}</span>
      </button>
      {open && (
        <ul className="divide-y divide-gray-100">
          {lessons.map((lesson, li) => (
            <li
              key={li}
              className="px-6 py-2 text-sm text-gray-600 flex items-center gap-2"
              onClick={onLessonClick ? () => onLessonClick(li) : undefined}
            >
              <span className="text-gray-400">▶</span>
              {lesson.title || `Lesson ${li + 1}`}
            </li>
          ))}
          {lessons.length === 0 && (
            <li className="px-6 py-2 text-sm text-gray-400 italic">No lessons yet</li>
          )}
        </ul>
      )}
    </div>
  )
}
