import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '@/services/api'
import { ilbApi, type Voice } from '@/services/ilbApi'
import { CreatorStandaloneBroadcasts } from './CreatorStandaloneBroadcasts'

/**
 * Creator authoring surface for ILB / "Podcast" broadcasts.
 * Pick a course → configure host persona + voice + avatar → generate a grounded script → SAVE →
 * render narration audio (ElevenLabs) → PUBLISH → preview/launch.
 *
 * Voice + narration audio are real (ElevenLabs). The live avatar is Bucket B (stubbed pending
 * HeyGen keys). See docs/superpowers/specs/2026-05-21-ilb-design.md.
 */

interface Course {
  id: number
  title: string
  status: string
}

const DEFAULT_PERSONA = 'a warm, clear, professional training host'

export function CreatorPodcastsPage() {
  const navigate = useNavigate()
  const [tab, setTab] = useState<'course' | 'standalone'>('course')
  const [courses, setCourses] = useState<Course[]>([])
  const [voices, setVoices] = useState<Voice[]>([])
  const [loading, setLoading] = useState(true)
  const [courseId, setCourseId] = useState<number | null>(null)

  const [hostPersona, setHostPersona] = useState(DEFAULT_PERSONA)
  const [targetMinutes, setTargetMinutes] = useState(10)
  const [avatarId, setAvatarId] = useState('demo_avatar')
  const [voiceId, setVoiceId] = useState('')

  const [script, setScript] = useState('')
  const [segmentCount, setSegmentCount] = useState<number | null>(null)
  const [audioCount, setAudioCount] = useState<number | null>(null)
  const [published, setPublished] = useState(false)

  const [generating, setGenerating] = useState(false)
  const [saving, setSaving] = useState(false)
  const [rendering, setRendering] = useState(false)
  const [publishing, setPublishing] = useState(false)
  const [status, setStatus] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api.get('/courses').then(async (res) => {
      if (res.ok) {
        const data = await res.json()
        const list: Course[] = Array.isArray(data) ? data : data.items ?? []
        setCourses(list)
        if (list.length > 0) setCourseId(list[0].id)
      }
      setLoading(false)
    })
    ilbApi.listVoices().then((vs) => {
      setVoices(vs)
      setVoiceId((cur) => cur || vs[0]?.voice_id || '')
    }).catch(() => {})
  }, [])

  // Load any existing broadcast config when the selected course changes.
  useEffect(() => {
    if (courseId == null) return
    setError(null)
    setStatus(null)
    ilbApi
      .getPodcast(courseId)
      .then((cfg) => {
        setHostPersona(cfg.host_persona ?? DEFAULT_PERSONA)
        setAvatarId(cfg.avatar_id ?? 'demo_avatar')
        setVoiceId(cfg.voice_id ?? '')
        setScript(cfg.script ?? '')
        setSegmentCount(cfg.segments?.length ?? null)
        setAudioCount(cfg.segment_audio?.length ?? null)
        setPublished(cfg.published)
      })
      .catch(() => {
        setScript('')
        setSegmentCount(null)
        setAudioCount(null)
        setPublished(false)
      })
  }, [courseId])

  async function generate() {
    if (courseId == null) return
    setGenerating(true)
    setError(null)
    setStatus(null)
    try {
      const res = await ilbApi.generatePodcastScript(courseId, hostPersona, targetMinutes)
      setScript(res.script)
      setSegmentCount(res.segments.length)
      setAudioCount(null)
      setStatus('Script generated — Save to keep it.')
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to generate script')
    } finally {
      setGenerating(false)
    }
  }

  async function save() {
    if (courseId == null) return
    setSaving(true)
    setError(null)
    try {
      const cfg = await ilbApi.savePodcast(courseId, script, hostPersona, avatarId, voiceId)
      setSegmentCount(cfg.segments?.length ?? null)
      setAudioCount(cfg.segment_audio?.length ?? null) // cleared on save
      setStatus('Saved. Render audio to give it a voice.')
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to save')
    } finally {
      setSaving(false)
    }
  }

  async function renderAudio() {
    if (courseId == null) return
    setRendering(true)
    setError(null)
    try {
      const res = await ilbApi.renderAudio(courseId)
      setAudioCount(res.segment_audio.length)
      setStatus(`Narration rendered — ${res.segment_audio.length} clip(s).`)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to render audio')
    } finally {
      setRendering(false)
    }
  }

  async function togglePublish() {
    if (courseId == null) return
    setPublishing(true)
    setError(null)
    try {
      const cfg = await ilbApi.publishPodcast(courseId, !published)
      setPublished(cfg.published)
      setStatus(cfg.published ? 'Published — learners can launch it.' : 'Unpublished.')
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to publish')
    } finally {
      setPublishing(false)
    }
  }

  const hasScript = script.trim().length > 0

  return (
    <div className="max-w-3xl">
      <h1 className="text-2xl font-bold text-gray-900 mb-2">Podcasts (Interactive Broadcast)</h1>
      <p className="text-sm text-gray-500 mb-6">
        Turn a course into an avatar-led interactive broadcast: generate a host-persona script
        grounded in the course content, pick a voice, render narration audio, publish, then launch.
        (Voice &amp; audio are real; the live avatar is stubbed until HeyGen keys are configured.)
      </p>

      <div className="flex gap-2 mb-5 text-sm">
        {(['course', 'standalone'] as const).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-3 py-1.5 rounded ${tab === t ? 'bg-indigo-600 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'}`}
          >
            {t === 'course' ? 'From course' : 'Standalone (brief / news)'}
          </button>
        ))}
      </div>

      {tab === 'standalone' ? (
        <CreatorStandaloneBroadcasts />
      ) : loading ? (
        <p className="text-gray-400">Loading courses…</p>
      ) : courses.length === 0 ? (
        <p className="text-gray-400">No courses yet — create one first.</p>
      ) : (
        <div className="space-y-5 bg-white rounded-lg border border-gray-200 p-6 shadow-sm">
          <div className="flex items-center justify-between gap-4">
            <div className="flex-1">
              <label className="block text-sm font-medium text-gray-700 mb-1">Course</label>
              <select
                value={courseId ?? ''}
                onChange={(e) => setCourseId(Number(e.target.value))}
                className="w-full rounded border border-gray-300 px-3 py-2 text-sm"
              >
                {courses.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.title} ({c.status})
                  </option>
                ))}
              </select>
            </div>
            <span
              className={`mt-5 text-xs px-2 py-1 rounded-full ${
                published ? 'bg-emerald-100 text-emerald-700' : 'bg-gray-100 text-gray-500'
              }`}
            >
              {published ? '● Published' : 'Draft'}
            </span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="sm:col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-1">Host persona</label>
              <input
                value={hostPersona}
                onChange={(e) => setHostPersona(e.target.value)}
                className="w-full rounded border border-gray-300 px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Target minutes</label>
              <input
                type="number"
                min={1}
                max={60}
                value={targetMinutes}
                onChange={(e) => setTargetMinutes(Number(e.target.value))}
                className="w-full rounded border border-gray-300 px-3 py-2 text-sm"
              />
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Voice (ElevenLabs)</label>
              <select
                value={voiceId}
                onChange={(e) => setVoiceId(e.target.value)}
                className="w-full rounded border border-gray-300 px-3 py-2 text-sm"
              >
                {voices.length === 0 && <option value="">Default</option>}
                {voices.map((v) => (
                  <option key={v.voice_id} value={v.voice_id}>
                    {v.name}{v.description ? ` — ${v.description}` : ''}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Avatar ID <span className="text-gray-400 font-normal">(HeyGen — stubbed)</span>
              </label>
              <input
                value={avatarId}
                onChange={(e) => setAvatarId(e.target.value)}
                className="w-full rounded border border-gray-300 px-3 py-2 text-sm"
              />
            </div>
          </div>

          {error && <p className="text-sm text-red-600">{error}</p>}
          {status && !error && <p className="text-sm text-emerald-600">{status}</p>}

          <div className="flex flex-wrap gap-3">
            <button
              onClick={() => void generate()}
              disabled={generating || courseId == null}
              className="px-4 py-2 rounded bg-blue-600 text-white text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
            >
              {generating ? 'Generating…' : 'Generate script'}
            </button>
            <button
              onClick={() => void save()}
              disabled={saving || !hasScript}
              className="px-4 py-2 rounded bg-gray-700 text-white text-sm font-medium hover:bg-gray-600 disabled:opacity-50"
            >
              {saving ? 'Saving…' : 'Save'}
            </button>
            <button
              onClick={() => void renderAudio()}
              disabled={rendering || segmentCount == null || segmentCount === 0}
              className="px-4 py-2 rounded bg-purple-600 text-white text-sm font-medium hover:bg-purple-500 disabled:opacity-50"
            >
              {rendering ? 'Rendering…' : audioCount ? `Re-render audio (${audioCount})` : 'Render audio'}
            </button>
            <button
              onClick={() => void togglePublish()}
              disabled={publishing || (!published && !hasScript)}
              className="px-4 py-2 rounded bg-amber-600 text-white text-sm font-medium hover:bg-amber-500 disabled:opacity-50"
            >
              {publishing ? '…' : published ? 'Unpublish' : 'Publish'}
            </button>
            <button
              onClick={() => courseId != null && navigate(`/learn/${courseId}/broadcast`)}
              disabled={courseId == null}
              className="px-4 py-2 rounded bg-emerald-700 text-white text-sm font-medium hover:bg-emerald-600 disabled:opacity-50"
            >
              ▶ Launch preview
            </button>
          </div>

          {hasScript && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Script {segmentCount != null && <span className="text-gray-400">· {segmentCount} segment(s){audioCount ? ` · ${audioCount} audio` : ''}</span>}
              </label>
              <textarea
                value={script}
                onChange={(e) => setScript(e.target.value)}
                rows={16}
                className="w-full rounded border border-gray-300 px-3 py-2 text-sm font-mono"
              />
              <p className="text-xs text-gray-400 mt-1">
                Edit then Save (Save clears stale audio — Render again). Use <code>[SEGMENT BREAK]</code> to mark boundaries.
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
