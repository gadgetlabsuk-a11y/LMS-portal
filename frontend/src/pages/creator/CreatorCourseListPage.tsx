import { useEffect, useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { api } from '@/services/api'
import { Button } from '@/components/common/Button'
import { Badge } from '@/components/common/Badge'
import { CourseIdentityModal } from '@/components/course/CourseIdentityModal'
import { CourseStructureModal } from '@/components/course/CourseStructureModal'

interface Course {
  id: number
  title: string
  status: string
}

export function CreatorCourseListPage() {
  const navigate = useNavigate()
  const [courses, setCourses] = useState<Course[]>([])
  const [loading, setLoading] = useState(true)
  const [showIdentityModal, setShowIdentityModal] = useState(false)
  const [showStructureModal, setShowStructureModal] = useState(false)
  const [pendingCourseId, setPendingCourseId] = useState<number | null>(null)

  const fetchCourses = async () => {
    const res = await api.get('/courses')
    if (res.ok) {
      const data = await res.json()
      setCourses(Array.isArray(data) ? data : data.courses ?? [])
    }
    setLoading(false)
  }

  useEffect(() => {
    fetchCourses()
  }, [])

  const handleCourseCreated = (courseId: number) => {
    setPendingCourseId(courseId)
    setShowIdentityModal(false)
    setShowStructureModal(true)
    fetchCourses()
  }

  const handleStructureConfirmed = (courseId: number) => {
    setShowStructureModal(false)
    navigate(`/creator/courses/${courseId}/builder`)
  }

  const handleStructureClose = () => {
    setShowStructureModal(false)
  }

  const statusVariant = (status: string) => {
    if (status === 'published') return 'success'
    if (status === 'archived') return 'warning'
    return 'info'
  }

  return (
    <div style={{ padding: '32px' }}>
      {/* Header */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: '24px',
        }}
      >
        <h1 style={{ fontSize: '24px', fontWeight: 700, color: '#111827', margin: 0 }}>
          My Courses
        </h1>
        <Button variant="primary" onClick={() => setShowIdentityModal(true)}>
          + New Course
        </Button>
      </div>

      {/* Course list */}
      {loading ? (
        <p style={{ color: '#9ca3af' }}>Loading courses...</p>
      ) : courses.length === 0 ? (
        <div
          style={{
            textAlign: 'center',
            padding: '60px 20px',
            color: '#9ca3af',
            border: '2px dashed #e5e7eb',
            borderRadius: '12px',
          }}
        >
          <p style={{ fontSize: '16px', marginBottom: '12px' }}>No courses yet.</p>
          <Button variant="primary" onClick={() => setShowIdentityModal(true)}>
            Create your first course
          </Button>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          {courses.map(course => (
            <div
              key={course.id}
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '16px 20px',
                background: '#fff',
                border: '1px solid #e5e7eb',
                borderRadius: '10px',
                boxShadow: '0 1px 3px rgba(0,0,0,0.05)',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <span style={{ fontWeight: 600, color: '#111827' }}>{course.title}</span>
                <Badge variant={statusVariant(course.status)}>{course.status}</Badge>
              </div>
              <Link
                to={`/creator/courses/${course.id}/builder`}
                style={{ color: '#2563eb', fontSize: '14px', textDecoration: 'none' }}
              >
                Open Builder →
              </Link>
            </div>
          ))}
        </div>
      )}

      {/* Modals */}
      <CourseIdentityModal
        open={showIdentityModal}
        onClose={() => setShowIdentityModal(false)}
        onCreated={handleCourseCreated}
      />
      <CourseStructureModal
        open={showStructureModal}
        onClose={handleStructureClose}
        courseId={pendingCourseId}
        onConfirmed={handleStructureConfirmed}
      />
    </div>
  )
}
