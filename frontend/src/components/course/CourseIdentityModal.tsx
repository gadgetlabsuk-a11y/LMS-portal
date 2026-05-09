import { useState } from 'react'
import { Modal } from '@/components/common/Modal'
import { Button } from '@/components/common/Button'
import { Input } from '@/components/common/Input'
import { Select } from '@/components/common/Select'
import { Textarea } from '@/components/common/Textarea'
import { api } from '@/services/api'
import { useSSEStream } from '@/hooks/useSSEStream'

interface CourseIdentityModalProps {
  open: boolean
  onClose: () => void
  onCreated: (courseId: number) => void
}

const AUDIENCE_LEVEL_OPTIONS = [
  { value: 'beginner', label: 'Beginner' },
  { value: 'intermediate', label: 'Intermediate' },
  { value: 'advanced', label: 'Advanced' },
]

const TONE_PRESET_OPTIONS = [
  { value: 'professional', label: 'Professional' },
  { value: 'casual', label: 'Casual' },
  { value: 'academic', label: 'Academic' },
  { value: 'conversational', label: 'Conversational' },
]

export function CourseIdentityModal({ open, onClose, onCreated }: CourseIdentityModalProps) {
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [audienceLevel, setAudienceLevel] = useState('')
  const [tonePreset, setTonePreset] = useState('')
  const [objectives, setObjectives] = useState<string[]>([''])
  const [saving, setSaving] = useState(false)

  const { startStream: startDescStream, cancel: cancelDesc, isStreaming: isStreamingDescription } = useSSEStream()
  const { startStream: startObjStream, cancel: cancelObj, isStreaming: isStreamingObjectives } = useSSEStream()

  const resetForm = () => {
    setTitle('')
    setDescription('')
    setAudienceLevel('')
    setTonePreset('')
    setObjectives([''])
    cancelDesc()
    cancelObj()
  }

  const handleClose = () => {
    cancelDesc()
    cancelObj()
    resetForm()
    onClose()
  }

  const addObjective = () => {
    if (objectives.length < 5) setObjectives([...objectives, ''])
  }

  const removeObjective = (i: number) => {
    setObjectives(objectives.filter((_, idx) => idx !== i))
  }

  const updateObjective = (i: number, val: string) => {
    setObjectives(objectives.map((o, idx) => (idx === i ? val : o)))
  }

  const streamDescription = async () => {
    setDescription('')
    await startDescStream({
      url: '/api/courses/ai/generate-description',
      body: { topic: title, tone_preset: tonePreset || 'professional' },
      onToken: t => setDescription(prev => prev + t),
    })
  }

  const streamObjectives = async () => {
    let accumulated = ''
    await startObjStream({
      url: '/api/courses/ai/generate-objectives',
      body: {
        course_title: title,
        description,
        tone_preset: tonePreset || 'professional',
      },
      onToken: t => { accumulated += t },
    })
    // Parse accumulated text into objectives — lines starting with "- "
    const parsed = accumulated
      .split('\n')
      .filter(l => l.trim().startsWith('- '))
      .map(l => l.trim().slice(2).trim())
      .slice(0, 5)
    if (parsed.length > 0) {
      setObjectives(parsed)
    }
  }

  const handleSave = async () => {
    if (!title.trim()) return
    setSaving(true)
    try {
      const res = await api.post('/courses', {
        title: title.trim(),
        description: description.trim() || undefined,
        status: 'draft',
        audience_level: audienceLevel || undefined,
        learning_objectives:
          objectives.filter(Boolean).length > 0 ? objectives.filter(Boolean) : undefined,
        ai_tone_preset: tonePreset || undefined,
      })
      if (res.ok) {
        const course = await res.json()
        onCreated(course.id)
      }
    } finally {
      setSaving(false)
    }
  }

  const isStreaming = isStreamingDescription || isStreamingObjectives

  return (
    <Modal open={open} onClose={handleClose} title="Create New Course" size="lg">
      <div style={{ maxHeight: '70vh', overflowY: 'auto', paddingRight: '4px' }}>
        {/* Title */}
        <Input
          label="Course Title *"
          value={title}
          onChange={e => setTitle(e.target.value)}
          placeholder="e.g. Introduction to Machine Learning"
        />

        {/* Audience Level + Tone Preset row */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
          <Select
            label="Audience Level"
            value={audienceLevel}
            onChange={e => setAudienceLevel(e.target.value)}
            options={AUDIENCE_LEVEL_OPTIONS}
          />
          <Select
            label="Tone Preset"
            value={tonePreset}
            onChange={e => setTonePreset(e.target.value)}
            options={TONE_PRESET_OPTIONS}
          />
        </div>

        {/* Description */}
        <Textarea
          label="Description"
          value={description}
          onChange={e => setDescription(e.target.value)}
          rows={4}
          placeholder="Describe what learners will get from this course..."
        />
        <div style={{ marginTop: '-8px', marginBottom: '16px' }}>
          <Button
            variant="secondary"
            size="sm"
            onClick={streamDescription}
            disabled={!title.trim() || isStreaming}
          >
            {isStreamingDescription ? 'Generating...' : 'Generate with AI'}
          </Button>
        </div>

        {/* Learning Objectives */}
        <div style={{ marginBottom: '8px' }}>
          <p style={{ fontSize: '14px', fontWeight: 500, color: '#374151', marginBottom: '8px' }}>
            Learning Objectives (up to 5)
          </p>
          {objectives.map((obj, i) => (
            <div key={i} style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
              <div style={{ flex: 1 }}>
                <Input
                  value={obj}
                  onChange={e => updateObjective(i, e.target.value)}
                  placeholder={`Objective ${i + 1}`}
                />
              </div>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => removeObjective(i)}
                disabled={objectives.length <= 1}
                style={{ flexShrink: 0, marginBottom: '16px' }}
              >
                ×
              </Button>
            </div>
          ))}
          <div style={{ display: 'flex', gap: '8px', marginBottom: '8px' }}>
            <Button
              variant="secondary"
              size="sm"
              onClick={addObjective}
              disabled={objectives.length >= 5}
            >
              + Add Objective
            </Button>
            <Button
              variant="secondary"
              size="sm"
              onClick={streamObjectives}
              disabled={!title.trim() || isStreaming}
            >
              {isStreamingObjectives ? 'Generating...' : 'Generate with AI'}
            </Button>
          </div>
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
          marginTop: '16px',
        }}
      >
        <Button variant="secondary" onClick={handleClose}>
          Cancel
        </Button>
        <Button
          variant="primary"
          onClick={handleSave}
          disabled={!title.trim() || saving}
        >
          {saving ? 'Creating...' : 'Create Course'}
        </Button>
      </div>
    </Modal>
  )
}
