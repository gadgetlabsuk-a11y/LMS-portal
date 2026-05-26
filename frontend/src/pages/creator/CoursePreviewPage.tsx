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
    <div style={{ height: '100vh', display: 'flex', flexDirection: 'column' }}>
      {/* Watermark banner — in flow at the top so the player fills the rest. */}
      <div
        data-testid="preview-watermark"
        style={{
          flexShrink: 0,
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

      {/* React CoursePlayer fills the remaining height so its footer controls
          (Prev/Pause/Next) are always visible without scrolling. */}
      <div style={{ flex: 1, minHeight: 0 }}>
        <CoursePlayer courseId={Number(id)} mode="preview" />
      </div>
    </div>
  )
}
