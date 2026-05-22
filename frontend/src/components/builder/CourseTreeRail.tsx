import { useNavigate } from 'react-router-dom'
import { Badge } from '@/components/common/Badge'
import type { BuilderModule as Module, BuilderVideo as Video, BuilderQuiz as Quiz } from './types'

interface CourseTreeRailProps {
  courseId: string | undefined
  modules: Module[]
  videos: Record<number, Video[]>
  quizzes: Record<number, Quiz[]>
}

export function CourseTreeRail({ courseId, modules, videos, quizzes }: CourseTreeRailProps) {
  const navigate = useNavigate()

  const statusVariant = (status: string | null): 'success' | 'info' =>
    status === 'published' ? 'success' : 'info'

  return (
    <aside
      data-testid="course-tree-rail"
      style={{
        width: '260px',
        minWidth: '260px',
        borderRight: '1px solid #e5e7eb',
        padding: '16px',
        overflowY: 'auto',
        background: '#f9fafb',
      }}
    >
      <p style={{
        fontSize: '11px', fontWeight: 600, textTransform: 'uppercase',
        color: '#6b7280', marginBottom: '12px', letterSpacing: '0.05em',
      }}>
        Course Structure
      </p>
      {modules.map((mod) => (
        <div key={mod.id} style={{ marginBottom: '8px' }}>
          {/* Module row */}
          <div
            data-testid="tree-module-row"
            onClick={() => navigate(`/creator/courses/${courseId}/modules/${mod.id}`)}
            style={{
              display: 'flex', alignItems: 'center', justifyContent: 'space-between',
              padding: '6px 8px', borderRadius: '6px', cursor: 'pointer',
              background: 'white', border: '1px solid #e5e7eb',
            }}
          >
            <span style={{
              fontSize: '13px', fontWeight: 500, color: '#111827',
              overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: '160px',
            }}>
              {mod.title}
            </span>
            <span data-testid="module-status-pill">
              <Badge variant={statusVariant(mod.status)}>
                {mod.status || 'draft'}
              </Badge>
            </span>
          </div>

          {/* Video rows */}
          {(videos[mod.id] || []).map((vid) => (
            <div
              key={vid.id}
              data-testid="tree-video-row"
              onClick={() => navigate(`/creator/courses/${courseId}/videos/${vid.id}/slides`)}
              style={{
                display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                padding: '4px 8px 4px 20px', borderRadius: '4px', cursor: 'pointer',
                marginTop: '2px',
              }}
            >
              <span style={{
                fontSize: '12px', color: '#374151',
                overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: '150px',
              }}>
                {vid.title}
              </span>
              <span data-testid="video-status-pill">
                <Badge variant={statusVariant(vid.status)}>
                  {vid.status || 'draft'}
                </Badge>
              </span>
            </div>
          ))}

          {/* Quiz rows — navigate to quiz builder */}
          {(quizzes[mod.id] || []).map((quiz) => (
            <div
              key={quiz.id}
              data-testid="tree-quiz-row"
              onClick={() => navigate(`/creator/courses/${courseId}/quizzes/${quiz.id}`)}
              style={{
                display: 'flex', alignItems: 'center', gap: '6px',
                padding: '4px 8px 4px 20px', borderRadius: '4px',
                marginTop: '2px', cursor: 'pointer',
              }}
            >
              <span style={{ fontSize: '11px', color: '#6b7280' }}>Quiz</span>
              <span style={{
                fontSize: '12px', color: '#374151',
                overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: '140px',
              }}>
                {quiz.title}
              </span>
            </div>
          ))}
        </div>
      ))}

      {modules.length === 0 && (
        <p style={{ fontSize: '12px', color: '#9ca3af', textAlign: 'center', marginTop: '24px' }}>
          No modules yet. Add modules below.
        </p>
      )}
    </aside>
  )
}
