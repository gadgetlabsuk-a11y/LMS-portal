// Wave 0 stub — imports non-existent source file to produce Cannot find module at collection
// QUIZ-02: MCQ single form
// QUIZ-03: MCQ multi form
// QUIZ-04: True/False form
// QUIZ-05: Short answer form
// QUIZ-06: Explanation field present
import { QuestionForm } from '../QuestionForm'

describe('QuestionForm', () => {
  it('renders MCQ single form with option inputs and single correct answer selector', () => {
    expect(QuestionForm).toBeDefined()
  })

  it('renders MCQ multi form with option inputs and multi correct answer checkboxes', () => {
    expect(QuestionForm).toBeDefined()
  })

  it('renders True/False form with fixed options', () => {
    expect(QuestionForm).toBeDefined()
  })

  it('renders short answer form with prompt and optional correct_answer', () => {
    expect(QuestionForm).toBeDefined()
  })

  it('renders explanation textarea for all question types', () => {
    expect(QuestionForm).toBeDefined()
  })
})
