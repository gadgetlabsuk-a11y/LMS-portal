import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { api } from '@/services/api'
import { CourseTreeRail } from '@/components/builder/CourseTreeRail'
import { ModuleOverviewList } from '@/components/builder/ModuleOverviewList'
import { AISuggestionsRail } from '@/components/ai/AISuggestionsRail'
import { PreflightModal } from '@/components/publish/PreflightModal'
import type { BuilderModule as Module, BuilderVideo as Video, BuilderQuiz as Quiz } from '@/components/builder/types'

export function CourseBuilderPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [modules, setModules] = useState<Module[]>([])
  const [videos, setVideos] = useState<Record<number, Video[]>>({})
  const [quizzes, setQuizzes] = useState<Record<number, Quiz[]>>({})
  const [loading, setLoading] = useState(true)
  const [showPreflight, setShowPreflight] = useState(false)
  const [courseStatus, setCourseStatus] = useState<string>('draft')

  useEffect(() => {
    if (!id) return
    const fetchTree = async () => {
      try {
        // Fetch course status
        const courseRes = await api.get(`/courses/${id}`)
        const courseData = await courseRes.json()
        setCourseStatus(courseData.status ?? 'draft')

        const modsRes = await api.get(`/courses/${id}/modules`)
        const mods: Module[] = await modsRes.json()
        setModules(mods)

        // Lazy-fetch videos + quizzes per module in parallel
        const videoMap: Record<number, Video[]> = {}
        const quizMap: Record<number, Quiz[]> = {}
        await Promise.all(
          mods.map(async (mod) => {
            const [vRes, qRes] = await Promise.all([
              api.get(`/modules/${mod.id}/videos`),
              api.get(`/modules/${mod.id}/quizzes`),
            ])
            videoMap[mod.id] = await vRes.json()
            quizMap[mod.id] = await qRes.json()
          }),
        )
        setVideos(videoMap)
        setQuizzes(quizMap)
      } catch (err) {
        console.error('Failed to load course tree:', err)
      } finally {
        setLoading(false)
      }
    }
    fetchTree()
  }, [id])

  const handlePreview = () => {
    navigate(
      `/creator/courses/${id}/preview?returnTo=${encodeURIComponent(`/creator/courses/${id}/builder`)}`
    )
  }

  const handleArchive = async () => {
    if (!confirm('Archive this course? It will no longer appear in the learner catalogue.')) return
    await api.post(`/courses/${id}/archive`, {})
    setCourseStatus('archived')
  }

  const handleModulesReorder = (reordered: Module[]) => {
    setModules(reordered)
  }

  const handleVideosReorder = (moduleId: number, reordered: Video[]) => {
    setVideos((prev) => ({ ...prev, [moduleId]: reordered }))
  }

  if (loading) {
    return (
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        height: '200px', color: '#6b7280',
      }}>
        Loading course...
      </div>
    )
  }

  return (
    <div style={{ display: 'flex', height: '100%', minHeight: '600px' }}>
      <CourseTreeRail
        courseId={id}
        modules={modules}
        videos={videos}
        quizzes={quizzes}
      />
      <main style={{ flex: 1, overflowY: 'auto', padding: '32px' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '24px' }}>
          <h1 style={{
            fontSize: '20px', fontWeight: 700, color: '#111827', margin: 0,
          }}>
            Course Builder
          </h1>
          <div style={{ display: 'flex', gap: '8px' }}>
            <button
              data-testid="preview-mode-btn"
              onClick={handlePreview}
              style={{
                padding: '6px 14px',
                background: '#f59e0b',
                color: 'white',
                borderRadius: '4px',
                border: 'none',
                cursor: 'pointer',
                fontSize: '0.875rem',
                fontWeight: 600,
              }}
            >
              Preview
            </button>
            <button
              data-testid="publish-btn"
              onClick={() => setShowPreflight(true)}
              style={{
                padding: '6px 14px',
                background: '#3b82f6',
                color: 'white',
                borderRadius: '4px',
                border: 'none',
                cursor: 'pointer',
                fontSize: '0.875rem',
                fontWeight: 600,
              }}
            >
              Publish
            </button>
            {(courseStatus === 'published' || courseStatus === 'has_unpublished_changes') && (
              <button
                data-testid="archive-btn"
                onClick={handleArchive}
                style={{
                  padding: '6px 14px',
                  background: '#6b7280',
                  color: 'white',
                  borderRadius: '4px',
                  border: 'none',
                  cursor: 'pointer',
                  fontSize: '0.875rem',
                  fontWeight: 600,
                }}
              >
                Archive
              </button>
            )}
          </div>
        </div>
        <ModuleOverviewList
          courseId={Number(id)}
          modules={modules}
          videos={videos}
          quizzes={quizzes}
          onModulesReorder={handleModulesReorder}
          onVideosReorder={handleVideosReorder}
        />
      </main>
      <div style={{ width: '256px', flexShrink: 0, overflowY: 'auto', borderLeft: '1px solid #e5e7eb' }}>
        <AISuggestionsRail modules={modules} videos={videos} quizzes={quizzes} />
      </div>
      <PreflightModal
        open={showPreflight}
        courseId={Number(id)}
        onClose={() => setShowPreflight(false)}
        onPublished={() => { setCourseStatus('published'); setShowPreflight(false) }}
      />
    </div>
  )
}
