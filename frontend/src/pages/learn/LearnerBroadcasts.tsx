import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ilbApi, type BroadcastSummary } from '@/services/ilbApi'

/**
 * Learner catalogue of standalone broadcasts (team briefs, company news, policy updates).
 * The API returns only published broadcasts to learners.
 */
export const LearnerBroadcasts = () => {
  const navigate = useNavigate()
  const [items, setItems] = useState<BroadcastSummary[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    ilbApi.listBroadcasts().then(setItems).catch(() => {}).finally(() => setLoading(false))
  }, [])

  return (
    <div>
      <h1 className="text-3xl font-bold text-gray-900 mb-1">Broadcasts</h1>
      <p className="text-gray-500 mb-6">Interactive briefings, company news, and updates.</p>

      {loading ? (
        <p className="text-gray-400">Loading…</p>
      ) : items.length === 0 ? (
        <div className="bg-gray-50 rounded-lg p-8 text-center text-gray-500">
          No broadcasts available right now.
        </div>
      ) : (
        <div className="space-y-3">
          {items.map((b) => (
            <div key={b.id} className="flex items-center justify-between bg-white border border-gray-100 rounded-lg shadow-sm p-4">
              <div>
                <p className="font-semibold text-gray-900">{b.title}</p>
                {b.description && <p className="text-sm text-gray-500">{b.description}</p>}
              </div>
              <button
                onClick={() => navigate(`/learn/broadcast/${b.id}`)}
                className="px-5 py-2 rounded-lg bg-indigo-600 text-white text-sm font-bold hover:bg-indigo-700"
              >
                🎙️ Launch
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
