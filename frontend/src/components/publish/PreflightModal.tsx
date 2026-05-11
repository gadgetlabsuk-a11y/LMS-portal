import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '@/services/api'
import { Modal } from '@/components/common/Modal'

interface PreflightResult {
  rule: string
  status: 'pass' | 'warn' | 'fail'
  message: string
  fix_url?: string | null
}
interface PreflightResponse {
  can_publish: boolean
  results: PreflightResult[]
}

interface PreflightModalProps {
  open: boolean
  courseId: number | string
  onClose: () => void
  onPublished: () => void
}

const statusColor = { pass: '#10b981', warn: '#f59e0b', fail: '#ef4444' }
const statusLabel = { pass: 'Pass', warn: 'Warn', fail: 'Fail' }

export function PreflightModal({ open, courseId, onClose, onPublished }: PreflightModalProps) {
  const navigate = useNavigate()
  const [preflight, setPreflight] = useState<PreflightResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [showConfirm, setShowConfirm] = useState(false)
  const [publishing, setPublishing] = useState(false)

  useEffect(() => {
    if (!open) return
    setLoading(true)
    api.get(`/courses/${courseId}/preflight`)
      .then(res => res.json())
      .then(data => setPreflight(data as PreflightResponse))
      .finally(() => setLoading(false))
  }, [open, courseId])

  const handlePublishClick = async () => {
    // Re-fetch preflight fresh before confirming
    const freshRes = await api.get(`/courses/${courseId}/preflight`)
    const fresh = await freshRes.json() as PreflightResponse
    setPreflight(fresh)
    if (fresh.can_publish) {
      setShowConfirm(true)
    }
  }

  const handleConfirmPublish = async () => {
    setPublishing(true)
    try {
      await api.post(`/courses/${courseId}/publish`, {})
      setShowConfirm(false)
      onClose()
      onPublished()
    } finally {
      setPublishing(false)
    }
  }

  return (
    <>
      <Modal open={open} onClose={onClose} title="Pre-flight Check">
        {loading && <p>Checking...</p>}
        {preflight && (
          <>
            <ul style={{ listStyle: 'none', padding: 0 }}>
              {preflight.results.map(r => (
                <li
                  key={r.rule}
                  data-testid={`preflight-result-${r.rule}`}
                  style={{
                    display: 'flex', alignItems: 'center', gap: '8px',
                    padding: '8px 0', borderBottom: '1px solid #f3f4f6',
                  }}
                >
                  <span
                    style={{
                      fontWeight: 600, fontSize: '0.75rem',
                      color: statusColor[r.status], minWidth: '36px',
                    }}
                  >
                    {statusLabel[r.status]}
                  </span>
                  <span style={{ flex: 1, fontSize: '0.875rem' }}>{r.message}</span>
                  {r.fix_url && r.status !== 'pass' && (
                    <button
                      data-testid={`preflight-fix-${r.rule}`}
                      onClick={() => { onClose(); navigate(r.fix_url!) }}
                      style={{
                        fontSize: '0.75rem', color: '#3b82f6',
                        background: 'none', border: 'none', cursor: 'pointer',
                      }}
                    >
                      Fix
                    </button>
                  )}
                </li>
              ))}
            </ul>
            <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '16px', gap: '8px' }}>
              <button onClick={onClose} style={{ padding: '6px 14px' }}>Cancel</button>
              <button
                data-testid="preflight-publish-btn"
                onClick={handlePublishClick}
                disabled={!preflight.can_publish}
                style={{
                  padding: '6px 14px', background: preflight.can_publish ? '#3b82f6' : '#9ca3af',
                  color: 'white', border: 'none', borderRadius: '4px',
                  cursor: preflight.can_publish ? 'pointer' : 'not-allowed',
                }}
              >
                Publish
              </button>
            </div>
          </>
        )}
      </Modal>

      <Modal open={showConfirm} onClose={() => setShowConfirm(false)} title="Confirm Publish">
        <p>Publishing will make this course visible to learners.</p>
        <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '16px', gap: '8px' }}>
          <button onClick={() => setShowConfirm(false)}>Cancel</button>
          <button
            data-testid="confirm-publish-btn"
            onClick={handleConfirmPublish}
            disabled={publishing}
            style={{
              padding: '6px 14px', background: '#10b981',
              color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer',
            }}
          >
            {publishing ? 'Publishing...' : 'Confirm & Publish'}
          </button>
        </div>
      </Modal>
    </>
  )
}
