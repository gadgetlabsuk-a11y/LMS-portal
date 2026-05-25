import { useState, useEffect } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { api } from '@/services/api'
import { useToast } from '@/context/ToastContext'
import { safeDesc } from '@/utils/text'
import { Button } from '@/components/common/Button'
import { Card } from '@/components/common/Card'
import { Badge } from '@/components/common/Badge'
import { CourseIdentityModal } from '@/components/course/CourseIdentityModal'
import { CourseStructureModal } from '@/components/course/CourseStructureModal'
import { GenerateFromContentWizard } from '@/components/generate/GenerateFromContentWizard'

const API_BASE = import.meta.env.PROD ? '/lms' : ''

interface Course {
  id: string
  title: string
  description: string
  status: string
  creator_id: string
  created_at: string
  enrollment_count?: number
  has_content?: boolean
  content?: string | null
}

export const CourseManagementPage = () => {
  const navigate = useNavigate()
  const [courses, setCourses] = useState<Course[]>([])
  const [loading, setLoading] = useState(true)
  const [showIdentityModal, setShowIdentityModal] = useState(false)
  const [showStructureModal, setShowStructureModal] = useState(false)
  const [pendingCourseId, setPendingCourseId] = useState<number | null>(null)
  const [showGenerateWizard, setShowGenerateWizard] = useState(false)
  const { showToast } = useToast()

  useEffect(() => {
    fetchCourses()
  }, [])

  const fetchCourses = async () => {
    setLoading(true)
    try {
      const res = await api.get('/courses')
      if (res.ok) {
        const d = await res.json()
        setCourses(Array.isArray(d) ? d : d.items || [])
      }
    } catch (err) {
      showToast('Failed to load courses', 'error')
    } finally {
      setLoading(false)
    }
  }

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

  const handleStructureClose = () => setShowStructureModal(false)

  const handlePublish = async (courseId: string) => {
    try {
      const res = await api.put(`/courses/${courseId}`, { status: 'published' })
      if (res.ok) {
        showToast('Course published', 'success')
        fetchCourses()
      } else {
        showToast('Failed to publish course', 'error')
      }
    } catch (err) {
      showToast((err as Error).message, 'error')
    }
  }

  const handleDelete = async (courseId: string) => {
    if (confirm('Are you sure you want to delete this course?')) {
      try {
        const res = await api.delete(`/courses/${courseId}`)
        if (res.ok) {
          showToast('Course deleted', 'success')
          fetchCourses()
        } else {
          showToast('Failed to delete course', 'error')
        }
      } catch (err) {
        showToast((err as Error).message, 'error')
      }
    }
  }

  const handleDownload = async (courseId: string, type: string, courseTitle: string) => {
    try {
      const endpoint = type === 'script' ? 'generate-script' : 'generate-slides'
      const ext = type === 'script' ? 'docx' : 'pptx'
      const res = await fetch(`${API_BASE}/api/courses/${courseId}/${endpoint}`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` },
      })
      if (!res.ok) {
        showToast(`Failed to generate ${type}`, 'error')
        return
      }
      const blob = await res.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${courseTitle}_${type}.${ext}`
      a.click()
      URL.revokeObjectURL(url)
      showToast(`${type === 'script' ? 'Script' : 'Slides'} downloaded!`, 'success')
    } catch (err) {
      showToast(`Error: ${(err as Error).message}`, 'error')
    }
  }

  const handleGenerateVoiceover = async (courseId: string) => {
    showToast('Generating voiceover — this may take a minute...', 'success')
    try {
      const res = await fetch(`${API_BASE}/api/courses/${courseId}/generate-voiceover`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` },
      })
      if (res.ok) {
        showToast('Voiceover generated!', 'success')
      } else {
        const err = await res.json()
        showToast(err.detail || 'Voiceover generation failed', 'error')
      }
    } catch (err) {
      showToast(`Error: ${(err as Error).message}`, 'error')
    }
  }

  const handleViewPlayer = (courseId: string) => {
    window.open(`${API_BASE}/api/courses/${courseId}/player`, '_blank')
  }

  return (
    <div className="space-y-6">
      <div className="flex gap-4">
        <Button variant="secondary" onClick={() => setShowGenerateWizard(true)}>
          ✨ Generate with AI
        </Button>
        <Button onClick={() => setShowIdentityModal(true)}>
          📚 New Course
        </Button>
      </div>

      {loading ? (
        <div className="text-center py-12"><div className="spin text-4xl inline-block">⏳</div></div>
      ) : courses.length === 0 ? (
        <Card className="p-12 text-center">
          <p className="text-gray-600 text-lg">No courses yet. Create one to get started!</p>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {courses.map(course => (
            <Card key={course.id} className="p-6 flex flex-col h-full">
              <div className="flex-1">
                <div className="flex justify-between items-start mb-2">
                  <h3 className="font-bold text-lg flex-1">{course.title}</h3>
                  <Badge variant={course.status === 'published' ? 'success' : 'warning'}>
                    {course.status}
                  </Badge>
                </div>
                <p className="text-gray-600 text-sm mb-3">{safeDesc(course.description)}</p>
                <div className="text-xs text-gray-500 space-y-1">
                  <p>Creator: {course.creator_id}</p>
                  <p>Created: {new Date(course.created_at).toLocaleDateString()}</p>
                  <p>Enrollments: {course.enrollment_count || 0}</p>
                </div>
              </div>
              <div className="mt-4 pt-4 border-t space-y-2">
                <Link
                  to={`/creator/courses/${course.id}/builder`}
                  className="block w-full text-center text-sm font-medium text-blue-600 hover:text-blue-800 py-1"
                >
                  Open Builder →
                </Link>
                {course.status !== 'published' && (
                  <Button size="sm" fullWidth onClick={() => handlePublish(course.id)}>
                    Publish
                  </Button>
                )}
                {(course.has_content || course.content) && (
                  <>
                    <Button size="sm" variant="secondary" fullWidth onClick={() => handleDownload(course.id, 'script', course.title)}>
                      📝 Script
                    </Button>
                    <Button size="sm" variant="secondary" fullWidth onClick={() => handleDownload(course.id, 'slides', course.title)}>
                      📊 Slides
                    </Button>
                    <Button size="sm" variant="secondary" fullWidth onClick={() => handleGenerateVoiceover(course.id)}>
                      🎙️ Voiceover
                    </Button>
                    <Button size="sm" variant="secondary" fullWidth onClick={() => handleViewPlayer(course.id)}>
                      🎬 View Course
                    </Button>
                  </>
                )}
                <Button size="sm" variant="danger" fullWidth onClick={() => handleDelete(course.id)}>
                  Delete
                </Button>
              </div>
            </Card>
          ))}
        </div>
      )}

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
      <GenerateFromContentWizard
        open={showGenerateWizard}
        onClose={() => setShowGenerateWizard(false)}
        onCreated={(courseId) => {
          setShowGenerateWizard(false)
          navigate(`/creator/courses/${courseId}/builder`)
        }}
      />
    </div>
  )
}
