import { useState, useEffect, useRef } from 'react'
import { useParams } from 'react-router-dom'
import { api } from '@/services/api'
import { Button } from '@/components/common/Button'
import { Input } from '@/components/common/Input'
import { Select } from '@/components/common/Select'
import { QuestionForm, type QuestionFormData } from '@/components/quiz/QuestionForm'
import { DndContext, type DragEndEvent, PointerSensor, KeyboardSensor, useSensor, useSensors } from '@dnd-kit/core'
import { SortableContext, arrayMove, sortableKeyboardCoordinates, verticalListSortingStrategy } from '@dnd-kit/sortable'
import { SortableQuestionRow } from '@/components/quiz/SortableQuestionRow'
import { SideDrawer } from '@/components/ai/SideDrawer'
import { useSSEStream } from '@/hooks/useSSEStream'

interface Quiz {
  id: number
  title: string
  pass_rate: number
  attempts_allowed: number
  show_feedback: string
  status: string | null
}

interface Question {
  id: number
  order_index: number
  type: string
  prompt: string
  points: number
  explanation: string | null
  options: string[] | null
  correct_answer: number | number[] | string | null
}

const FEEDBACK_OPTIONS = [
  { value: 'immediate', label: 'Immediate' },
  { value: 'on_completion', label: 'After completion' },
  { value: 'never', label: 'Never' },
]

const TONE_OPTIONS = [
  { value: 'professional', label: 'Professional' },
  { value: 'casual', label: 'Casual' },
  { value: 'academic', label: 'Academic' },
]

export function QuizBuilderPage() {
  const { id: courseId, quizId } = useParams<{ id: string; quizId: string }>()

  const [quiz, setQuiz] = useState<Quiz | null>(null)
  const [questions, setQuestions] = useState<Question[]>([])
  const [passRate, setPassRate] = useState('80')
  const [attemptsAllowed, setAttemptsAllowed] = useState('3')
  const [showFeedback, setShowFeedback] = useState('immediate')
  const [showAddForm, setShowAddForm] = useState(false)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [aiDrawerOpen, setAiDrawerOpen] = useState(false)
  const [generateCount, setGenerateCount] = useState('5')
  const [tonePreset, setTonePreset] = useState('professional')
  const [pendingQuestions, setPendingQuestions] = useState<QuestionFormData[]>([])
  const bufferRef = useRef('')
  const { startStream, isStreaming } = useSSEStream()

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 8 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }),
  )

  useEffect(() => {
    if (!quizId) return
    const load = async () => {
      setLoading(true)
      try {
        const [qRes, questRes] = await Promise.all([
          api.get(`/quizzes/${quizId}`),
          api.get(`/quizzes/${quizId}/questions`),
        ])
        const quizData: Quiz = await qRes.json()
        const questData: Question[] = await questRes.json()
        setQuiz(quizData)
        setPassRate(String(quizData.pass_rate))
        setAttemptsAllowed(String(quizData.attempts_allowed))
        setShowFeedback(quizData.show_feedback)
        setQuestions(questData)
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [quizId])

  const handleSaveSettings = async () => {
    if (!quizId) return
    setSaving(true)
    try {
      const res = await api.put(`/quizzes/${quizId}`, {
        pass_rate: parseInt(passRate, 10),
        attempts_allowed: parseInt(attemptsAllowed, 10),
        show_feedback: showFeedback,
      })
      const updated: Quiz = await res.json()
      setQuiz(updated)
    } finally {
      setSaving(false)
    }
  }

  const loadQuestions = async () => {
    if (!quizId) return
    const res = await api.get(`/quizzes/${quizId}/questions`)
    const data: Question[] = await res.json()
    setQuestions(data)
  }

  const handleAddQuestion = async (data: QuestionFormData) => {
    if (!quizId) return
    await api.post(`/quizzes/${quizId}/questions`, {
      type: data.type,
      prompt: data.prompt,
      options: data.options,
      correct_answer: data.correct_answer,
      explanation: data.explanation || null,
    })
    setShowAddForm(false)
    await loadQuestions()
  }

  const handleUpdateQuestion = async (questionId: number, data: QuestionFormData) => {
    await api.put(`/questions/${questionId}`, {
      type: data.type,
      prompt: data.prompt,
      options: data.options,
      correct_answer: data.correct_answer,
      explanation: data.explanation || null,
    })
    setEditingId(null)
    await loadQuestions()
  }

  const handleDeleteQuestion = async (questionId: number) => {
    await api.delete(`/questions/${questionId}`)
    await loadQuestions()
  }

  const handleDragEnd = async (event: DragEndEvent) => {
    const { active, over } = event
    if (!over || active.id === over.id) return
    const oldIndex = questions.findIndex((q) => q.id === active.id)
    const newIndex = questions.findIndex((q) => q.id === over.id)
    const newOrder = arrayMove(questions, oldIndex, newIndex)
    setQuestions(newOrder) // optimistic update
    await api.post(`/quizzes/${quizId}/questions/reorder`, {
      question_ids: newOrder.map((q) => q.id),
    })
  }

  const handleGenerate = async () => {
    bufferRef.current = ''
    try {
      await startStream({
        url: `/quizzes/${quizId}/ai/generate-questions`,
        body: { count: parseInt(generateCount, 10), tone_preset: tonePreset },
        onToken: (t) => { bufferRef.current += t },
      })
      const parsed: QuestionFormData[] = JSON.parse(bufferRef.current)
      setPendingQuestions(parsed)
    } catch (e) {
      console.error('AI question generation failed:', e)
    }
  }

  const handleConfirmAI = async () => {
    if (!quizId) return
    for (const q of pendingQuestions) {
      await api.post(`/quizzes/${quizId}/questions`, {
        type: q.type,
        prompt: q.prompt,
        options: q.options,
        correct_answer: q.correct_answer,
        explanation: q.explanation || null,
      })
    }
    setPendingQuestions([])
    setAiDrawerOpen(false)
    await loadQuestions()
  }

  if (loading) return <div data-testid="quiz-builder-loading">Loading...</div>

  return (
    <div data-testid="quiz-builder-page" style={{ padding: '24px', maxWidth: '800px', margin: '0 auto' }}>
      <h1 style={{ fontSize: '20px', fontWeight: 700, marginBottom: '4px' }}>
        {quiz?.title ?? 'Quiz Builder'}
      </h1>
      <p style={{ fontSize: '13px', color: '#6b7280', marginBottom: '24px' }}>
        Course ID: {courseId}
      </p>

      {/* Quiz Settings */}
      <section
        data-testid="quiz-settings"
        style={{ background: '#f9fafb', border: '1px solid #e5e7eb', borderRadius: '8px', padding: '16px', marginBottom: '24px' }}
      >
        <h2 style={{ fontSize: '15px', fontWeight: 600, marginBottom: '12px' }}>Quiz Settings</h2>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '12px', marginBottom: '12px' }}>
          <div>
            <label style={{ fontSize: '12px', fontWeight: 600, color: '#374151', display: 'block', marginBottom: '4px' }}>
              Pass Rate (%)
            </label>
            <Input
              data-testid="pass-rate-input"
              type="number"
              value={passRate}
              onChange={(e) => setPassRate(e.target.value)}
              min="0"
              max="100"
            />
          </div>
          <div>
            <label style={{ fontSize: '12px', fontWeight: 600, color: '#374151', display: 'block', marginBottom: '4px' }}>
              Attempts Allowed
            </label>
            <Input
              data-testid="attempts-allowed-input"
              type="number"
              value={attemptsAllowed}
              onChange={(e) => setAttemptsAllowed(e.target.value)}
              min="1"
            />
          </div>
          <div>
            <label style={{ fontSize: '12px', fontWeight: 600, color: '#374151', display: 'block', marginBottom: '4px' }}>
              Show Feedback
            </label>
            <Select
              data-testid="show-feedback-select"
              value={showFeedback}
              options={FEEDBACK_OPTIONS}
              onChange={(e) => setShowFeedback(e.target.value)}
            />
          </div>
        </div>
        <Button data-testid="save-settings-btn" onClick={handleSaveSettings} disabled={saving}>
          {saving ? 'Saving...' : 'Save Settings'}
        </Button>
      </section>

      {/* Questions */}
      <section data-testid="questions-section">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
          <h2 style={{ fontSize: '15px', fontWeight: 600 }}>
            Questions ({questions.length})
          </h2>
          <div style={{ display: 'flex', gap: '8px' }}>
            <Button
              data-testid="ai-generate-btn"
              onClick={() => { setPendingQuestions([]); setAiDrawerOpen(true) }}
              variant="secondary"
            >
              Generate with AI
            </Button>
            <Button
              data-testid="add-question-btn"
              onClick={() => setShowAddForm(true)}
            >
              + Add Question
            </Button>
          </div>
        </div>

        {/* Add question form */}
        {showAddForm && (
          <QuestionForm
            onSave={handleAddQuestion}
            onCancel={() => setShowAddForm(false)}
          />
        )}

        {/* Question list */}
        <DndContext sensors={sensors} onDragEnd={handleDragEnd}>
          <SortableContext items={questions.map((q) => q.id)} strategy={verticalListSortingStrategy}>
            <div data-testid="question-list" style={{ paddingLeft: '28px' }}>
              {questions.map((q) => (
                <SortableQuestionRow key={q.id} id={q.id}>
                  <div
                    data-testid={`question-row-${q.id}`}
                    style={{
                      border: '1px solid #e5e7eb', borderRadius: '6px', padding: '12px',
                      marginBottom: '8px', background: 'white',
                    }}
                  >
                    {editingId === q.id ? (
                      <QuestionForm
                        initial={{
                          type: q.type as QuestionFormData['type'],
                          prompt: q.prompt,
                          options: q.options,
                          correct_answer: q.correct_answer,
                          explanation: q.explanation ?? '',
                        }}
                        onSave={(data) => handleUpdateQuestion(q.id, data)}
                        onCancel={() => setEditingId(null)}
                      />
                    ) : (
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                        <div>
                          <span style={{ fontSize: '11px', color: '#6b7280', textTransform: 'uppercase', fontWeight: 600 }}>
                            {q.type.replace('_', ' ')}
                          </span>
                          <p style={{ fontSize: '14px', color: '#111827', marginTop: '4px' }}>{q.prompt}</p>
                          {q.explanation && (
                            <p style={{ fontSize: '12px', color: '#6b7280', marginTop: '4px', fontStyle: 'italic' }}>
                              {q.explanation}
                            </p>
                          )}
                        </div>
                        <div style={{ display: 'flex', gap: '8px', flexShrink: 0, marginLeft: '12px' }}>
                          <Button
                            data-testid={`edit-question-${q.id}`}
                            onClick={() => setEditingId(q.id)}
                            variant="secondary"
                          >
                            Edit
                          </Button>
                          <Button
                            data-testid={`delete-question-${q.id}`}
                            onClick={() => handleDeleteQuestion(q.id)}
                            variant="danger"
                          >
                            Delete
                          </Button>
                        </div>
                      </div>
                    )}
                  </div>
                </SortableQuestionRow>
              ))}
              {questions.length === 0 && !showAddForm && (
                <p style={{ fontSize: '13px', color: '#9ca3af', textAlign: 'center', padding: '24px' }}>
                  No questions yet. Add a question or generate with AI.
                </p>
              )}
            </div>
          </SortableContext>
        </DndContext>
      </section>

      <SideDrawer
        isOpen={aiDrawerOpen}
        onClose={() => setAiDrawerOpen(false)}
        title="AI Question Generator"
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          <div>
            <label style={{ fontSize: '12px', fontWeight: 600, color: '#374151', display: 'block', marginBottom: '4px' }}>
              Number of questions
            </label>
            <Input
              data-testid="generate-count-input"
              type="number"
              value={generateCount}
              onChange={(e) => setGenerateCount(e.target.value)}
              min="1"
              max="20"
            />
          </div>
          <div>
            <label style={{ fontSize: '12px', fontWeight: 600, color: '#374151', display: 'block', marginBottom: '4px' }}>
              Tone
            </label>
            <Select
              data-testid="generate-tone-select"
              value={tonePreset}
              options={TONE_OPTIONS}
              onChange={(e) => setTonePreset(e.target.value)}
            />
          </div>
          <Button
            data-testid="generate-questions-btn"
            onClick={handleGenerate}
            disabled={isStreaming}
          >
            {isStreaming ? 'Generating...' : 'Generate Questions'}
          </Button>

          {pendingQuestions.length > 0 && (
            <div data-testid="pending-questions-preview">
              <p style={{ fontSize: '13px', fontWeight: 600, marginBottom: '8px' }}>
                {pendingQuestions.length} questions generated — review below:
              </p>
              {pendingQuestions.map((q, i) => (
                <div key={i} style={{ borderBottom: '1px solid #e5e7eb', paddingBottom: '8px', marginBottom: '8px' }}>
                  <span style={{ fontSize: '11px', color: '#6b7280', textTransform: 'uppercase' }}>{q.type}</span>
                  <p style={{ fontSize: '13px', color: '#111827', marginTop: '2px' }}>{q.prompt}</p>
                </div>
              ))}
              <Button data-testid="confirm-ai-questions-btn" onClick={handleConfirmAI}>
                Add All Questions
              </Button>
            </div>
          )}
        </div>
      </SideDrawer>
    </div>
  )
}
