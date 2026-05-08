import { useState, useEffect, useRef } from 'react'
import { api } from '@/services/api'
import { useToast } from '@/context/ToastContext'
import { safeDesc } from '@/utils/text'
import { Modal } from '@/components/common/Modal'
import { Button } from '@/components/common/Button'
import { Card } from '@/components/common/Card'
import { Badge } from '@/components/common/Badge'
import { Input } from '@/components/common/Input'
import { Select } from '@/components/common/Select'
import { Textarea } from '@/components/common/Textarea'

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

interface CourseFormData {
  title: string
  description: string
}

interface AiData {
  topic: string
  num_modules: number
  difficulty: string
  additional_instructions: string
}

interface WizardParams {
  videos_per_module: number
  video_duration: string
  tone: string
  target_audience: string
  include_assessment: boolean
}

export const CourseManagementPage = () => {
  const [courses, setCourses] = useState<Course[]>([])
  const [loading, setLoading] = useState(true)
  const [modalOpen, setModalOpen] = useState(false)
  const [aiModalOpen, setAiModalOpen] = useState(false)
  const [formData, setFormData] = useState<CourseFormData>({ title: '', description: '' })
  const [aiData, setAiData] = useState<AiData>({ topic: '', num_modules: 5, difficulty: 'intermediate', additional_instructions: '' })
  const [formError, setFormError] = useState('')
  const [aiMode, setAiMode] = useState('document')
  const [uploadedFile, setUploadedFile] = useState<File | null>(null)
  const [docDifficulty, setDocDifficulty] = useState('intermediate')
  const [docInstructions, setDocInstructions] = useState('')
  const [generating, setGenerating] = useState(false)
  const [wizardStep, setWizardStep] = useState(1)
  const [wizardParams, setWizardParams] = useState<WizardParams>({
    videos_per_module: 1,
    video_duration: 'medium',
    tone: 'formal',
    target_audience: 'general',
    include_assessment: true,
  })
  const fileInputRef = useRef<HTMLInputElement>(null)
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

  const handleCreateCourse = async () => {
    setFormError('')
    if (!formData.title || !formData.description) {
      setFormError('Please fill all fields')
      return
    }

    try {
      const res = await api.post('/courses', formData)
      if (res.ok) {
        showToast('Course created', 'success')
        setModalOpen(false)
        setFormData({ title: '', description: '' })
        fetchCourses()
      } else {
        const err = await res.json()
        setFormError(err.detail || 'Failed to create course')
      }
    } catch (err) {
      setFormError((err as Error).message)
    }
  }

  const handleGenerateCourse = async () => {
    setFormError('')

    if (wizardStep === 1) {
      if (aiMode === 'document' && !uploadedFile) {
        setFormError('Please select a file')
        return
      }
      if (aiMode === 'topic' && !aiData.topic) {
        setFormError('Please enter a topic')
        return
      }
      setWizardStep(2)
      return
    }

    setGenerating(true)

    try {
      if (aiMode === 'document') {
        const fd = new FormData()
        fd.append('file', uploadedFile!)
        fd.append('difficulty', docDifficulty)
        if (docInstructions) fd.append('additional_instructions', docInstructions)
        fd.append('videos_per_module', String(wizardParams.videos_per_module))
        fd.append('video_duration', wizardParams.video_duration)
        fd.append('tone', wizardParams.tone)
        fd.append('target_audience', wizardParams.target_audience)
        fd.append('include_assessment', String(wizardParams.include_assessment))

        const res = await fetch(`${API_BASE}/api/courses/generate-from-document`, {
          method: 'POST',
          headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` },
          body: fd,
        })

        if (res.ok) {
          showToast('Course generated from document!', 'success')
          setAiModalOpen(false)
          setUploadedFile(null)
          setDocDifficulty('intermediate')
          setDocInstructions('')
          setWizardStep(1)
          setWizardParams({
            videos_per_module: 1,
            video_duration: 'medium',
            tone: 'formal',
            target_audience: 'general',
            include_assessment: true,
          })
          fetchCourses()
        } else {
          const err = await res.json()
          setFormError(err.detail || 'Failed to generate course from document')
        }
      } else {
        const res = await api.post('/courses/generate', { ...aiData, ...wizardParams })
        if (res.ok) {
          showToast('Course generated! Check your courses list.', 'success')
          setAiModalOpen(false)
          setAiData({ topic: '', num_modules: 5, difficulty: 'intermediate', additional_instructions: '' })
          setWizardStep(1)
          setWizardParams({
            videos_per_module: 1,
            video_duration: 'medium',
            tone: 'formal',
            target_audience: 'general',
            include_assessment: true,
          })
          fetchCourses()
        } else {
          const err = await res.json()
          setFormError(err.detail || 'Failed to generate course')
        }
      }
    } catch (err) {
      setFormError((err as Error).message)
    } finally {
      setGenerating(false)
    }
  }

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
        <Button onClick={() => setModalOpen(true)}>
          📚 New Course
        </Button>
        <Button variant="secondary" onClick={() => setAiModalOpen(true)}>
          ✨ Generate with AI
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

      <Modal open={modalOpen} onClose={() => setModalOpen(false)} title="Create Course">
        <div className="space-y-4">
          <Input
            label="Title"
            value={formData.title}
            onChange={(e) => setFormData({ ...formData, title: e.target.value })}
            placeholder="Course title"
          />
          <Textarea
            label="Description"
            value={formData.description}
            onChange={(e) => setFormData({ ...formData, description: e.target.value })}
            placeholder="Course description"
            rows={4}
          />
          {formError && (
            <div className="p-3 bg-red-50 border border-red-200 rounded text-red-700 text-sm">
              {formError}
            </div>
          )}
          <div className="flex gap-2 justify-end">
            <Button variant="secondary" onClick={() => setModalOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleCreateCourse}>
              Create
            </Button>
          </div>
        </div>
      </Modal>

      <Modal open={aiModalOpen} onClose={() => {
        setAiModalOpen(false)
        setWizardStep(1)
        setWizardParams({
          videos_per_module: 1,
          video_duration: 'medium',
          tone: 'formal',
          target_audience: 'general',
          include_assessment: true,
        })
      }} title={wizardStep === 1 ? 'Generate Course with AI' : 'Customise Your Course'}>
        <div className="space-y-4">
          {wizardStep === 2 && (
            <button
              onClick={() => setWizardStep(1)}
              className="text-gray-500 hover:text-gray-700 text-sm font-medium mb-4"
            >
              ← Back
            </button>
          )}
          {wizardStep === 1 && (
            <>
              {/* Tab Toggle */}
              <div className="flex gap-2">
                <button
                  onClick={() => setAiMode('document')}
                  className={`px-4 py-2 rounded font-medium transition-colors ${
                    aiMode === 'document'
                      ? 'bg-blue-500 text-white'
                      : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                  }`}
                >
                  From Document
                </button>
                <button
                  onClick={() => setAiMode('topic')}
                  className={`px-4 py-2 rounded font-medium transition-colors ${
                    aiMode === 'topic'
                      ? 'bg-blue-500 text-white'
                      : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                  }`}
                >
                  From Topic
                </button>
              </div>
            </>
          )}

          {wizardStep === 1 && (
            <>
              {/* From Document Tab */}
              {aiMode === 'document' && (
                <>
                  {/* File Upload Zone */}
                  <div
                    onDragOver={(e) => {
                      e.preventDefault()
                      e.currentTarget.classList.add('border-blue-400')
                    }}
                    onDragLeave={(e) => {
                      e.currentTarget.classList.remove('border-blue-400')
                    }}
                    onDrop={(e) => {
                      e.preventDefault()
                      e.currentTarget.classList.remove('border-blue-400')
                      const files = e.dataTransfer.files
                      if (files.length > 0) {
                        const file = files[0]
                        const validTypes = ['.docx', '.pptx', '.pdf']
                        const isValid = validTypes.some(type => file.name.toLowerCase().endsWith(type))
                        if (isValid && file.size <= 10 * 1024 * 1024) {
                          setUploadedFile(file)
                        } else {
                          setFormError('Invalid file. Please upload .docx, .pptx, or .pdf (max 10MB)')
                        }
                      }
                    }}
                    onClick={() => fileInputRef.current?.click()}
                    className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors ${
                      uploadedFile
                        ? 'border-green-400 bg-green-50'
                        : 'border-gray-300 hover:border-blue-400'
                    }`}
                  >
                    <input
                      ref={fileInputRef}
                      type="file"
                      accept=".docx,.pptx,.pdf"
                      onChange={(e) => {
                        const file = e.target.files?.[0]
                        if (file) {
                          const validTypes = ['.docx', '.pptx', '.pdf']
                          const isValid = validTypes.some(type => file.name.toLowerCase().endsWith(type))
                          if (isValid && file.size <= 10 * 1024 * 1024) {
                            setUploadedFile(file)
                            setFormError('')
                          } else {
                            setFormError('Invalid file. Please upload .docx, .pptx, or .pdf (max 10MB)')
                          }
                        }
                      }}
                      style={{ display: 'none' }}
                    />
                    {uploadedFile ? (
                      <div className="space-y-2">
                        <p className="text-green-700 font-medium">✓ {uploadedFile.name}</p>
                        <button
                          onClick={(e) => {
                            e.stopPropagation()
                            setUploadedFile(null)
                          }}
                          className="inline-block text-gray-500 hover:text-gray-700 text-lg"
                        >
                          ×
                        </button>
                      </div>
                    ) : (
                      <div className="space-y-2">
                        <p className="font-medium text-gray-800">Drop your document here or click to browse</p>
                        <p className="text-sm text-gray-600">Supports .docx, .pptx, .pdf — max 10MB</p>
                      </div>
                    )}
                  </div>

                  <Select
                    label="Difficulty Level"
                    value={docDifficulty}
                    onChange={(e) => setDocDifficulty(e.target.value)}
                    options={[
                      { value: 'beginner', label: 'Beginner' },
                      { value: 'intermediate', label: 'Intermediate' },
                      { value: 'advanced', label: 'Advanced' },
                    ]}
                  />

                  <Textarea
                    label="Additional Instructions"
                    value={docInstructions}
                    onChange={(e) => setDocInstructions(e.target.value)}
                    placeholder="Any specific topics or focus areas? (optional)"
                    rows={3}
                  />
                </>
              )}

              {/* From Topic Tab */}
              {aiMode === 'topic' && (
                <>
                  <Input
                    label="Topic"
                    value={aiData.topic}
                    onChange={(e) => setAiData({ ...aiData, topic: e.target.value })}
                    placeholder="e.g., 'Advanced JavaScript Patterns'"
                  />
                  <Input
                    label="Number of Modules"
                    type="number"
                    value={aiData.num_modules}
                    onChange={(e) => setAiData({ ...aiData, num_modules: parseInt(e.target.value) })}
                    min={1}
                    max={20}
                  />
                  <Select
                    label="Difficulty Level"
                    value={aiData.difficulty}
                    onChange={(e) => setAiData({ ...aiData, difficulty: e.target.value })}
                    options={[
                      { value: 'beginner', label: 'Beginner' },
                      { value: 'intermediate', label: 'Intermediate' },
                      { value: 'advanced', label: 'Advanced' },
                    ]}
                  />
                  <Textarea
                    label="Additional Instructions"
                    value={aiData.additional_instructions}
                    onChange={(e) => setAiData({ ...aiData, additional_instructions: e.target.value })}
                    placeholder="Any specific topics or focus areas?"
                    rows={3}
                  />
                </>
              )}
            </>
          )}

          {wizardStep === 2 && (
            <>
              <div className="text-xs text-gray-500 mb-4">Step 2 of 2</div>
              <Input
                label="Videos per module"
                type="number"
                value={wizardParams.videos_per_module}
                onChange={(e) => setWizardParams({ ...wizardParams, videos_per_module: parseInt(e.target.value) })}
                min={1}
                max={5}
              />
              <Select
                label="Video duration"
                value={wizardParams.video_duration}
                onChange={(e) => setWizardParams({ ...wizardParams, video_duration: e.target.value })}
                options={[
                  { value: 'short', label: 'Short (3-5 min)' },
                  { value: 'medium', label: 'Medium (10-15 min)' },
                  { value: 'long', label: 'Long (20-30 min)' },
                ]}
              />
              <Select
                label="Tone"
                value={wizardParams.tone}
                onChange={(e) => setWizardParams({ ...wizardParams, tone: e.target.value })}
                options={[
                  { value: 'formal', label: 'Formal & Educational' },
                  { value: 'conversational', label: 'Conversational' },
                  { value: 'technical', label: 'Technical' },
                ]}
              />
              <Select
                label="Target audience"
                value={wizardParams.target_audience}
                onChange={(e) => setWizardParams({ ...wizardParams, target_audience: e.target.value })}
                options={[
                  { value: 'new_starters', label: 'New Starters' },
                  { value: 'experienced_staff', label: 'Experienced Staff' },
                  { value: 'management', label: 'Management' },
                  { value: 'general', label: 'General' },
                ]}
              />
              <div className="flex items-center gap-3">
                <input
                  type="checkbox"
                  id="include-assessment"
                  checked={wizardParams.include_assessment}
                  onChange={(e) => setWizardParams({ ...wizardParams, include_assessment: e.target.checked })}
                  className="w-4 h-4"
                />
                <label htmlFor="include-assessment" className="text-sm font-medium">
                  Include end-of-course assessment?
                </label>
              </div>
            </>
          )}

          {formError && (
            <div className="p-3 bg-red-50 border border-red-200 rounded text-red-700 text-sm">
              {formError}
            </div>
          )}

          <div className="flex gap-2 justify-end">
            <Button variant="secondary" onClick={() => setAiModalOpen(false)} disabled={generating}>
              Cancel
            </Button>
            <Button onClick={handleGenerateCourse} disabled={generating}>
              {wizardStep === 1 ? (
                'Next →'
              ) : generating ? (
                <span className="flex items-center gap-2">
                  <span className="inline-block spin">⏳</span>
                  Generating...
                </span>
              ) : (
                'Generate Course'
              )}
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  )
}
