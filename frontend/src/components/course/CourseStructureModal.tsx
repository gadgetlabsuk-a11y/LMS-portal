import { useState } from 'react'
import { Modal } from '@/components/common/Modal'
import { Button } from '@/components/common/Button'
import { Input } from '@/components/common/Input'
import { SkeletonTreePreview } from '@/components/course/SkeletonTreePreview'
import { api } from '@/services/api'

interface CourseStructureModalProps {
  open: boolean
  onClose: () => void
  courseId: number | null
  onConfirmed: (courseId: number) => void
}

export function CourseStructureModal({
  open,
  onClose,
  courseId,
  onConfirmed,
}: CourseStructureModalProps) {
  const [moduleCount, setModuleCount] = useState(3)
  const [videosPerModule, setVideosPerModule] = useState(2)
  const [quizPerModule, setQuizPerModule] = useState(false)
  const [scaffolding, setScaffolding] = useState(false)

  const handleConfirm = async () => {
    if (!courseId) return
    setScaffolding(true)
    try {
      for (let mi = 0; mi < moduleCount; mi++) {
        const modRes = await api.post(`/courses/${courseId}/modules`, {
          title: `Module ${mi + 1}`,
          status: 'draft',
        })
        if (!modRes.ok) throw new Error('Module creation failed')
        const mod = await modRes.json()

        for (let vi = 0; vi < videosPerModule; vi++) {
          const vidRes = await api.post(`/modules/${mod.id}/videos`, {
            title: `Video ${vi + 1}`,
            status: 'draft',
            video_type: 'slides',
          })
          if (!vidRes.ok) throw new Error('Video creation failed')
        }

        if (quizPerModule) {
          await api.post(`/modules/${mod.id}/quizzes`, {
            title: `Quiz ${mi + 1}`,
            pass_rate: 80,
            attempts_allowed: 3,
            show_feedback: true,
          })
        }
      }
      onConfirmed(courseId)
    } catch (err) {
      console.error('Scaffolding error:', err)
      // Re-enable button so user can retry
    } finally {
      setScaffolding(false)
    }
  }

  return (
    <Modal open={open} onClose={onClose} title="Set Up Course Structure" size="lg">
      <p style={{ color: '#6b7280', fontSize: '14px', marginBottom: '20px' }}>
        Define the skeleton of your course. You can add, remove, and rename modules and videos in
        the Course Builder.
      </p>

      {/* Number inputs */}
      <Input
        label="Number of Modules"
        type="number"
        value={moduleCount}
        min={1}
        max={10}
        onChange={e => setModuleCount(Math.max(1, Math.min(10, Number(e.target.value))))}
      />
      <Input
        label="Videos per Module"
        type="number"
        value={videosPerModule}
        min={1}
        max={10}
        onChange={e => setVideosPerModule(Math.max(1, Math.min(10, Number(e.target.value))))}
      />

      {/* Quiz toggle */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '20px' }}>
        <input
          id="quiz-toggle"
          type="checkbox"
          checked={quizPerModule}
          onChange={e => setQuizPerModule(e.target.checked)}
          style={{ width: '16px', height: '16px', cursor: 'pointer' }}
        />
        <label htmlFor="quiz-toggle" style={{ fontSize: '14px', color: '#374151', cursor: 'pointer' }}>
          Include a quiz in each module
        </label>
      </div>

      {/* Structure preview */}
      <div style={{ marginBottom: '20px' }}>
        <p style={{ fontSize: '14px', fontWeight: 500, color: '#374151', marginBottom: '8px' }}>
          Structure Preview
        </p>
        <div
          style={{
            border: '1px solid #e5e7eb',
            borderRadius: '8px',
            overflow: 'hidden',
            maxHeight: '300px',
            overflowY: 'auto',
          }}
        >
          <SkeletonTreePreview
            moduleCount={moduleCount}
            videosPerModule={videosPerModule}
            quizPerModule={quizPerModule}
          />
        </div>
      </div>

      {/* Footer */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'flex-end',
          gap: '12px',
          paddingTop: '16px',
          borderTop: '1px solid #e5e7eb',
        }}
      >
        <Button variant="secondary" onClick={onClose} disabled={scaffolding}>
          Back
        </Button>
        <Button variant="primary" onClick={handleConfirm} disabled={scaffolding}>
          {scaffolding ? 'Building...' : 'Confirm & Build'}
        </Button>
      </div>
    </Modal>
  )
}
