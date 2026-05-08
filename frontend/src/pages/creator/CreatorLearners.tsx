import { useState, useEffect, useCallback } from 'react'
import { api } from '@/services/api'
import { Card } from '@/components/common/Card'

interface Course {
  id: number
  title: string
}

interface Learner {
  email: string
  course_id: number
  learner_name: string
  course_title: string
  enrolled_at: string
}

export const CreatorLearners = () => {
  const [learners, setLearners] = useState<Learner[]>([])
  const [courses, setCourses] = useState<Course[]>([])
  const [selectedCourse, setSelectedCourse] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    fetchCourses()
  }, [])

  const fetchLearners = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const path = '/creator/learners' + (selectedCourse ? `?course_id=${selectedCourse}` : '')
      const res = await api.get(path)
      if (res.ok) {
        setLearners(await res.json())
      } else {
        setError('Could not load learners.')
      }
    } catch (_err) {
      setError('Could not load learners. Please try again.')
    } finally {
      setLoading(false)
    }
  }, [selectedCourse])

  useEffect(() => {
    fetchLearners()
  }, [fetchLearners])

  const fetchCourses = async () => {
    try {
      const res = await api.get('/courses')
      if (res.ok) {
        const d = await res.json()
        setCourses(Array.isArray(d) ? d : d.items || [])
      } else {
        console.error('Failed to load courses list')
      }
    } catch (err) {
      console.error('Failed to load courses', err)
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-4">
        <select
          value={selectedCourse}
          onChange={e => setSelectedCourse(e.target.value)}
          className="border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value="">All Courses</option>
          {courses.map(c => (
            <option key={c.id} value={c.id}>{c.title}</option>
          ))}
        </select>
      </div>

      {loading ? (
        <div className="text-center py-12"><div className="spin text-4xl inline-block">⏳</div></div>
      ) : error ? (
        <div className="text-center py-12">
          <p className="text-red-600 mb-4">{error}</p>
          <button onClick={fetchLearners} className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700">Retry</button>
        </div>
      ) : learners.length === 0 ? (
        <Card className="p-12 text-center">
          <p className="text-4xl mb-3">👥</p>
          <p className="text-gray-600">No learners enrolled yet.</p>
        </Card>
      ) : (
        <Card className="overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b">
              <tr className="text-left text-gray-500">
                <th className="px-4 py-3 font-medium">Learner</th>
                <th className="px-4 py-3 font-medium">Email</th>
                <th className="px-4 py-3 font-medium">Course</th>
                <th className="px-4 py-3 font-medium">Enrolled</th>
              </tr>
            </thead>
            <tbody>
              {learners.map((l) => (
                <tr key={`${l.email}-${l.course_id}`} className="border-b last:border-0 hover:bg-gray-50">
                  <td className="px-4 py-3 font-medium text-gray-900">{l.learner_name}</td>
                  <td className="px-4 py-3 text-gray-600">{l.email}</td>
                  <td className="px-4 py-3 text-gray-700">{l.course_title}</td>
                  <td className="px-4 py-3 text-gray-500">{new Date(l.enrolled_at).toLocaleDateString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}
    </div>
  )
}
