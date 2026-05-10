import { useState } from 'react'
import { Button } from '@/components/common/Button'
import { Input } from '@/components/common/Input'
import { Textarea } from '@/components/common/Textarea'
import { Select } from '@/components/common/Select'

type QuestionType = 'mcq_single' | 'mcq_multi' | 'true_false' | 'short_answer'

export interface QuestionFormData {
  type: QuestionType
  prompt: string
  options: string[] | null
  correct_answer: number | number[] | string | null
  explanation: string
}

interface QuestionFormProps {
  initial?: Partial<QuestionFormData>
  onSave: (data: QuestionFormData) => void
  onCancel: () => void
}

const TYPE_OPTIONS = [
  { value: 'mcq_single', label: 'Multiple Choice (single answer)' },
  { value: 'mcq_multi', label: 'Multiple Choice (multi answer)' },
  { value: 'true_false', label: 'True / False' },
  { value: 'short_answer', label: 'Short Answer' },
]

export function QuestionForm({ initial, onSave, onCancel }: QuestionFormProps) {
  const [type, setType] = useState<QuestionType>(initial?.type ?? 'mcq_single')
  const [prompt, setPrompt] = useState(initial?.prompt ?? '')
  const [options, setOptions] = useState<string[]>(
    (initial?.options as string[]) ?? ['', '']
  )
  const [correctSingle, setCorrectSingle] = useState<number>(
    typeof initial?.correct_answer === 'number' ? initial.correct_answer : 0
  )
  const [correctMulti, setCorrectMulti] = useState<number[]>(
    Array.isArray(initial?.correct_answer) ? (initial.correct_answer as number[]) : []
  )
  const [correctTF, setCorrectTF] = useState<'True' | 'False'>(
    typeof initial?.correct_answer === 'string' && (initial.correct_answer === 'True' || initial.correct_answer === 'False')
      ? initial.correct_answer
      : 'True'
  )
  const [correctSA, setCorrectSA] = useState<string>(
    type === 'short_answer' && typeof initial?.correct_answer === 'string' ? initial.correct_answer : ''
  )
  const [explanation, setExplanation] = useState(initial?.explanation ?? '')

  const handleTypeChange = (newType: string) => {
    setType(newType as QuestionType)
    if (newType === 'mcq_single' || newType === 'mcq_multi') {
      if (options.length < 2) setOptions(['', ''])
    }
  }

  const addOption = () => setOptions([...options, ''])
  const updateOption = (i: number, val: string) => {
    const next = [...options]
    next[i] = val
    setOptions(next)
  }
  const removeOption = (i: number) => setOptions(options.filter((_, idx) => idx !== i))

  const toggleMultiCorrect = (i: number) => {
    setCorrectMulti(prev =>
      prev.includes(i) ? prev.filter(x => x !== i) : [...prev, i]
    )
  }

  const buildCorrectAnswer = (): number | number[] | string | null => {
    if (type === 'mcq_single') return correctSingle
    if (type === 'mcq_multi') return correctMulti
    if (type === 'true_false') return correctTF
    return correctSA || null
  }

  const handleSave = () => {
    onSave({
      type,
      prompt,
      options: (type === 'mcq_single' || type === 'mcq_multi') ? options : null,
      correct_answer: buildCorrectAnswer(),
      explanation,
    })
  }

  return (
    <div data-testid="question-form" style={{ border: '1px solid #e5e7eb', borderRadius: '8px', padding: '16px', marginBottom: '12px' }}>
      <div style={{ marginBottom: '12px' }}>
        <label style={{ fontSize: '12px', fontWeight: 600, color: '#374151', display: 'block', marginBottom: '4px' }}>
          Question Type
        </label>
        <Select
          data-testid="question-type-select"
          value={type}
          options={TYPE_OPTIONS}
          onChange={(e) => handleTypeChange(e.target.value)}
        />
      </div>

      <div style={{ marginBottom: '12px' }}>
        <label style={{ fontSize: '12px', fontWeight: 600, color: '#374151', display: 'block', marginBottom: '4px' }}>
          Question Prompt
        </label>
        <Textarea
          data-testid="question-prompt"
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder="Enter question text..."
          rows={2}
        />
      </div>

      {/* MCQ options */}
      {(type === 'mcq_single' || type === 'mcq_multi') && (
        <div style={{ marginBottom: '12px' }}>
          <label style={{ fontSize: '12px', fontWeight: 600, color: '#374151', display: 'block', marginBottom: '4px' }}>
            Answer Options {type === 'mcq_single' ? '(select correct one)' : '(select all correct)'}
          </label>
          {options.map((opt, i) => (
            <div key={i} style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
              {type === 'mcq_single' ? (
                <input
                  type="radio"
                  data-testid={`mcq-single-radio-${i}`}
                  name="correct-single"
                  checked={correctSingle === i}
                  onChange={() => setCorrectSingle(i)}
                />
              ) : (
                <input
                  type="checkbox"
                  data-testid={`mcq-multi-checkbox-${i}`}
                  checked={correctMulti.includes(i)}
                  onChange={() => toggleMultiCorrect(i)}
                />
              )}
              <Input
                data-testid={`option-input-${i}`}
                value={opt}
                onChange={(e) => updateOption(i, e.target.value)}
                placeholder={`Option ${i + 1}`}
              />
              {options.length > 2 && (
                <button
                  data-testid={`remove-option-${i}`}
                  onClick={() => removeOption(i)}
                  style={{ color: '#ef4444', background: 'none', border: 'none', cursor: 'pointer', fontSize: '16px' }}
                  aria-label={`Remove option ${i + 1}`}
                >
                  ×
                </button>
              )}
            </div>
          ))}
          {options.length < 5 && (
            <button
              data-testid="add-option-btn"
              onClick={addOption}
              style={{ fontSize: '12px', color: '#6366f1', background: 'none', border: 'none', cursor: 'pointer', padding: 0 }}
            >
              + Add option
            </button>
          )}
        </div>
      )}

      {/* True/False */}
      {type === 'true_false' && (
        <div style={{ marginBottom: '12px' }}>
          <label style={{ fontSize: '12px', fontWeight: 600, color: '#374151', display: 'block', marginBottom: '4px' }}>
            Correct Answer
          </label>
          <div style={{ display: 'flex', gap: '16px' }}>
            {(['True', 'False'] as const).map((val) => (
              <label key={val} style={{ display: 'flex', alignItems: 'center', gap: '6px', cursor: 'pointer' }}>
                <input
                  type="radio"
                  data-testid={`tf-radio-${val.toLowerCase()}`}
                  name="correct-tf"
                  value={val}
                  checked={correctTF === val}
                  onChange={() => setCorrectTF(val)}
                />
                <span style={{ fontSize: '13px' }}>{val}</span>
              </label>
            ))}
          </div>
        </div>
      )}

      {/* Short answer */}
      {type === 'short_answer' && (
        <div style={{ marginBottom: '12px' }}>
          <label style={{ fontSize: '12px', fontWeight: 600, color: '#374151', display: 'block', marginBottom: '4px' }}>
            Sample Correct Answer (optional — for manual grading reference)
          </label>
          <Input
            data-testid="short-answer-input"
            value={correctSA}
            onChange={(e) => setCorrectSA(e.target.value)}
            placeholder="Model answer (optional)"
          />
        </div>
      )}

      {/* Explanation — present for all types */}
      <div style={{ marginBottom: '12px' }}>
        <label style={{ fontSize: '12px', fontWeight: 600, color: '#374151', display: 'block', marginBottom: '4px' }}>
          Explanation (shown after answer)
        </label>
        <Textarea
          data-testid="question-explanation"
          value={explanation}
          onChange={(e) => setExplanation(e.target.value)}
          placeholder="Why is this the correct answer?"
          rows={2}
        />
      </div>

      <div style={{ display: 'flex', gap: '8px' }}>
        <Button data-testid="save-question-btn" onClick={handleSave}>Save Question</Button>
        <Button data-testid="cancel-question-btn" onClick={onCancel} variant="secondary">Cancel</Button>
      </div>
    </div>
  )
}
