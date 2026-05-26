import { useEffect, useRef, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { API_BASE } from '@/services/api'
import { ilbApi, type LiveTransport } from '@/services/ilbApi'
import { useSegmentAutoplay } from '@/hooks/useSegmentAutoplay'

/**
 * ILB (Interactive Learning Broadcast) player.
 *
 * Wired to the backend: loads the course's saved broadcast (script + avatar config), runs the
 * session lifecycle, and answers TEXT questions via the grounded/guarded Q&A. Learners only reach
 * a published broadcast; creators/admins can preview a draft.
 *
 * Bucket B (stubbed pending HeyGen/Deepgram/ElevenLabs keys): the avatar video + live stream,
 * voice input (STT), and spoken-answer audio (live TTS). The script renders as on-screen narration
 * in the meantime. See docs/superpowers/specs/2026-05-21-ilb-design.md.
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

export const ILBPlayerPage = ({ kind = 'course' }: { kind?: 'course' | 'broadcast' }) => {
  const { id } = useParams<{ id: string }>()
  const targetId = Number(id)
  const navigate = useNavigate()

  const [configLoading, setConfigLoading] = useState(true)
  const [available, setAvailable] = useState(false)
  const [segments, setSegments] = useState<string[]>([])
  const [segmentAudio, setSegmentAudio] = useState<string[]>([])
  const [segmentVideo, setSegmentVideo] = useState<(string | null)[]>([])
  const [segIdx, setSegIdx] = useState(0)
  const [avatarId, setAvatarId] = useState<string | null>(null)
  const [draftPreview, setDraftPreview] = useState(false)

  const [mode, setMode] = useState<Mode>('interrupt')
  const [sessionId, setSessionId] = useState<number | null>(null)
  const [, setLive] = useState<LiveTransport | null>(null)
  const [state, setState] = useState<PlayerState>('idle')
  const [starting, setStarting] = useState(false)
  const [asking, setAsking] = useState(false)
  const [completing, setCompleting] = useState(false)
  const [completed, setCompleted] = useState(false)
  const [captionsOn, setCaptionsOn] = useState(true)
  const [question, setQuestion] = useState('')
  const [queued, setQueued] = useState<string[]>([])
  const [error, setError] = useState<string | null>(null)
  const [transcript, setTranscript] = useState<TranscriptEntry[]>([])
  const [recording, setRecording] = useState(false)
  const [answerAudioUrl, setAnswerAudioUrl] = useState<string | null>(null)
  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const chunksRef = useRef<Blob[]>([])
  const [nudgedFinish, setNudgedFinish] = useState(false)

  const liveAvatar = state === 'listening' || state === 'answering'

  // Load the course's saved broadcast config (gated server-side: learners only see published).
  useEffect(() => {
    if (!Number.isFinite(targetId)) {
      setConfigLoading(false)
      return
    }
    const load = kind === 'broadcast' ? ilbApi.getBroadcast(targetId) : ilbApi.getPodcast(targetId)
    load
      .then((cfg) => {
        setAvailable(true)
        setSegments(cfg.segments ?? [])
        setSegmentAudio(cfg.segment_audio ?? [])
        setSegmentVideo(cfg.segment_video ?? [])
        setAvatarId(cfg.avatar_id)
        setDraftPreview(!cfg.published)
        setTranscript([{ role: 'system', text: 'Choose a mode and start the broadcast.' }])
      })
      .catch(() => setAvailable(false))
      .finally(() => setConfigLoading(false))
  }, [targetId, kind])

  function push(entry: TranscriptEntry) {
    setTranscript((t) => [...t, entry])
  }

  async function startBroadcast() {
    setStarting(true)
    setError(null)
    try {
      const { session, live: transport } =
        kind === 'broadcast'
          ? await ilbApi.startBroadcastSession(targetId, mode)
          : await ilbApi.startSession(targetId, mode)
      setSessionId(session.id)
      setLive(transport)
      setState('playing')
      push({ role: 'system', text: `Broadcast started (${mode} mode). Avatar/voice are stubbed pending keys; the script narration and text Q&A are live.` })
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to start session')
    } finally {
      setStarting(false)
    }
  }

  async function askBackend(q: string, inputMode: 'text' | 'voice' = 'text') {
    if (sessionId == null) return
    push({ role: 'learner', text: q })
    setAsking(true)
    setState('answering')
    try {
      const res = await ilbApi.ask(sessionId, q, inputMode)
      push({ role: 'host', text: res.answer, escalated: res.escalated, sourceRefs: res.source_refs, disclaimer: res.disclaimer })
      if (res.answer_audio_url) setAnswerAudioUrl(res.answer_audio_url)
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
      push({ role: 'system', text: `Queued: "${q}" — answered at the next segment break.` })
    }
  }

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

  // Push-to-talk: click to record, click to stop → Deepgram transcribes → ask.
  async function toggleVoiceCapture() {
    if (recording) {
      mediaRecorderRef.current?.stop()
      return
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const mr = new MediaRecorder(stream)
      chunksRef.current = []
      mr.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data)
      }
      mr.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop())
        setRecording(false)
        setState('answering')
        const blob = new Blob(chunksRef.current, { type: mr.mimeType || 'audio/webm' })
        try {
          const { transcript } = await ilbApi.transcribe(blob)
          const q = transcript.trim()
          if (!q) {
            push({ role: 'system', text: "Didn't catch that — try again." })
            setState('playing')
            return
          }
          if (mode === 'interrupt') {
            setState('paused')
            void askBackend(q, 'voice')
          } else {
            setQueued((qs) => [...qs, q])
            push({ role: 'system', text: `Queued: "${q}"` })
            setState('playing')
          }
        } catch (e) {
          push({ role: 'system', text: `Transcription failed: ${e instanceof Error ? e.message : 'error'}` })
          setState('playing')
        }
      }
      mediaRecorderRef.current = mr
      mr.start()
      setRecording(true)
      setState('listening')
    } catch {
      push({ role: 'system', text: 'Microphone unavailable or permission denied.' })
    }
  }

  const started = sessionId != null
  const hasSegments = segments.length > 0
  const currentSegment = hasSegments ? segments[Math.min(segIdx, segments.length - 1)] : null
  const currentAudio = segmentAudio.length > 0 ? segmentAudio[Math.min(segIdx, segmentAudio.length - 1)] : null
  const currentVideo = segmentVideo.length > 0 ? segmentVideo[Math.min(segIdx, segmentVideo.length - 1)] : null

  // --- Autoplay / auto-advance (E-1) ---------------------------------------
  // Move to the next segment, flushing any deferred questions at the break.
  function advanceSegment() {
    setSegIdx((i) => Math.min(segments.length - 1, i + 1))
    if (mode === 'defer') void flushQueue()
  }

  const { ref: mediaRef, onEnded: handleSegmentEnded } = useSegmentAutoplay({
    playing: state === 'playing',
    index: segIdx,
    mediaUrl: currentVideo || currentAudio,
    text: currentSegment,
    isLast: segIdx >= segments.length - 1,
    onAdvance: advanceSegment,
  })

  // Reaching the last segment (manual or auto) nudges the learner to Finish.
  useEffect(() => {
    if (started && hasSegments && !completed && !nudgedFinish && segIdx >= segments.length - 1) {
      setNudgedFinish(true)
      push({ role: 'system', text: 'End of the broadcast — press Finish to complete.' })
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [started, hasSegments, completed, segIdx, segments.length, nudgedFinish])

  if (configLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-900 text-gray-400">Loading…</div>
    )
  }

  if (!available) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center bg-gray-900 text-gray-300 gap-4">
        <div className="text-5xl">🎙️</div>
        <p>{kind === 'broadcast' ? 'This broadcast isn’t published yet.' : 'This course doesn’t have a published broadcast yet.'}</p>
        <button onClick={() => navigate(-1)} className="text-indigo-400 hover:underline text-sm">← Back</button>
      </div>
    )
  }

  return (
    <div className="min-h-screen flex flex-col bg-gray-900 text-gray-100">
      {/* Top bar */}
      <div className="bg-gray-800 px-6 py-3 flex items-center justify-between flex-shrink-0">
        <button onClick={() => navigate(-1)} className="text-gray-300 hover:text-white text-sm flex items-center gap-1">
          ← Back
        </button>
        <span className="text-gray-300 text-sm font-medium">
          Interactive Learning Broadcast{draftPreview && <span className="ml-2 text-amber-400 text-xs">(draft preview)</span>}
        </span>
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

      {error && <div className="bg-red-900/60 text-red-200 text-sm px-6 py-2">{error}</div>}

      <div className="flex flex-1 min-h-0">
        {/* Avatar stage */}
        <div className="flex-1 flex flex-col items-center justify-center p-6 gap-4">
          <div className="relative w-full max-w-2xl aspect-video rounded-lg overflow-hidden bg-black flex items-center justify-center p-6">
            {started && currentSegment ? (
              // Keep the broadcast media MOUNTED during a Q&A so the play/pause effect
              // can pause it (and resume from the same position). Unmounting it here
              // meant it couldn't be paused and played under the spoken answer.
              <div className="w-full h-full flex flex-col gap-2 overflow-y-auto">
                {currentVideo ? (
                  <video
                    key={`v-${segIdx}`}
                    ref={mediaRef as unknown as React.RefObject<HTMLVideoElement>}
                    controls
                    onEnded={handleSegmentEnded}
                    src={`${API_BASE}${currentVideo}`}
                    className="w-full h-full object-contain"
                  />
                ) : (
                  <>
                    <p className="text-gray-200 text-sm leading-relaxed">{currentSegment}</p>
                    {currentAudio && (
                      <audio
                        key={`a-${segIdx}`}
                        ref={mediaRef as unknown as React.RefObject<HTMLAudioElement>}
                        controls
                        onEnded={handleSegmentEnded}
                        src={`${API_BASE}${currentAudio}`}
                        className="w-full mt-auto"
                      />
                    )}
                  </>
                )}
              </div>
            ) : (
              <span className="text-gray-500 text-sm text-center">
                {hasSegments ? 'Press play to begin the broadcast.' : 'No script saved for this course yet — text Q&A still works.'}
              </span>
            )}
            {liveAvatar && (
              <div className="absolute inset-0 flex items-center justify-center bg-black/70 pointer-events-none">
                <span className="text-gray-200 text-sm text-center px-4">
                  ● {state === 'listening' ? 'Listening…' : 'Answering your question'} — broadcast paused
                </span>
              </div>
            )}
            <span className={`absolute top-3 left-3 text-[10px] px-2 py-0.5 rounded-full ${liveAvatar ? 'bg-red-600' : 'bg-gray-700'}`}>
              {liveAvatar ? 'LIVE' : 'PRE-RENDERED'}
            </span>
            {avatarId && <span className="absolute bottom-3 right-3 text-[10px] text-gray-500">avatar: {avatarId}</span>}
          </div>

          {captionsOn && (
            <div className="w-full max-w-2xl min-h-[2.5rem] rounded bg-black/60 px-4 py-2 text-center text-sm">
              {liveAvatar ? transcript[transcript.length - 1]?.text ?? '' : currentSegment ?? ''}
            </div>
          )}

          {answerAudioUrl && (
            <audio key={answerAudioUrl} autoPlay controls src={`${API_BASE}${answerAudioUrl}`} className="w-full max-w-2xl" />
          )}

          {!started ? (
            <button
              onClick={() => void startBroadcast()}
              disabled={starting}
              className="px-6 py-2 rounded bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-sm font-medium"
            >
              {starting ? 'Starting…' : 'Start broadcast'}
            </button>
          ) : (
            <>
              <div className="flex flex-wrap items-center justify-center gap-2">
                <button
                  onClick={() => setState((s) => (s === 'playing' ? 'paused' : 'playing'))}
                  disabled={completed}
                  className="px-4 py-2 rounded bg-gray-700 hover:bg-gray-600 disabled:opacity-40 text-sm"
                >
                  {state === 'playing' ? 'Pause' : 'Play'}
                </button>
                {hasSegments && (
                  <>
                    <button
                      onClick={() => setSegIdx((i) => Math.max(0, i - 1))}
                      disabled={segIdx === 0}
                      className="px-3 py-2 rounded bg-gray-700 hover:bg-gray-600 disabled:opacity-40 text-sm"
                    >
                      ◀ Prev
                    </button>
                    <span className="text-xs text-gray-400">Segment {Math.min(segIdx + 1, segments.length)}/{segments.length}</span>
                    <button
                      onClick={() => {
                        setSegIdx((i) => Math.min(segments.length - 1, i + 1))
                        if (mode === 'defer') void flushQueue()
                      }}
                      disabled={segIdx >= segments.length - 1}
                      className="px-3 py-2 rounded bg-gray-700 hover:bg-gray-600 disabled:opacity-40 text-sm"
                    >
                      Next ▶
                    </button>
                  </>
                )}
                <button
                  onClick={() => void toggleVoiceCapture()}
                  disabled={asking || completed}
                  className={`px-4 py-2 rounded text-sm disabled:opacity-40 ${recording ? 'bg-red-600 hover:bg-red-500' : 'bg-gray-700 hover:bg-gray-600'}`}
                >
                  {recording ? '⏹ Stop' : '🎤 Speak'}
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
                <button onClick={() => setCaptionsOn((c) => !c)} className="px-3 py-2 rounded bg-gray-700 hover:bg-gray-600 text-xs">
                  CC {captionsOn ? 'on' : 'off'}
                </button>
              </div>

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
          <div className="px-4 py-2 border-b border-gray-800 text-xs uppercase tracking-wide text-gray-400">Transcript</div>
          <div className="flex-1 overflow-y-auto p-3 space-y-2 text-sm">
            {transcript.map((e, i) => (
              <div
                key={i}
                className={e.role === 'learner' ? 'text-indigo-300' : e.role === 'system' ? 'text-gray-500 italic' : 'text-gray-100'}
              >
                <span className="text-[10px] uppercase mr-1 text-gray-500">{e.role}</span>
                {e.text}
                {e.escalated && <span className="ml-1 text-amber-400 text-[10px]">(escalated)</span>}
                {e.sourceRefs && e.sourceRefs.length > 0 && (
                  <div className="mt-1 text-[10px] text-gray-500">cites: {e.sourceRefs.map((s) => `“${s}”`).join(' · ')}</div>
                )}
                {e.disclaimer && <div className="mt-0.5 text-[10px] text-gray-600 italic">{e.disclaimer}</div>}
              </div>
            ))}
          </div>
          {mode === 'defer' && queued.length > 0 && (
            <div className="border-t border-gray-800 p-3 text-xs text-amber-300">{queued.length} question(s) queued</div>
          )}
        </aside>
      </div>
    </div>
  )
}
