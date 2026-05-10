import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { QuestionForm } from '../QuestionForm'

describe('QuestionForm', () => {
  it('renders MCQ single form with option inputs and single correct answer radio', () => {
    render(<QuestionForm onSave={vi.fn()} onCancel={vi.fn()} />)
    expect(screen.getByTestId('question-type-select')).toBeDefined()
    expect(screen.getByTestId('mcq-single-radio-0')).toBeDefined()
    expect(screen.getByTestId('option-input-0')).toBeDefined()
  })

  it('shows MCQ multi checkboxes when type is mcq_multi', () => {
    render(<QuestionForm initial={{ type: 'mcq_multi' }} onSave={vi.fn()} onCancel={vi.fn()} />)
    expect(screen.getByTestId('mcq-multi-checkbox-0')).toBeDefined()
    expect(screen.getByTestId('mcq-multi-checkbox-1')).toBeDefined()
  })

  it('renders True/False radio buttons', () => {
    render(<QuestionForm initial={{ type: 'true_false' }} onSave={vi.fn()} onCancel={vi.fn()} />)
    expect(screen.getByTestId('tf-radio-true')).toBeDefined()
    expect(screen.getByTestId('tf-radio-false')).toBeDefined()
  })

  it('renders short answer form with prompt and optional correct answer input', () => {
    render(<QuestionForm initial={{ type: 'short_answer' }} onSave={vi.fn()} onCancel={vi.fn()} />)
    expect(screen.getByTestId('short-answer-input')).toBeDefined()
  })

  it('renders explanation textarea for all question types', () => {
    const { rerender } = render(<QuestionForm onSave={vi.fn()} onCancel={vi.fn()} />)
    expect(screen.getByTestId('question-explanation')).toBeDefined()
    rerender(<QuestionForm initial={{ type: 'true_false' }} onSave={vi.fn()} onCancel={vi.fn()} />)
    expect(screen.getByTestId('question-explanation')).toBeDefined()
  })

  it('calls onSave with integer correct_answer for mcq_single', () => {
    const onSave = vi.fn()
    render(<QuestionForm onSave={onSave} onCancel={vi.fn()} />)
    fireEvent.click(screen.getByTestId('save-question-btn'))
    expect(onSave).toHaveBeenCalledWith(expect.objectContaining({
      type: 'mcq_single',
      correct_answer: expect.any(Number),
    }))
  })

  it('calls onCancel when Cancel is clicked', () => {
    const onCancel = vi.fn()
    render(<QuestionForm onSave={vi.fn()} onCancel={onCancel} />)
    fireEvent.click(screen.getByTestId('cancel-question-btn'))
    expect(onCancel).toHaveBeenCalled()
  })
})
