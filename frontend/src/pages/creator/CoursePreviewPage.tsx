import { useParams, useNavigate, useSearchParams } from 'react-router-dom'
import { CoursePlayer } from '@/components/player/CoursePlayer'

export function CoursePreviewPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const returnTo = decodeURIComponent(
    searchParams.get('returnTo') ?? `/creator/courses/${id}/builder`
  )

  return (
    <div style={{ position: 'relative', minHeight: '100vh' }}>
      {/* Fixed watermark banner — sits above iframe */}
      <div
        data-testid="preview-watermark"
        style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          zIndex: 1000,
          background: '#fef3c7',
          borderBottom: '2px solid #f59e0b',
          padding: '8px 16px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
        }}
      >
        <span style={{ fontWeight: 600, color: '#92400e' }}>
          Preview Mode — Draft
        </span>
        <button
          data-testid="exit-preview-btn"
          onClick={() => navigate(returnTo)}
          style={{
            padding: '4px 12px',
            borderRadius: '4px',
            background: '#92400e',
            color: 'white',
            border: 'none',
            cursor: 'pointer',
            fontSize: '0.875rem',
          }}
        >
          Exit Preview
        </button>
      </div>

      {/* React CoursePlayer — replaces the backend iframe (PREVIEW-02). */}
      <div style={{ paddingTop: '48px', height: '100vh', boxSizing: 'border-box' }}>
        <CoursePlayer courseId={Number(id)} mode="preview" />
      </div>
    </div>
  )
}
