import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'

/**
 * ILB (Interactive Learning Broadcast) player — SCAFFOLD.
 *
 * Demonstrates the structure + interaction state machine from
 * docs/superpowers/specs/2026-05-21-ilb-design.md:
 *   - Hybrid avatar: pre-rendered video for the scripted podcast, live HeyGen stream for Q&A.
 *   - Two modes: interrupt (pause → answer live → resume) and defer (queue → batch at segment end).
 *   - Bi-modal input (voice via Deepgram / text), captions, transcript, audit-logged interactions.
 *
 * The avatar video, LiveKit live stream, Deepgram STT, and grounded Q&A are STUBBED here — they
 * wire in once the backend routes exist and HeyGen/Deepgram/ElevenLabs keys are configured.
 * Search "DEMO STUB" for the wiring points.
 */

type Mode = 'interrupt' | 'defer'
type PlayerState = 'idle' | 'playing' | 'paused' | 'listening' | 'answering'

interface TranscriptEntry {
  role: 'host' | 'learner' | 'system'
  text: string
  escalated?: boolean
}

export const ILBPlayerPage = () => {
  const { id: courseId } = useParams<{ id: string }>()
  const navigate = useNavigate()

  const [mode, setMode] = useState<Mode>('interrupt')
  const [state, setState] = useState<PlayerState>('idle')
  const [captionsOn, setCaptionsOn] = useState(true)
  const [question, setQuestion] = useState('')
  const [queued, setQueued] = useState<string[]>([])
  const [transcript, setTranscript] = useState<TranscriptEntry[]>([
    { role: 'system', text: `Welcome — choose Interrupt or Defer, then press play. (Course #${courseId})` },
  ])

  const liveAvatar = state === 'listening' || state === 'answering'

  function push(entry: TranscriptEntry) {
    setTranscript((t) => [...t, entry])
  }

  // DEMO STUB: real impl POSTs to /api/ilb/sessions/:id/ask → qa_service (grounded + guarded),
  // streams the answer through live TTS, and drives the live HeyGen avatar over LiveKit.
  // The guardrail (cite / refuse / escalate) is enforced server-side by qa_service.
  async function answerLive(q: string) {
    push({ role: 'learner', text: q })
    setState('answering')
    push({
      role: 'host',
      text: '[stub] Grounded answer will appear here, spoken by the live avatar. Wires to qa_service + live TTS + HeyGen.',
    })
    setState('playing')
  }

  function handleAsk() {
    const q = question.trim()
    if (!q) return
    setQuestion('')
    if (mode === 'interrupt') {
      setState('paused')
      void answerLive(q)
    } else {
      setQueued((qs) => [...qs, q])
      push({ role: 'system', text: `Queued: "${q}" — will be answered at the next segment break.` })
    }
  }

  // DEMO STUB: defer mode batch-answers queued questions at a segment boundary.
  function flushQueue() {
    if (queued.length === 0) return
    setState('answering')
    queued.forEach((q) => {
      push({ role: 'learner', text: q })
      push({ role: 'host', text: '[stub] Batched answer (qa_service + live avatar).' })
    })
    setQueued([])
    setState('playing')
  }

  // DEMO STUB: tap-to-talk → Deepgram streaming STT → fills the question box.
  function startVoiceCapture() {
    setState('listening')
    push({ role: 'system', text: '[stub] Listening… (Deepgram STT). Type a question to simulate.' })
  }

  return (
    <div className="min-h-screen flex flex-col bg-gray-900 text-gray-100">
      {/* Top bar */}
      <div className="bg-gray-800 px-6 py-3 flex items-center justify-between flex-shrink-0">
        <button
          onClick={() => navigate(-1)}
          className="text-gray-300 hover:text-white text-sm flex items-center gap-1"
        >
          ← Back
        </button>
        <span className="text-gray-300 text-sm font-medium">Interactive Learning Broadcast</span>
        <div className="flex items-center gap-2 text-xs">
          <span className="text-gray-400">Mode:</span>
          {(['interrupt', 'defer'] as Mode[]).map((m) => (
            <button
              key={m}
              onClick={() => setMode(m)}
              className={`px-2 py-1 rounded ${
                mode === m ? 'bg-indigo-600 text-white' : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
              }`}
            >
              {m === 'interrupt' ? 'Interrupt' : 'Defer'}
            </button>
          ))}
        </div>
      </div>

      <div className="flex flex-1 min-h-0">
        {/* Avatar stage */}
        <div className="flex-1 flex flex-col items-center justify-center p-6 gap-4">
          <div className="relative w-full max-w-2xl aspect-video rounded-lg overflow-hidden bg-black flex items-center justify-center">
            {/* DEMO STUB: pre-rendered avatar <video> for the scripted podcast goes here;
                during Q&A this swaps to the LiveKit live-avatar stream of the same persona. */}
            <span className="text-gray-500 text-sm text-center px-6">
              {liveAvatar
                ? '● LIVE avatar (HeyGen streaming over LiveKit) — answering'
                : 'Pre-rendered avatar video (scripted podcast)'}
            </span>
            <span
              className={`absolute top-3 left-3 text-[10px] px-2 py-0.5 rounded-full ${
                liveAvatar ? 'bg-red-600' : 'bg-gray-700'
              }`}
            >
              {liveAvatar ? 'LIVE' : 'PRE-RENDERED'}
            </span>
          </div>

          {captionsOn && (
            <div className="w-full max-w-2xl min-h-[2.5rem] rounded bg-black/60 px-4 py-2 text-center text-sm">
              {/* DEMO STUB: synced captions (WCAG 2.2 AA) */}
              {transcript[transcript.length - 1]?.text ?? ''}
            </div>
          )}

          {/* Transport + ask controls */}
          <div className="flex flex-wrap items-center justify-center gap-2">
            <button
              onClick={() => setState((s) => (s === 'playing' ? 'paused' : 'playing'))}
              className="px-4 py-2 rounded bg-gray-700 hover:bg-gray-600 text-sm"
            >
              {state === 'playing' ? 'Pause' : 'Play'}
            </button>
            <button
              onClick={startVoiceCapture}
              className="px-4 py-2 rounded bg-indigo-600 hover:bg-indigo-500 text-sm"
            >
              🎤 Ask (voice)
            </button>
            {mode === 'defer' && (
              <button
                onClick={flushQueue}
                disabled={queued.length === 0}
                className="px-4 py-2 rounded bg-amber-600 hover:bg-amber-500 disabled:opacity-40 text-sm"
              >
                Answer queued ({queued.length})
              </button>
            )}
            <button
              onClick={() => setCaptionsOn((c) => !c)}
              className="px-3 py-2 rounded bg-gray-700 hover:bg-gray-600 text-xs"
            >
              CC {captionsOn ? 'on' : 'off'}
            </button>
          </div>

          {/* Text question input */}
          <form
            onSubmit={(e) => {
              e.preventDefault()
              handleAsk()
            }}
            className="w-full max-w-2xl flex gap-2"
          >
            <input
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="Type a question…"
              className="flex-1 rounded bg-gray-800 border border-gray-700 px-3 py-2 text-sm focus:outline-none focus:border-indigo-500"
            />
            <button type="submit" className="px-4 py-2 rounded bg-indigo-600 hover:bg-indigo-500 text-sm">
              {mode === 'interrupt' ? 'Ask now' : 'Queue'}
            </button>
          </form>
          <p className="text-[11px] text-gray-500">State: {state} · Q&amp;A is a learning aid; comprehension is assessed by the knowledge checks.</p>
        </div>

        {/* Transcript / queue panel */}
        <aside className="w-80 flex-shrink-0 border-l border-gray-800 flex flex-col min-h-0">
          <div className="px-4 py-2 border-b border-gray-800 text-xs uppercase tracking-wide text-gray-400">
            Transcript
          </div>
          <div className="flex-1 overflow-y-auto p-3 space-y-2 text-sm">
            {transcript.map((e, i) => (
              <div
                key={i}
                className={
                  e.role === 'learner'
                    ? 'text-indigo-300'
                    : e.role === 'system'
                    ? 'text-gray-500 italic'
                    : 'text-gray-100'
                }
              >
                <span className="text-[10px] uppercase mr-1 text-gray-500">{e.role}</span>
                {e.text}
                {e.escalated && <span className="ml-1 text-amber-400 text-[10px]">(escalated)</span>}
              </div>
            ))}
          </div>
          {mode === 'defer' && queued.length > 0 && (
            <div className="border-t border-gray-800 p-3 text-xs text-amber-300">
              {queued.length} question(s) queued
            </div>
          )}
        </aside>
      </div>
    </div>
  )
}
