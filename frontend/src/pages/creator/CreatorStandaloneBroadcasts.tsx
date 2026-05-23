import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ilbApi, type Voice, type BroadcastSummary } from '@/services/ilbApi'

/**
 * Creator authoring for STANDALONE broadcasts (org content outside a course:
 * team brief, company news, policy update). Source via paste / upload / AI-from-topic.
 * Voice + narration audio are real (ElevenLabs); the live avatar is stubbed pending HeyGen.
 */

const DEFAULT_PERSONA = 'a warm, clear, professional host'

export function CreatorStandaloneBroadcasts() {
  const navigate = useNavigate()
  const fileRef = useRef<HTMLInputElement | null>(null)

  const [list, setList] = useState<BroadcastSummary[]>([])
  const [voices, setVoices] = useState<Voice[]>([])
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [newTitle, setNewTitle] = useState('')

  const [title, setTitle] = useState('')
  const [sourceText, setSourceText] = useState('')
  const [hostPersona, setHostPersona] = useState(DEFAULT_PERSONA)
  const [targetMinutes, setTargetMinutes] = useState(5)
  const [voiceId, setVoiceId] = useState('')
  const [script, setScript] = useState('')
  const [segmentCount, setSegmentCount] = useState<number | null>(null)
  const [audioCount, setAudioCount] = useState<number | null>(null)
  const [published, setPublished] = useState(false)

  const [busy, setBusy] = useState<string | null>(null)
  const [status, setStatus] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  function refreshList() {
    ilbApi.listBroadcasts().then(setList).catch(() => {})
  }

  useEffect(() => {
    refreshList()
    ilbApi.listVoices().then((vs) => {
      setVoices(vs)
      setVoiceId((cur) => cur || vs[0]?.voice_id || '')
    }).catch(() => {})
  }, [])

  useEffect(() => {
    if (selectedId == null) return
    setError(null)
    setStatus(null)
    ilbApi.getBroadcast(selectedId).then((b) => {
      setTitle(b.title)
      setSourceText(b.source_text ?? '')
      setHostPersona(b.host_persona ?? DEFAULT_PERSONA)
      setVoiceId(b.voice_id ?? voiceId)
      setScript(b.script ?? '')
      setSegmentCount(b.segments?.length ?? null)
      setAudioCount(b.segment_audio?.length ?? null)
      setPublished(b.published)
    }).catch(() => setError('Could not load broadcast'))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedId])

  async function run(label: string, fn: () => Promise<void>) {
    setBusy(label)
    setError(null)
    try {
      await fn()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Something went wrong')
    } finally {
      setBusy(null)
    }
  }

  async function createBroadcast() {
    const t = newTitle.trim()
    if (!t) return
    await run('create', async () => {
      const b = await ilbApi.createBroadcast(t)
      setNewTitle('')
      refreshList()
      setSelectedId(b.id)
      setStatus('Broadcast created.')
    })
  }

  async function save() {
    if (selectedId == null) return
    await run('save', async () => {
      const b = await ilbApi.updateBroadcast(selectedId, {
        title, source_text: sourceText, host_persona: hostPersona, voice_id: voiceId, script,
      })
      setSegmentCount(b.segments?.length ?? null)
      setAudioCount(b.segment_audio?.length ?? null)
      refreshList()
      setStatus('Saved.')
    })
  }

  async function uploadSource(file: File) {
    if (selectedId == null) return
    await run('upload', async () => {
      const b = await ilbApi.uploadBroadcastSource(selectedId, file)
      setSourceText(b.source_text ?? '')
      setStatus(`Extracted ${b.source_text?.length ?? 0} chars from ${file.name}.`)
    })
  }

  async function generate() {
    if (selectedId == null) return
    await run('generate', async () => {
      // persist source first so the server generates from the latest content
      await ilbApi.updateBroadcast(selectedId, { source_text: sourceText, host_persona: hostPersona })
      const res = await ilbApi.generateBroadcastScript(selectedId, hostPersona, targetMinutes)
      setScript(res.script)
      setSegmentCount(res.segments.length)
      setAudioCount(null)
      setStatus('Script generated — Save, then Render audio.')
    })
  }

  async function renderAudio() {
    if (selectedId == null) return
    await run('render', async () => {
      const res = await ilbApi.renderBroadcastAudio(selectedId)
      setAudioCount(res.segment_audio.length)
      setStatus(`Narration rendered — ${res.segment_audio.length} clip(s).`)
    })
  }

  async function togglePublish() {
    if (selectedId == null) return
    await run('publish', async () => {
      const b = await ilbApi.publishBroadcast(selectedId, !published)
      setPublished(b.published)
      refreshList()
      setStatus(b.published ? 'Published — learners can launch it.' : 'Unpublished.')
    })
  }

  const hasScript = script.trim().length > 0

  return (
    <div className="space-y-5">
      {/* List + create */}
      <div className="bg-white rounded-lg border border-gray-200 p-4 shadow-sm">
        <div className="flex items-center gap-2 mb-3">
          <input
            value={newTitle}
            onChange={(e) => setNewTitle(e.target.value)}
            placeholder="New broadcast title (e.g. April company news)"
            className="flex-1 rounded border border-gray-300 px-3 py-2 text-sm"
          />
          <button
            onClick={() => void createBroadcast()}
            disabled={busy === 'create' || !newTitle.trim()}
            className="px-4 py-2 rounded bg-blue-600 text-white text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
          >
            New broadcast
          </button>
        </div>
        {list.length === 0 ? (
          <p className="text-sm text-gray-400">No standalone broadcasts yet.</p>
        ) : (
          <div className="flex flex-col gap-1">
            {list.map((b) => (
              <button
                key={b.id}
                onClick={() => setSelectedId(b.id)}
                className={`flex items-center justify-between text-left px-3 py-2 rounded text-sm ${
                  selectedId === b.id ? 'bg-indigo-50 border border-indigo-200' : 'hover:bg-gray-50'
                }`}
              >
                <span>{b.title}</span>
                <span className={`text-xs px-2 py-0.5 rounded-full ${b.published ? 'bg-emerald-100 text-emerald-700' : 'bg-gray-100 text-gray-500'}`}>
                  {b.published ? 'Published' : 'Draft'}
                </span>
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Editor */}
      {selectedId != null && (
        <div className="bg-white rounded-lg border border-gray-200 p-6 shadow-sm space-y-5">
          <div className="flex items-center justify-between gap-4">
            <input
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="flex-1 rounded border border-gray-300 px-3 py-2 text-sm font-medium"
            />
            <span className={`text-xs px-2 py-1 rounded-full ${published ? 'bg-emerald-100 text-emerald-700' : 'bg-gray-100 text-gray-500'}`}>
              {published ? '● Published' : 'Draft'}
            </span>
          </div>

          <div>
            <div className="flex items-center justify-between mb-1">
              <label className="block text-sm font-medium text-gray-700">Source content</label>
              <div className="flex items-center gap-2">
                <input
                  ref={fileRef}
                  type="file"
                  accept=".pdf,.docx,.pptx"
                  className="hidden"
                  onChange={(e) => {
                    const f = e.target.files?.[0]
                    if (f) void uploadSource(f)
                    e.target.value = ''
                  }}
                />
                <button
                  onClick={() => fileRef.current?.click()}
                  disabled={busy === 'upload'}
                  className="text-xs px-2 py-1 rounded bg-gray-200 hover:bg-gray-300 disabled:opacity-50"
                >
                  {busy === 'upload' ? 'Extracting…' : 'Upload doc'}
                </button>
              </div>
            </div>
            <textarea
              value={sourceText}
              onChange={(e) => setSourceText(e.target.value)}
              rows={6}
              placeholder="Paste the brief / news / policy text here, upload a document, or type a topic for the AI to expand."
              className="w-full rounded border border-gray-300 px-3 py-2 text-sm"
            />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="sm:col-span-1">
              <label className="block text-sm font-medium text-gray-700 mb-1">Host persona</label>
              <input value={hostPersona} onChange={(e) => setHostPersona(e.target.value)} className="w-full rounded border border-gray-300 px-3 py-2 text-sm" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Voice</label>
              <select value={voiceId} onChange={(e) => setVoiceId(e.target.value)} className="w-full rounded border border-gray-300 px-3 py-2 text-sm">
                {voices.length === 0 && <option value="">Default</option>}
                {voices.map((v) => (
                  <option key={v.voice_id} value={v.voice_id}>{v.name}{v.description ? ` — ${v.description}` : ''}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Target minutes</label>
              <input type="number" min={1} max={60} value={targetMinutes} onChange={(e) => setTargetMinutes(Number(e.target.value))} className="w-full rounded border border-gray-300 px-3 py-2 text-sm" />
            </div>
          </div>

          {error && <p className="text-sm text-red-600">{error}</p>}
          {status && !error && <p className="text-sm text-emerald-600">{status}</p>}

          <div className="flex flex-wrap gap-3">
            <button onClick={() => void generate()} disabled={busy != null || !sourceText.trim()} className="px-4 py-2 rounded bg-blue-600 text-white text-sm font-medium hover:bg-blue-700 disabled:opacity-50">
              {busy === 'generate' ? 'Generating…' : 'Generate script'}
            </button>
            <button onClick={() => void save()} disabled={busy != null} className="px-4 py-2 rounded bg-gray-700 text-white text-sm font-medium hover:bg-gray-600 disabled:opacity-50">
              {busy === 'save' ? 'Saving…' : 'Save'}
            </button>
            <button onClick={() => void renderAudio()} disabled={busy != null || segmentCount == null || segmentCount === 0} className="px-4 py-2 rounded bg-purple-600 text-white text-sm font-medium hover:bg-purple-500 disabled:opacity-50">
              {busy === 'render' ? 'Rendering…' : audioCount ? `Re-render audio (${audioCount})` : 'Render audio'}
            </button>
            <button onClick={() => void togglePublish()} disabled={busy != null || (!published && !hasScript)} className="px-4 py-2 rounded bg-amber-600 text-white text-sm font-medium hover:bg-amber-500 disabled:opacity-50">
              {busy === 'publish' ? '…' : published ? 'Unpublish' : 'Publish'}
            </button>
            <button onClick={() => navigate(`/learn/broadcast/${selectedId}`)} className="px-4 py-2 rounded bg-emerald-700 text-white text-sm font-medium hover:bg-emerald-600">
              ▶ Launch preview
            </button>
          </div>

          {hasScript && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Script {segmentCount != null && <span className="text-gray-400">· {segmentCount} segment(s){audioCount ? ` · ${audioCount} audio` : ''}</span>}
              </label>
              <textarea value={script} onChange={(e) => setScript(e.target.value)} rows={14} className="w-full rounded border border-gray-300 px-3 py-2 text-sm font-mono" />
              <p className="text-xs text-gray-400 mt-1">Edit then Save. <code>[SEGMENT BREAK]</code> marks segment boundaries.</p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
