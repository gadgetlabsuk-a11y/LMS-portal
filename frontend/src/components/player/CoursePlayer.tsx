import { useEffect, useMemo, useState } from 'react'
import { API_BASE } from '@/services/api'
import { coursePlayerApi, type PlayerCourse, type PlayerSlide, type PlayerQuiz } from '@/services/coursePlayerApi'
import { useSegmentAutoplay } from '@/hooks/useSegmentAutoplay'
import { SlideBlockView } from './SlideBlockView'
import { QuizRunner } from './QuizRunner'

type Step = { kind: 'slide'; slide: PlayerSlide } | { kind: 'quiz'; quiz: PlayerQuiz }

export function CoursePlayer({ courseId, mode, onExit }: { courseId: number; mode: 'learner' | 'preview'; onExit?: () => void }) {
  const [course, setCourse] = useState<PlayerCourse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [idx, setIdx] = useState(0)
  const [playing, setPlaying] = useState(true)
  const [unlocked, setUnlocked] = useState<Set<number>>(new Set())

  useEffect(() => {
    const load = mode === 'learner' ? coursePlayerApi.getLearnerPlayer(courseId) : coursePlayerApi.getPreviewTree(courseId)
    load.then(setCourse).catch((e) => setError(e instanceof Error ? e.message : 'Failed to load course'))
  }, [courseId, mode])

  const steps: Step[] = useMemo(() => {
    if (!course) return []
    const out: Step[] = []
    for (const m of course.modules) {
      for (const v of m.videos) {
        for (const s of v.slides) out.push({ kind: 'slide', slide: s })
        for (const q of v.quizzes || []) out.push({ kind: 'quiz', quiz: q })
      }
      for (const q of m.quizzes || []) out.push({ kind: 'quiz', quiz: q })
    }
    return out
  }, [course])

  const step = steps[Math.min(idx, steps.length - 1)]
  const slideStep = step && step.kind === 'slide' ? step.slide : null
  const isLast = idx >= steps.length - 1

  // A quiz step is locked (blocks Next) only for a learner with attempts still
  // available who hasn't yet passed/resolved it. Already-passed or already-
  // exhausted quizzes (from the server load) are NOT locked. Preview never gates.
  const quizLocked = !!(
    mode === 'learner' &&
    step && step.kind === 'quiz' &&
    !unlocked.has(idx) &&
    !step.quiz.passed &&
    step.quiz.attempts_remaining > 0
  )

  const advance = () => setIdx((i) => Math.min(steps.length - 1, i + 1))
  const onQuizResolved = (passed: boolean) => {
    setUnlocked((s) => new Set(s).add(idx))
    if (passed) advance()
  }
  const { ref: mediaRef, onEnded } = useSegmentAutoplay({
    playing, index: idx, mediaUrl: slideStep?.narration_audio_url ?? null,
    text: null, isLast, onAdvance: advance, enableTimer: false,
  })

  useEffect(() => {
    if (mode !== 'learner' || !slideStep) return
    void coursePlayerApi.postProgress(courseId, slideStep.id).catch(() => {})
  }, [mode, courseId, slideStep?.id])

  if (error) return <div className="h-full flex items-center justify-center bg-gray-900 text-gray-300">{error}</div>
  if (!course) return <div className="h-full flex items-center justify-center bg-gray-900 text-gray-400">Loading…</div>
  if (steps.length === 0) return <div className="h-full flex items-center justify-center bg-gray-900 text-gray-300">This course has no content yet.</div>

  return (
    <div className="h-full flex flex-col bg-gray-900 text-gray-100">
      <div className="bg-gray-800 px-6 py-2 text-xs text-gray-400 flex justify-between items-center">
        <span>{course.title}{mode === 'preview' && ' · preview'}</span>
        <div className="flex items-center gap-3">
          <span>Step {idx + 1} / {steps.length}</span>
          {mode === 'learner' && onExit && (
            <button onClick={onExit} className="px-2 py-1 rounded bg-gray-700 hover:bg-gray-600 text-gray-100">Exit ✕</button>
          )}
        </div>
      </div>
      <div className="flex-1 flex flex-col items-center justify-center p-6 gap-4">
        {step.kind === 'slide' ? (
          <div className="w-full max-w-3xl space-y-3">
            {step.slide.blocks.map((b) => <SlideBlockView key={b.id} block={b} />)}
          </div>
        ) : (
          <QuizRunner quiz={step.quiz} mode={mode} onResolved={onQuizResolved} />
        )}
      </div>
      {slideStep?.narration_audio_url && (
        <div className="bg-gray-800 px-6 pt-3">
          <audio key={`a-${idx}`} ref={mediaRef as React.RefObject<HTMLAudioElement>} controls onEnded={onEnded}
                 src={`${API_BASE}${slideStep.narration_audio_url}`} className="block w-full max-w-3xl mx-auto" />
        </div>
      )}
      <div className="bg-gray-800 px-6 py-3 flex items-center justify-center gap-3">
        <button onClick={() => setIdx((i) => Math.max(0, i - 1))} disabled={idx === 0}
                className="px-3 py-2 rounded bg-gray-700 disabled:opacity-40 text-sm">◀ Prev</button>
        {slideStep && (
          <button onClick={() => setPlaying((p) => !p)} className="px-3 py-2 rounded bg-gray-700 text-sm">
            {playing ? 'Pause' : 'Play'}
          </button>
        )}
        <button onClick={advance} disabled={isLast || quizLocked}
                className="px-4 py-2 rounded bg-indigo-600 disabled:opacity-40 text-sm">Next ▶</button>
        {isLast && (mode === 'learner' && onExit
          ? <button onClick={onExit} className="px-4 py-2 rounded bg-emerald-600 hover:bg-emerald-500 text-sm ml-2">Finish ✓</button>
          : <span className="text-emerald-400 text-sm ml-2">End of course</span>)}
      </div>
    </div>
  )
}
