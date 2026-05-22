import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '@/services/api'
import { safeDesc } from '@/utils/text'

interface Course {
  id: number
  title: string
  description?: string
  has_content: boolean
  created_at: string
}

const SkeletonCard = () => (
  <div className="bg-white rounded-lg shadow-sm border border-gray-100 overflow-hidden animate-pulse">
    <div className="h-32 bg-gray-200" />
    <div className="p-4 space-y-2">
      <div className="h-4 bg-gray-200 rounded w-3/4" />
      <div className="h-3 bg-gray-200 rounded w-full" />
      <div className="h-3 bg-gray-200 rounded w-2/3" />
    </div>
  </div>
)

export const LearnerCatalogue = () => {
  const [courses, setCourses] = useState<Course[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [searchInput, setSearchInput] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const navigate = useNavigate()

  useEffect(() => {
    const timer = setTimeout(() => setSearch(searchInput), 300)
    return () => clearTimeout(timer)
  }, [searchInput])

  useEffect(() => {
    setPage(1)
    setCourses([])
  }, [search])

  useEffect(() => {
    fetchCourses(page, search, page === 1)
  }, [page, search])

  const fetchCourses = async (p: number, q: string, replace: boolean) => {
    setLoading(true)
    setError('')
    try {
      const params = new URLSearchParams({ page: String(p), page_size: '20' })
      if (q) params.append('q', q)
      const res = await api.get(`/learn/courses?${params}`)
      if (!res.ok) throw new Error('Failed to load courses')
      const data = await res.json()
      setTotal(data.total)
      setCourses((prev: Course[]) => replace ? data.items : [...prev, ...data.items])
    } catch (_err) {
      setError('Could not load courses. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 mb-6">All Courses</h1>

      {/* Search */}
      <div className="mb-8">
        <input
          type="text"
          placeholder="Search courses..."
          value={searchInput}
          onChange={e => setSearchInput(e.target.value)}
          className="w-full max-w-xl px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
        />
      </div>

      {/* Error */}
      {error && (
        <div className="text-center py-12">
          <p className="text-red-500 mb-4">{error}</p>
          <button
            onClick={() => fetchCourses(1, search, true)}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm"
          >
            Try again
          </button>
        </div>
      )}

      {/* Course grid */}
      {!error && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {courses.map(course => (
            <div
              key={course.id}
              onClick={() => navigate(`/learn/${course.id}`)}
              className="bg-white rounded-lg shadow-sm hover:shadow-md transition-shadow duration-200 cursor-pointer overflow-hidden border border-gray-100"
            >
              <div className="h-32 bg-gradient-to-br from-blue-500 to-blue-700 flex items-center justify-center">
                <span className="text-white text-4xl">📚</span>
              </div>
              <div className="p-4">
                <h3 className="font-bold text-gray-900 text-sm mb-1 overflow-hidden" style={{ display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical' }}>
                  {course.title}
                </h3>
                <p className="text-gray-500 text-xs mb-3 overflow-hidden" style={{ display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical' }}>
                  {safeDesc(course.description, 100)}
                </p>
                <div className="flex items-center justify-between">
                  {course.has_content ? (
                    <span className="bg-green-100 text-green-700 text-xs px-2 py-0.5 rounded-full font-medium">
                      Content Ready
                    </span>
                  ) : <span />}
                  <span className="text-gray-400 text-xs">
                    {new Date(course.created_at).toLocaleDateString()}
                  </span>
                </div>
              </div>
            </div>
          ))}

          {/* Skeleton cards while loading */}
          {loading && [1, 2, 3].map(n => <SkeletonCard key={n} />)}
        </div>
      )}

      {/* Empty state */}
      {!loading && !error && courses.length === 0 && (
        <div className="text-center py-24">
          <div className="text-6xl mb-4">📭</div>
          <p className="text-gray-500 text-lg">No courses available yet.</p>
        </div>
      )}

      {/* Load more */}
      {!loading && !error && courses.length < total && (
        <div className="text-center mt-10">
          <button
            onClick={() => setPage(p => p + 1)}
            className="px-6 py-2 border border-gray-300 rounded-lg text-sm text-gray-700 hover:bg-gray-50"
          >
            Load more
          </button>
        </div>
      )}
    </div>
  )
}
