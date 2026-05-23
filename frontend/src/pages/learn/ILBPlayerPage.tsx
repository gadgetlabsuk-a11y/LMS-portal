import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ilbApi, type LiveTransport } from '@/services/ilbApi'

/**
 * ILB (Interactive Learning Broadcast) player.
 *
 * Bucket A (wired to the backend): session lifecycle + grounded/guarded TEXT Q&A + completion +
 * audit sealing, via /api/ilb/* (services/qa_service, audit_service).
 *
 * Bucket B (still stubbed — needs HeyGen/Deepgram/ElevenLabs keys): the avatar video + live
 * stream, voice input (STT), and spoken-answer audio (live TTS). Those regions are placeholders.
 *
 * See docs/superpowers/specs/2026-05-21-ilb-design.md.
 */

type Mode = 'interrupt' | 'defer'
type PlayerState = 'idle' | 'playing' | 'paused' | 'listening' | 'answering'

interface TranscriptEntry {
  role: 'host' | 'learner' | 'system'
  text: string
  escalated?: boolean
  sourceRefs?: string[]
  disclaimer?: string
}

export const ILBPlayerPage = () => {
  const { id } = useParams<{ id: string }>()
  const courseId = Number(id)
  const navigate = useNavigate()

  const [mode, setMode] = useState<Mode>('interrupt')
  const [sessionId, setSessionId] = useState<number | null>(null)
  const [live, setLive] = useState<LiveTransport | null>(null)
  const [state, setState] = useState<PlayerState>('idle')
  const [starting, setStarting] = useState(false)
  const [asking, setAsking] = useState(false)
  const [completing, setCompleting] = useState(false)
  const [completed, setCompleted] = useState(false)
  const [captionsOn, setCaptionsOn] = useState(true)
  const [question, setQuestion] = useState('')
  const [queued, setQueued] = useState<string[]>([])
  const [error, setError] = useState<string | null>(null)
  const [transcript, setTranscript] = useState<TranscriptEntry[]>([
    { role: 'system', text: `Choose a mode and start the broadcast. (Course #${id})` },
  ])

  const liveAvatar = state === 'listening' || state === 'answering'

  function push(entry: TranscriptEntry) {
    setTranscript((t) => [...t, entry])
  }

  async function startBroadcast() {
    if (!Number.isFinite(courseId)) {
      setError('Invalid course id.')
      return
    }
    setStarting(true)
    setError(null)
    try {
      const { session, live: transport } = await ilbApi.startSession(courseId, mode)
      setSessionId(session.id)
      setLive(transport)
      setState('playing')
      push({ role: 'system', text: `Broadcast started (${mode} mode). Avatar/voice are stubbed pending keys; text Q&A is live.` })
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to start session')
    } finally {
      setStarting(false)
    }
  }

  // Real grounded/guarded answer (qa_service). Q&A is a learning aid — escalations don't block.
  async function askBackend(q: string) {
    if (sessionId == null) return
    push({ role: 'learner', text: q })
    setAsking(true)
    setState('answering')
    try {
      const res = await ilbApi.ask(sessionId, q, 'text')
      push({
        role: 'host',
        text: res.answer,
        escalated: res.escalated,
        sourceRefs: res.source_refs,
        disclaimer: res.disclaimer,
      })
    } catch (e) {
      push({ role: 'system', text: `Q&A failed: ${e instanceof Error ? e.message : 'error'}` })
    } finally {
      setAsking(false)
      setState('playing')
    }
  }

  function handleAsk() {
    const q = question.trim()
    if (!q || sessionId == null) return
    setQuestion('')
    if (mode === 'interrupt') {
      setState('paused')
      void askBackend(q)
    } else {
      setQueued((qs) => [...qs, q])
      push({ role: 'system', text: `Queued: "${q}" — will be answered at the next segment break.` })
    }
  }

  // Defer mode: answer all queued questions in sequence (no batch endpoint server-side).
  async function flushQueue() {
    if (queued.length === 0 || sessionId == null) return
    const pending = [...queued]
    setQueued([])
    for (const q of pending) {
      await askBackend(q)
    }
  }

  async function finish() {
    if (sessionId == null) return
    setCompleting(true)
    setError(null)
    try {
      const { attestation } = await ilbApi.complete(sessionId)
      setCompleted(true)
      setState('idle')
      push({ role: 'system', text: `Session completed and sealed (audit chain #${attestation.sequence}, hash ${attestation.content_hash.slice(0, 12)}…).` })
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to complete session')
    } finally {
      setCompleting(false)
    }
  }

  // Bucket B stub: real impl streams Deepgram STT into the question box.
  function startVoiceCapture() {
    push({ role: 'system', text: '[stub] Voice input (Deepgram STT) arrives with API keys. Type your question for now.' })
  }

  const started = sessionId != null

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
              onClick={() => !started && setMode(m)}
              disabled={started}
              className={`px-2 py-1 rounded ${
                mode === m ? 'bg-indigo-600 text-white' : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
              } ${started ? 'opacity-60 cursor-not-allowed' : ''}`}
            >
              {m === 'interrupt' ? 'Interrupt' : 'Defer'}
            </button>
          ))}
        </div>
      </div>

      {error && (
        <div className="bg-red-900/60 text-red-200 text-sm px-6 py-2">{error}</div>
      )}

      <div className="flex flex-1 min-h-0">
        {/* Avatar stage */}
        <div className="flex-1 flex flex-col items-center justify-center p-6 gap-4">
          <div className="relative w-full max-w-2xl aspect-video rounded-lg overflow-hidden bg-black flex items-center justify-center">
            {/* Bucket B: pre-rendered avatar <video> / live LiveKit stream goes here. */}
            <span className="text-gray-500 text-sm text-center px-6">
              {liveAvatar
                ? '● LIVE avatar (HeyGen streaming) — stubbed pending keys'
                : 'Pre-rendered avatar video — stubbed pending keys'}
            </span>
            <span
              className={`absolute top-3 left-3 text-[10px] px-2 py-0.5 rounded-full ${
                liveAvatar ? 'bg-red-600' : 'bg-gray-700'
              }`}
            >
              {liveAvatar ? 'LIVE' : 'PRE-RENDERED'}
            </span>
            {live && (
              <span className="absolute bottom-3 right-3 text-[10px] text-gray-500">
                transport: {live.provider}
              </span>
            )}
          </div>

          {captionsOn && (
            <div className="w-full max-w-2xl min-h-[2.5rem] rounded bg-black/60 px-4 py-2 text-center text-sm">
              {transcript[transcript.length - 1]?.text ?? ''}
            </div>
          )}

          {!started ? (
            <button
              onClick={startBroadcast}
              disabled={starting}
              className="px-6 py-2 rounded bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-sm font-medium"
            >
              {starting ? 'Starting…' : 'Start broadcast'}
            </button>
          ) : (
            <>
              {/* Transport + ask controls */}
              <div className="flex flex-wrap items-center justify-center gap-2">
                <button
                  onClick={() => setState((s) => (s === 'playing' ? 'paused' : 'playing'))}
                  disabled={completed}
                  className="px-4 py-2 rounded bg-gray-700 hover:bg-gray-600 disabled:opacity-40 text-sm"
                >
                  {state === 'playing' ? 'Pause' : 'Play'}
                </button>
                <button
                  onClick={startVoiceCapture}
                  className="px-4 py-2 rounded bg-gray-700 hover:bg-gray-600 text-sm"
                  title="Voice input arrives with API keys"
                >
                  🎤 Ask (voice) ·stub
                </button>
                {mode === 'defer' && (
                  <button
                    onClick={() => void flushQueue()}
                    disabled={queued.length === 0 || asking}
                    className="px-4 py-2 rounded bg-amber-600 hover:bg-amber-500 disabled:opacity-40 text-sm"
                  >
                    Answer queued ({queued.length})
                  </button>
                )}
                <button
                  onClick={() => void finish()}
                  disabled={completing || completed}
                  className="px-4 py-2 rounded bg-emerald-700 hover:bg-emerald-600 disabled:opacity-40 text-sm"
                >
                  {completed ? 'Completed ✓' : completing ? 'Finishing…' : 'Finish'}
                </button>
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
                  placeholder={asking ? 'Answering…' : 'Type a question…'}
                  disabled={asking || completed}
                  className="flex-1 rounded bg-gray-800 border border-gray-700 px-3 py-2 text-sm focus:outline-none focus:border-indigo-500 disabled:opacity-50"
                />
                <button
                  type="submit"
                  disabled={asking || completed || !question.trim()}
                  className="px-4 py-2 rounded bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 text-sm"
                >
                  {mode === 'interrupt' ? (asking ? '…' : 'Ask now') : 'Queue'}
                </button>
              </form>
            </>
          )}
          <p className="text-[11px] text-gray-500">
            State: {state} · Q&amp;A is a learning aid; comprehension is assessed by the knowledge checks.
          </p>
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
                {e.sourceRefs && e.sourceRefs.length > 0 && (
                  <div className="mt-1 text-[10px] text-gray-500">
                    cites: {e.sourceRefs.map((s) => `“${s}”`).join(' · ')}
                  </div>
                )}
                {e.disclaimer && <div className="mt-0.5 text-[10px] text-gray-600 italic">{e.disclaimer}</div>}
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
