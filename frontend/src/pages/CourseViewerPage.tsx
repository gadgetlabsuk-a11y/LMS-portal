import { useParams, useNavigate } from 'react-router-dom'
import { API_BASE } from '@/services/api'

export const CourseViewerPage = () => {
  const { id: courseId } = useParams<{ id: string }>()
  const navigate = useNavigate()

  return (
    <div className="min-h-screen flex flex-col bg-gray-900">
      <div className="bg-gray-800 px-6 py-3 flex items-center justify-between flex-shrink-0">
        <button
          onClick={() => navigate(-1)}
          className="text-gray-300 hover:text-white text-sm flex items-center gap-1"
        >
          ← Back
        </button>
        <span className="text-gray-400 text-xs">Course Player</span>
      </div>
      <iframe
        src={`${API_BASE}/api/courses/${courseId}/player`}
        className="flex-1 w-full border-0"
        style={{ minHeight: 'calc(100vh - 52px)' }}
        title="Course Player"
        allowFullScreen
      />
    </div>
  )
}
