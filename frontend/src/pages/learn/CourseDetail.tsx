import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { api } from '@/services/api'
import { ModuleAccordion } from '@/pages/learn/ModuleAccordion'

interface Lesson {
  title?: string
}

interface Module {
  title?: string
  lessons?: Lesson[]
}

interface CourseContent {
  modules?: Module[]
}

interface Course {
  id: number
  title: string
  description?: string
  has_content: boolean
  content?: CourseContent
}

export const CourseDetail = () => {
  const { id: courseId } = useParams<{ id: string }>()
  const [course, setCourse] = useState<Course | null>(null)
  const [loading, setLoading] = useState(true)
  const [notFound, setNotFound] = useState(false)
  const navigate = useNavigate()

  useEffect(() => {
    fetchCourse()
  }, [courseId])

  const fetchCourse = async () => {
    setLoading(true)
    setNotFound(false)
    try {
      const res = await api.get(`/learn/courses/${courseId}`)
      if (res.status === 404) { setNotFound(true); return }
      if (!res.ok) throw new Error('Failed to load course')
      setCourse(await res.json())
    } catch (_err) {
      setNotFound(true)
    } finally {
      setLoading(false)
    }
  }

  if (loading) return (
    <div className="flex items-center justify-center py-24">
      <div className="spin text-4xl">⏳</div>
    </div>
  )

  if (notFound) return (
    <div className="text-center py-24">
      <div className="text-6xl mb-4">🔍</div>
      <p className="text-gray-600 text-lg mb-4">Course not found.</p>
      <button onClick={() => navigate('/learn')} className="text-blue-600 hover:underline text-sm">
        ← Back to Courses
      </button>
    </div>
  )

  const modules = course!.content?.modules || []

  return (
    <div>
      {/* Back link */}
      <button
        onClick={() => navigate('/learn')}
        className="text-blue-600 hover:underline text-sm mb-6 flex items-center gap-1"
      >
        ← Back to Courses
      </button>

      <div className="lg:grid lg:grid-cols-3 lg:gap-8">
        {/* Main content */}
        <div className="lg:col-span-2">
          <h1 className="text-3xl font-bold text-gray-900 mb-4">{course!.title}</h1>
          {course!.description && (
            <p className="text-gray-600 text-base mb-8 leading-relaxed">
              {course!.description}
            </p>
          )}

          {/* Module accordion */}
          {modules.length > 0 ? (
            <div>
              <h2 className="text-xl font-semibold text-gray-800 mb-4">Course Content</h2>
              <div className="space-y-2">
                {modules.map((mod, mi) => (
                  <ModuleAccordion key={mi} module={mod} index={mi} />
                ))}
              </div>
            </div>
          ) : (
            <div className="bg-gray-50 rounded-lg p-8 text-center">
              <p className="text-gray-500">Course content coming soon.</p>
            </div>
          )}
        </div>

        {/* Sticky side panel */}
        <div className="mt-8 lg:mt-0">
          <div className="lg:sticky lg:top-20 bg-white rounded-lg shadow-md border border-gray-100 p-6">
            <p className="text-gray-500 text-sm mb-4">
              {modules.length > 0
                ? `${modules.length} module${modules.length > 1 ? 's' : ''}`
                : 'No modules yet'}
            </p>
            <button
              onClick={() => course!.has_content ? navigate(`/courses/${course!.id}`) : undefined}
              disabled={!course!.has_content}
              title={!course!.has_content ? 'No content yet' : ''}
              className={`w-full py-3 px-6 rounded-lg font-bold text-white text-base transition-all ${
                course!.has_content
                  ? 'bg-blue-600 hover:bg-blue-700 cursor-pointer'
                  : 'bg-gray-300 cursor-not-allowed'
              }`}
            >
              {course!.has_content ? '▶ Start Course' : 'No content yet'}
            </button>
            <button
              onClick={() => navigate(`/learn/${course!.id}/broadcast`)}
              className="w-full mt-3 py-3 px-6 rounded-lg font-bold text-white text-base bg-indigo-600 hover:bg-indigo-700 cursor-pointer transition-all"
            >
              🎙️ Launch Broadcast
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
