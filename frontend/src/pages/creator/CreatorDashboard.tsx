import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '@/services/api'
import { useAuth } from '@/context/AuthContext'
import { Card } from '@/components/common/Card'

interface CreatorStats {
  total_courses: number | null
  published_courses: number | null
  draft_courses: number | null
  total_enrollments: number | null
}

interface Course {
  id: number
  title: string
  status: string
}

interface StatCardProps {
  title: string
  value: number | null | undefined
  icon: string
}

const StatCard = ({ title, value, icon }: StatCardProps) => (
  <Card className="p-6">
    <div className="flex items-center justify-between">
      <div>
        <p className="text-gray-600 text-sm">{title}</p>
        <p className="text-3xl font-bold mt-2">{value ?? '—'}</p>
      </div>
      <div className="text-4xl">{icon}</div>
    </div>
  </Card>
)

export const CreatorDashboard = () => {
  const [stats, setStats] = useState<CreatorStats | null>(null)
  const [recentCourses, setRecentCourses] = useState<Course[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const { user } = useAuth()
  const navigate = useNavigate()

  useEffect(() => {
    fetchDashboard()
  }, [])

  const fetchDashboard = async () => {
    setLoading(true)
    setError('')
    try {
      const [statsRes, coursesRes] = await Promise.all([
        api.get('/creator/stats'),
        api.get('/courses'),
      ])
      if (statsRes.ok) setStats(await statsRes.json())
      else setError('Could not load stats.')
      if (coursesRes.ok) {
        const d = await coursesRes.json()
        const list: Course[] = Array.isArray(d) ? d : d.items || []
        setRecentCourses(list.slice(0, 5))
      } else if (!error) {
        setError('Could not load courses.')
      }
    } catch (_err) {
      setError('Could not load dashboard. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return <div className="text-center py-12"><div className="spin text-4xl inline-block">⏳</div></div>
  }

  if (error) {
    return (
      <div className="text-center py-12">
        <p className="text-red-600 mb-4">{error}</p>
        <button onClick={fetchDashboard} className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700">
          Retry
        </button>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="bg-indigo-50 border-l-4 border-indigo-500 p-4 rounded">
        <p className="text-lg font-semibold">Welcome, {user?.username}! 👋</p>
        <p className="text-gray-600 text-sm mt-1">Here's an overview of your courses and learners.</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard title="Total Courses" value={stats?.total_courses} icon="📚" />
        <StatCard title="Published" value={stats?.published_courses} icon="✅" />
        <StatCard title="Drafts" value={stats?.draft_courses} icon="📝" />
        <StatCard title="Total Enrollments" value={stats?.total_enrollments} icon="👥" />
      </div>

      <Card className="p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold">Recent Courses</h3>
          <button
            onClick={() => navigate('/creator/courses')}
            className="text-sm text-blue-600 hover:underline"
          >
            View all →
          </button>
        </div>
        {recentCourses.length === 0 ? (
          <p className="text-gray-500 text-sm">No courses yet. <button onClick={() => navigate('/creator/courses')} className="text-blue-600 hover:underline">Create your first course →</button></p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-gray-500 border-b">
                <th className="pb-2 font-medium">Title</th>
                <th className="pb-2 font-medium">Status</th>
                <th className="pb-2 font-medium"></th>
              </tr>
            </thead>
            <tbody>
              {recentCourses.map(c => (
                <tr key={c.id} className="border-b last:border-0">
                  <td className="py-2 font-medium text-gray-900">{c.title}</td>
                  <td className="py-2">
                    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${c.status === 'published' ? 'bg-green-100 text-green-700' : 'bg-yellow-100 text-yellow-700'}`}>
                      {c.status}
                    </span>
                  </td>
                  <td className="py-2 text-right">
                    <button
                      onClick={() => navigate('/creator/courses')}
                      className="text-blue-600 hover:underline text-xs"
                    >
                      Edit
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>
    </div>
  )
}
