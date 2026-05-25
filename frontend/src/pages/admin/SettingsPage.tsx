import { useState, useEffect, useCallback } from 'react'
import { api } from '@/services/api'
import { useToast } from '@/context/ToastContext'
import { Card } from '@/components/common/Card'
import { Badge } from '@/components/common/Badge'
import { Button } from '@/components/common/Button'

type ProviderKey = 'elevenlabs' | 'deepgram' | 'claude' | 'heygen'

interface ProviderStatus {
  configured: boolean
  masked: string | null
  source: 'database' | 'environment' | null
}

type StatusMap = Record<ProviderKey, ProviderStatus>

// payload field name on the backend for each provider
const FIELD: Record<ProviderKey, string> = {
  elevenlabs: 'elevenlabs_api_key',
  deepgram: 'deepgram_api_key',
  claude: 'claude_api_key',
  heygen: 'heygen_api_key',
}

const PROVIDERS: { key: ProviderKey; name: string; desc: string; note?: string }[] = [
  { key: 'elevenlabs', name: 'ElevenLabs', desc: 'Podcast / broadcast narration audio (text-to-speech).' },
  { key: 'deepgram', name: 'Deepgram', desc: 'Voice questions in the broadcast player (speech-to-text).' },
  { key: 'claude', name: 'Claude (Anthropic)', desc: 'AI course generation and the grounded Q&A assistant.' },
  {
    key: 'heygen',
    name: 'HeyGen',
    desc: 'Live avatar video for broadcasts.',
    note: 'Not active yet — the avatar integration is still in development. Your key is stored and will be used once it ships.',
  },
]

export const SettingsPage = () => {
  const [status, setStatus] = useState<StatusMap | null>(null)
  const [loading, setLoading] = useState(true)
  const [inputs, setInputs] = useState<Record<ProviderKey, string>>({ elevenlabs: '', deepgram: '', claude: '', heygen: '' })
  const [savingKey, setSavingKey] = useState<ProviderKey | null>(null)
  const { showToast } = useToast()

  const fetchStatus = useCallback(async () => {
    setLoading(true)
    try {
      const res = await api.get('/admin/integrations')
      if (res.ok) {
        const data = await res.json()
        setStatus(data.providers as StatusMap)
      } else {
        showToast('Failed to load integration settings', 'error')
      }
    } catch {
      showToast('Failed to load integration settings', 'error')
    } finally {
      setLoading(false)
    }
  }, [showToast])

  useEffect(() => { void fetchStatus() }, [fetchStatus])

  const save = async (key: ProviderKey, value: string) => {
    setSavingKey(key)
    try {
      const res = await api.put('/admin/integrations', { [FIELD[key]]: value })
      if (res.ok) {
        const data = await res.json()
        setStatus(data.providers as StatusMap)
        setInputs((prev) => ({ ...prev, [key]: '' }))
        showToast(value ? 'Key saved' : 'Key cleared', 'success')
      } else {
        showToast('Failed to save key', 'error')
      }
    } catch {
      showToast('Failed to save key', 'error')
    } finally {
      setSavingKey(null)
    }
  }

  return (
    <div>
      <h1 className="text-2xl font-bold text-brand-dark mb-1">Integration Settings</h1>
      <p className="text-sm text-gray-500 mb-6">
        API keys for the third-party services that power audio, voice input and AI features.
        Keys are stored securely and never shown in full. A saved key takes effect immediately.
      </p>

      {loading ? (
        <p className="text-gray-500">Loading…</p>
      ) : (
        <div className="space-y-4 max-w-2xl">
          {PROVIDERS.map(({ key, name, desc, note }) => {
            const s = status?.[key]
            const configured = !!s?.configured
            return (
              <Card key={key} className="p-5">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <div className="flex items-center gap-2">
                      <h2 className="font-semibold text-brand-dark">{name}</h2>
                      {configured ? (
                        <Badge variant="success">Configured</Badge>
                      ) : (
                        <Badge variant="warning">Not configured</Badge>
                      )}
                      {note && <Badge variant="info">Coming soon</Badge>}
                    </div>
                    <p className="text-sm text-gray-500 mt-1">{desc}</p>
                    {note && <p className="text-xs text-amber-600 mt-1">{note}</p>}
                    {configured && (
                      <p className="text-xs text-gray-400 mt-1">
                        Current: <span className="font-mono">{s?.masked}</span>
                        {s?.source && <span className="ml-2">(from {s.source})</span>}
                      </p>
                    )}
                  </div>
                </div>

                <div className="flex items-end gap-2 mt-4">
                  <div className="flex-1">
                    <label className="block text-sm font-medium mb-1 text-gray-700" htmlFor={`key-${key}`}>
                      {configured ? 'Replace key' : 'Add key'}
                    </label>
                    <input
                      id={`key-${key}`}
                      type="password"
                      autoComplete="off"
                      value={inputs[key]}
                      onChange={(e) => setInputs((prev) => ({ ...prev, [key]: e.target.value }))}
                      placeholder={`Paste your ${name} API key`}
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                  </div>
                  <Button
                    onClick={() => void save(key, inputs[key].trim())}
                    disabled={savingKey === key || !inputs[key].trim()}
                  >
                    {savingKey === key ? 'Saving…' : 'Save'}
                  </Button>
                  {configured && (
                    <Button
                      variant="ghost"
                      onClick={() => void save(key, '')}
                      disabled={savingKey === key}
                    >
                      Clear
                    </Button>
                  )}
                </div>
              </Card>
            )
          })}

          <p className="text-xs text-gray-400 mt-2">
            Note: keys saved here live in the application database. If the backend is
            redeployed without a persistent volume they may need re-entering — set the
            matching environment variables on the host for permanence.
          </p>
        </div>
      )}
    </div>
  )
}
