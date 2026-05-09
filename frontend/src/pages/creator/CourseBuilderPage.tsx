import { useState, useEffect } from 'react'
import { useParams } from 'react-router-dom'
import { api } from '@/services/api'
import { CourseTreeRail } from '@/components/builder/CourseTreeRail'
import { ModuleOverviewList } from '@/components/builder/ModuleOverviewList'
import type { BuilderModule as Module, BuilderVideo as Video, BuilderQuiz as Quiz } from '@/components/builder/types'

export function CourseBuilderPage() {
  const { id } = useParams<{ id: string }>()
  const [modules, setModules] = useState<Module[]>([])
  const [videos, setVideos] = useState<Record<number, Video[]>>({})
  const [quizzes, setQuizzes] = useState<Record<number, Quiz[]>>({})
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!id) return
    const fetchTree = async () => {
      try {
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
        <h1 style={{
          fontSize: '20px', fontWeight: 700, color: '#111827', marginBottom: '24px',
        }}>
          Course Builder
        </h1>
        <ModuleOverviewList
          courseId={Number(id)}
          modules={modules}
          videos={videos}
          quizzes={quizzes}
          onModulesReorder={handleModulesReorder}
          onVideosReorder={handleVideosReorder}
        />
      </main>
    </div>
  )
}
