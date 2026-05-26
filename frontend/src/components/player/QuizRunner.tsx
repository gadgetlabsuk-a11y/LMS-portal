import { useState } from 'react'
import { coursePlayerApi, type PlayerQuiz, type AttemptResult } from '@/services/coursePlayerApi'

export function QuizRunner({
  quiz,
  mode,
  onResolved,
}: {
  quiz: PlayerQuiz
  mode: 'learner' | 'preview'
  onResolved: (passed: boolean) => void
}) {
  const [answers, setAnswers] = useState<Record<string, unknown>>({})
  const [result, setResult] = useState<AttemptResult | null>(null)
  const [remaining, setRemaining] = useState(quiz.attempts_remaining)
  const [busy, setBusy] = useState(false)
  const preview = mode === 'preview'

  const setSingle = (qid: number, idx: number) => setAnswers((a) => ({ ...a, [qid]: idx }))
  const toggleMulti = (qid: number, idx: number) => setAnswers((a) => {
    const cur = Array.isArray(a[qid]) ? (a[qid] as number[]) : []
    return { ...a, [qid]: cur.includes(idx) ? cur.filter((x) => x !== idx) : [...cur, idx] }
  })

  const submit = async () => {
    setBusy(true)
    try {
      const res = await coursePlayerApi.submitAttempt(quiz.id, answers)
      setResult(res); setRemaining(res.attempts_remaining)
      if (res.passed) onResolved(true)
      else if (res.attempts_remaining === 0) onResolved(false)
    } finally { setBusy(false) }
  }

  if (result) {
    return (
      <div className="max-w-2xl mx-auto p-6 text-center text-gray-100">
        <h3 className="text-xl font-bold mb-2">{result.passed ? 'Passed ✓' : 'Not passed'}</h3>
        <p className="mb-4">Score: {result.score}% (pass mark {quiz.pass_rate}%)</p>
        {!result.passed && remaining > 0 && (
          <button onClick={() => { setResult(null); setAnswers({}) }} className="px-4 py-2 rounded bg-indigo-600 text-white">
            Retake ({remaining} left)
          </button>
        )}
        {!result.passed && remaining === 0 && <p className="text-amber-400">No attempts remaining.</p>}
      </div>
    )
  }

  return (
    <div className="max-w-2xl mx-auto p-6 text-gray-100">
      <h3 className="text-xl font-bold mb-4">{quiz.title}</h3>
      {preview && (
        <p className="mb-4 text-sm text-amber-400">Preview — quiz is not scored.</p>
      )}
      {quiz.questions.map((q) => (
        <div key={q.id} className="mb-5">
          <p className="font-medium mb-2">{q.prompt}</p>
          {(q.options ?? []).map((opt, idx) => (
            <label key={idx} className="flex items-center gap-2 mb-1">
              <input
                type={q.type === 'mcq_multi' ? 'checkbox' : 'radio'}
                name={`q-${q.id}`}
                aria-label={opt}
                disabled={preview}
                onChange={() => (q.type === 'mcq_multi' ? toggleMulti(q.id, idx) : setSingle(q.id, idx))}
              />
              {opt}
            </label>
          ))}
          {q.type === 'true_false' && (q.options == null) && (
            ['True', 'False'].map((tf) => (
              <label key={tf} className="flex items-center gap-2 mb-1">
                <input type="radio" name={`q-${q.id}`} aria-label={tf} disabled={preview} onChange={() => setAnswers((a) => ({ ...a, [q.id]: tf }))} />
                {tf}
              </label>
            ))
          )}
          {q.type === 'short_answer' && (
            <input
              type="text"
              aria-label={q.prompt}
              disabled={preview}
              className="w-full px-3 py-2 rounded bg-gray-800 text-gray-100 border border-gray-600 disabled:opacity-50"
              onChange={(e) => setAnswers((a) => ({ ...a, [q.id]: e.target.value }))}
            />
          )}
        </div>
      ))}
      {!preview && (
        <button onClick={() => void submit()} disabled={busy} className="px-5 py-2 rounded bg-indigo-600 text-white disabled:opacity-50">
          {busy ? 'Submitting…' : 'Submit'}
        </button>
      )}
    </div>
  )
}
