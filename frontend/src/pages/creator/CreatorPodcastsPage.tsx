import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '@/services/api'
import { ilbApi } from '@/services/ilbApi'

/**
 * Creator authoring surface for ILB / "Podcast" broadcasts.
 * Pick a course → configure host persona + avatar → generate a grounded podcast script →
 * launch the interactive broadcast preview.
 *
 * Avatar selection + script persistence are demo-level; the live avatar/voice are Bucket B
 * (stubbed pending HeyGen/Deepgram/ElevenLabs keys). See docs/superpowers/specs/2026-05-21-ilb-design.md.
 */

interface Course {
  id: number
  title: string
  status: string
}

export function CreatorPodcastsPage() {
  const navigate = useNavigate()
  const [courses, setCourses] = useState<Course[]>([])
  const [loading, setLoading] = useState(true)
  const [courseId, setCourseId] = useState<number | null>(null)

  const [hostPersona, setHostPersona] = useState('a warm, clear, professional training host')
  const [targetMinutes, setTargetMinutes] = useState(10)
  const [avatarId, setAvatarId] = useState('demo_avatar')

  const [script, setScript] = useState('')
  const [segmentCount, setSegmentCount] = useState<number | null>(null)
  const [generating, setGenerating] = useState(false)
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
  }, [])

  async function generate() {
    if (courseId == null) return
    setGenerating(true)
    setError(null)
    try {
      const res = await ilbApi.generatePodcastScript(courseId, hostPersona, targetMinutes)
      setScript(res.script)
      setSegmentCount(res.segments.length)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to generate script')
    } finally {
      setGenerating(false)
    }
  }

  return (
    <div className="max-w-3xl">
      <h1 className="text-2xl font-bold text-gray-900 mb-2">Podcasts (Interactive Broadcast)</h1>
      <p className="text-sm text-gray-500 mb-6">
        Turn a course into an avatar-led interactive broadcast. Generate a host-persona script
        grounded in the course content, then launch the player. (Live avatar &amp; voice are stubbed
        until API keys are configured.)
      </p>

      {loading ? (
        <p className="text-gray-400">Loading courses…</p>
      ) : courses.length === 0 ? (
        <p className="text-gray-400">No courses yet — create one first.</p>
      ) : (
        <div className="space-y-5 bg-white rounded-lg border border-gray-200 p-6 shadow-sm">
          <div>
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

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Avatar ID <span className="text-gray-400 font-normal">(HeyGen — stubbed pending keys)</span>
            </label>
            <input
              value={avatarId}
              onChange={(e) => setAvatarId(e.target.value)}
              className="w-full rounded border border-gray-300 px-3 py-2 text-sm"
            />
          </div>

          {error && <p className="text-sm text-red-600">{error}</p>}

          <div className="flex flex-wrap gap-3">
            <button
              onClick={() => void generate()}
              disabled={generating || courseId == null}
              className="px-4 py-2 rounded bg-blue-600 text-white text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
            >
              {generating ? 'Generating…' : 'Generate script'}
            </button>
            <button
              onClick={() => courseId != null && navigate(`/learn/${courseId}/broadcast`)}
              disabled={courseId == null}
              className="px-4 py-2 rounded bg-emerald-700 text-white text-sm font-medium hover:bg-emerald-600 disabled:opacity-50"
            >
              ▶ Launch broadcast preview
            </button>
          </div>

          {script && (
            <div>
              <div className="flex items-center justify-between mb-1">
                <label className="block text-sm font-medium text-gray-700">
                  Generated script {segmentCount != null && <span className="text-gray-400">· {segmentCount} segment(s)</span>}
                </label>
              </div>
              <textarea
                value={script}
                onChange={(e) => setScript(e.target.value)}
                rows={16}
                className="w-full rounded border border-gray-300 px-3 py-2 text-sm font-mono"
              />
              <p className="text-xs text-gray-400 mt-1">
                Editable. Persisting the script to the course and rendering the avatar video are follow-ups.
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
