import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { api, API_BASE } from '@/services/api'
import { Input } from '@/components/common/Input'
import { Textarea } from '@/components/common/Textarea'
import { Select } from '@/components/common/Select'
import { Button } from '@/components/common/Button'
import { useSSEStream } from '@/hooks/useSSEStream'
import { SideDrawer } from '@/components/ai/SideDrawer'
import { StreamingTextOutput } from '@/components/ai/StreamingTextOutput'

interface ModuleData {
  id: number
  course_id: number
  title: string
  description: string | null
  learning_objectives: string[] | null
  estimated_duration_minutes: number | null
  unlock_rule: string | null
  status: string | null
}

const UNLOCK_OPTIONS = [
  { value: 'immediate', label: 'Available immediately' },
  { value: 'after_previous', label: 'After completing previous module' },
  { value: 'on_date', label: 'On a specific date' },
]

const STATUS_OPTIONS = [
  { value: 'draft', label: 'Draft' },
  { value: 'published', label: 'Published' },
]

export function ModuleDetailPage() {
  const { id: courseId, moduleId } = useParams<{ id: string; moduleId: string }>()
  const navigate = useNavigate()

  const [module, setModule] = useState<ModuleData | null>(null)
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [objectives, setObjectives] = useState<string[]>([''])
  const [durationMinutes, setDurationMinutes] = useState<string>('')
  const [unlockRule, setUnlockRule] = useState('immediate')
  const [status, setStatus] = useState('draft')
  const [saving, setSaving] = useState(false)
  const [saveMsg, setSaveMsg] = useState('')

  // AI generation state
  const [aiPrompt, setAiPrompt] = useState('')
  const [docFile, setDocFile] = useState<File | null>(null)
  const [tonePreset, setTonePreset] = useState('professional')
  const [aiDrawerOpen, setAiDrawerOpen] = useState(false)
  const { startStream, cancel, isStreaming: streaming } = useSSEStream()

  useEffect(() => {
    if (!courseId) return
    api.get(`/courses/${courseId}`)
      .then(res => res.json())
      .then((course: { ai_tone_preset?: string }) => {
        setTonePreset(course.ai_tone_preset || 'professional')
      })
      .catch(() => {})
  }, [courseId])

  useEffect(() => {
    if (!moduleId) return
    api.get(`/modules/${moduleId}`)
      .then(res => res.json())
      .then((data: ModuleData) => {
        setModule(data)
        setTitle(data.title || '')
        setDescription(data.description || '')
        setObjectives(
          data.learning_objectives && data.learning_objectives.length > 0
            ? data.learning_objectives
            : ['']
        )
        setDurationMinutes(data.estimated_duration_minutes?.toString() || '')
        setUnlockRule(data.unlock_rule || 'immediate')
        setStatus(data.status || 'draft')
      })
      .catch(err => console.error('Failed to load module:', err))
  }, [moduleId])

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!moduleId) return
    setSaving(true)
    setSaveMsg('')
    try {
      await api.put(`/modules/${moduleId}`, {
        title,
        description: description || null,
        learning_objectives: objectives.filter(o => o.trim().length > 0),
        estimated_duration_minutes: durationMinutes ? parseInt(durationMinutes, 10) : null,
        unlock_rule: unlockRule || null,
        status,
      })
      setSaveMsg('Saved')
      setTimeout(() => setSaveMsg(''), 3000)
    } catch (err) {
      setSaveMsg('Save failed')
      console.error(err)
    } finally {
      setSaving(false)
    }
  }

  const handleGenerateDescription = async () => {
    if (!moduleId || !aiPrompt.trim()) return
    setDescription('')

    let docUrl: string | undefined
    if (docFile) {
      try {
        const formData = new FormData()
        formData.append('file', docFile)
        formData.append('category', 'documents')
        const uploadRes = await fetch(`${API_BASE}/api/uploads`, {
          method: 'POST',
          headers: { Authorization: `Bearer ${localStorage.getItem('token')}` },
          body: formData,
        })
        const { url } = await uploadRes.json()
        docUrl = url
      } catch {
        console.warn('Document upload failed — proceeding without document context')
      }
    }

    await startStream({
      url: `/api/modules/${moduleId}/ai/generate-description`,
      body: {
        prompt: aiPrompt,
        tone_preset: tonePreset,
        document_url: docUrl,
      },
      onToken: t => setDescription(prev => prev + t),
    })
  }

  const updateObjective = (index: number, value: string) => {
    setObjectives(prev => prev.map((o, i) => (i === index ? value : o)))
  }

  const addObjective = () => {
    if (objectives.length < 5) setObjectives(prev => [...prev, ''])
  }

  const removeObjective = (index: number) => {
    setObjectives(prev => prev.filter((_, i) => i !== index))
  }

  return (
    <div style={{ maxWidth: '720px', margin: '0 auto', padding: '32px 24px' }}>
      {/* Back link */}
      <button
        onClick={() => navigate(`/creator/courses/${courseId}/builder`)}
        style={{ background: 'none', border: 'none', color: '#6366f1', cursor: 'pointer',
          fontSize: '14px', marginBottom: '20px', padding: 0 }}
      >
        Back to Course Builder
      </button>

      <h1 style={{ fontSize: '22px', fontWeight: 700, color: '#111827', marginBottom: '8px' }}>
        Module Details
      </h1>
      {module && (
        <p style={{ fontSize: '13px', color: '#6b7280', marginBottom: '28px' }}>
          Editing module #{module.id}
        </p>
      )}

      <form onSubmit={handleSave}>
        {/* Title */}
        <div style={{ marginBottom: '20px' }}>
          <label style={{ display: 'block', fontSize: '13px', fontWeight: 600,
            color: '#374151', marginBottom: '6px' }}>
            Module Title *
          </label>
          <Input
            data-testid="module-title-input"
            value={title}
            onChange={(e: React.ChangeEvent<HTMLInputElement>) => setTitle(e.target.value)}
            required
            placeholder="e.g. Introduction to React Hooks"
          />
        </div>

        {/* Description + AI generation */}
        <div style={{ marginBottom: '20px' }}>
          <label style={{ display: 'block', fontSize: '13px', fontWeight: 600,
            color: '#374151', marginBottom: '6px' }}>
            Description
          </label>
          <Textarea
            data-testid="module-description-textarea"
            value={description}
            onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => setDescription(e.target.value)}
            placeholder="Describe what learners will cover in this module..."
            rows={4}
          />

          {/* AI generation trigger */}
          <div style={{ marginTop: '8px' }}>
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={() => setAiDrawerOpen(true)}
            >
              Generate with AI
            </Button>
          </div>

          {/* AI generation SideDrawer */}
          <SideDrawer
            isOpen={aiDrawerOpen}
            onClose={() => { cancel(); setAiDrawerOpen(false) }}
            title="Generate Description"
          >
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <Textarea
                value={aiPrompt}
                onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => setAiPrompt(e.target.value)}
                placeholder="Describe the module topic for AI to write the description..."
                rows={3}
              />
              <input
                type="file"
                accept=".pdf,.docx"
                onChange={(e) => setDocFile(e.target.files?.[0] || null)}
                style={{ fontSize: '12px', color: '#6b7280' }}
                title="Optional: upload a document for context"
              />
              <div style={{ display: 'flex', gap: '8px' }}>
                <Button
                  type="button"
                  data-testid="ai-generate-description-btn"
                  onClick={handleGenerateDescription}
                  disabled={streaming || !aiPrompt.trim()}
                >
                  {streaming ? 'Generating...' : 'Generate description'}
                </Button>
                {streaming && (
                  <button
                    type="button"
                    onClick={() => cancel()}
                    style={{ fontSize: '12px', color: '#ef4444', background: 'none',
                      border: 'none', cursor: 'pointer' }}
                  >
                    Stop
                  </button>
                )}
              </div>
              <StreamingTextOutput
                text={description}
                isStreaming={streaming}
                placeholder="Generated description will appear here (and update the field above)..."
              />
              {!streaming && description && (
                <button
                  type="button"
                  onClick={() => setAiDrawerOpen(false)}
                  style={{ fontSize: '13px', color: '#2563eb', background: 'none',
                    border: 'none', cursor: 'pointer', textAlign: 'left' }}
                >
                  ✓ Description applied — close drawer
                </button>
              )}
            </div>
          </SideDrawer>
        </div>

        {/* Learning Objectives (UI label: "Learning Outcome", API field: learning_objectives) */}
        <div style={{ marginBottom: '20px' }}>
          <label style={{ display: 'block', fontSize: '13px', fontWeight: 600,
            color: '#374151', marginBottom: '6px' }}>
            Learning Outcome
          </label>
          {objectives.map((obj, i) => (
            <div key={i} style={{ display: 'flex', gap: '8px', marginBottom: '6px' }}>
              <Input
                value={obj}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => updateObjective(i, e.target.value)}
                placeholder={`Objective ${i + 1}`}
              />
              {objectives.length > 1 && (
                <button
                  type="button"
                  onClick={() => removeObjective(i)}
                  style={{ color: '#ef4444', background: 'none', border: 'none',
                    cursor: 'pointer', fontSize: '16px', padding: '0 4px' }}
                  title="Remove"
                >
                  x
                </button>
              )}
            </div>
          ))}
          {objectives.length < 5 && (
            <button
              type="button"
              onClick={addObjective}
              style={{ fontSize: '12px', color: '#6366f1', background: 'none',
                border: 'none', cursor: 'pointer', padding: 0 }}
            >
              + Add objective
            </button>
          )}
        </div>

        {/* Duration Estimate */}
        <div style={{ marginBottom: '20px' }}>
          <label style={{ display: 'block', fontSize: '13px', fontWeight: 600,
            color: '#374151', marginBottom: '6px' }}>
            Duration Estimate (minutes)
          </label>
          <Input
            data-testid="module-duration-input"
            type="number"
            value={durationMinutes}
            onChange={(e: React.ChangeEvent<HTMLInputElement>) => setDurationMinutes(e.target.value)}
            placeholder="e.g. 45"
            min={1}
          />
        </div>

        {/* Unlock Rule */}
        <div style={{ marginBottom: '20px' }}>
          <label style={{ display: 'block', fontSize: '13px', fontWeight: 600,
            color: '#374151', marginBottom: '6px' }}>
            Unlock Rule
          </label>
          <Select
            data-testid="module-unlock-rule-select"
            value={unlockRule}
            onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setUnlockRule(e.target.value)}
            options={UNLOCK_OPTIONS}
          />
        </div>

        {/* Status */}
        <div style={{ marginBottom: '28px' }}>
          <label style={{ display: 'block', fontSize: '13px', fontWeight: 600,
            color: '#374151', marginBottom: '6px' }}>
            Status
          </label>
          <Select
            value={status}
            onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setStatus(e.target.value)}
            options={STATUS_OPTIONS}
          />
        </div>

        {/* Save */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <Button type="submit" disabled={saving}>
            {saving ? 'Saving...' : 'Save changes'}
          </Button>
          {saveMsg && (
            <span style={{ fontSize: '13px',
              color: saveMsg === 'Saved' ? '#16a34a' : '#ef4444' }}>
              {saveMsg}
            </span>
          )}
        </div>
      </form>
    </div>
  )
}
