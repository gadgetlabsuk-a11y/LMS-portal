import { useState, useEffect } from 'react'
import { api } from '@/services/api'
import { useToast } from '@/context/ToastContext'
import { Card } from '@/components/common/Card'

interface SysHealth {
  uptime: number
  memory: number
  dbSize: number
  apiCalls: number
  cpu?: number
}

interface ErrorEntry {
  error_type: string
  message: string
  timestamp: string
  stack_trace?: string
}

interface ApiUsageEntry {
  model: string
  call_count: number
  input_tokens: number
  output_tokens: number
  cost?: number
}

interface FeatureFlag {
  id: string
  name: string
  description: string
  enabled: boolean
}

interface EnvInfo {
  version?: string
  environment?: string
  python_version?: string
  api_version?: string
}

export const DevToolsPage = () => {
  const [sysHealth, setSysHealth] = useState<SysHealth>({ uptime: 0, memory: 0, dbSize: 0, apiCalls: 0 })
  const [errors, setErrors] = useState<ErrorEntry[]>([])
  const [apiUsage, setApiUsage] = useState<ApiUsageEntry[]>([])
  const [flags, setFlags] = useState<FeatureFlag[]>([])
  const [envInfo, setEnvInfo] = useState<EnvInfo>({})
  const [loading, setLoading] = useState(true)
  const [expandedError, setExpandedError] = useState<number | null>(null)
  const { showToast } = useToast()

  useEffect(() => {
    fetchDevData()
  }, [])

  const fetchDevData = async () => {
    setLoading(true)
    try {
      const [healthRes, errorsRes, usageRes, flagsRes, envRes] = await Promise.all([
        api.get('/dev/health'),
        api.get('/dev/errors?limit=20'),
        api.get('/dev/api-usage?limit=20'),
        api.get('/dev/feature-flags'),
        api.get('/dev/env-info'),
      ])

      if (healthRes.ok) {
        const h = await healthRes.json()
        setSysHealth({
          uptime: h.uptime_seconds ?? h.uptime ?? 0,
          memory: h.memory_percent ?? h.memory ?? 0,
          dbSize: (h.database_size_mb ?? 0) * 1024 * 1024,
          apiCalls: h.api_calls ?? h.apiCalls ?? 0,
          cpu: h.cpu_percent ?? 0,
        })
      }
      if (errorsRes.ok) { const d = await errorsRes.json(); setErrors(Array.isArray(d) ? d : d.items || []) }
      if (usageRes.ok) { const d = await usageRes.json(); setApiUsage(Array.isArray(d) ? d : d.items || []) }
      if (flagsRes.ok) { const d = await flagsRes.json(); setFlags(Array.isArray(d) ? d : d.items || []) }
      if (envRes.ok) setEnvInfo(await envRes.json())
    } catch (err) {
      showToast('Failed to load dev data', 'error')
    } finally {
      setLoading(false)
    }
  }

  const handleToggleFlag = async (flagId: string, enabled: boolean) => {
    try {
      const res = await api.put(`/dev/feature-flags/${flagId}`, { enabled: !enabled })
      if (res.ok) {
        showToast('Flag updated', 'success')
        fetchDevData()
      } else {
        showToast('Failed to update flag', 'error')
      }
    } catch (err) {
      showToast((err as Error).message, 'error')
    }
  }

  return (
    <div className="space-y-6">
      {loading ? (
        <div className="text-center py-12"><div className="spin text-4xl inline-block">⏳</div></div>
      ) : (
        <>
          <div>
            <h3 className="text-lg font-bold mb-4">System Health</h3>
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <Card className="p-4">
                <p className="text-sm text-gray-600">Uptime</p>
                <p className="text-2xl font-bold mt-1">{(sysHealth.uptime / 3600).toFixed(1)}h</p>
              </Card>
              <Card className="p-4">
                <p className="text-sm text-gray-600">Memory Usage</p>
                <div className="mt-2 bg-gray-200 rounded-full h-2">
                  <div
                    className="bg-blue-600 h-2 rounded-full"
                    style={{ width: `${Math.min(sysHealth.memory, 100)}%` }}
                  ></div>
                </div>
                <p className="text-sm mt-1">{sysHealth.memory.toFixed(1)}%</p>
              </Card>
              <Card className="p-4">
                <p className="text-sm text-gray-600">DB Size</p>
                <p className="text-2xl font-bold mt-1">{(sysHealth.dbSize / 1024 / 1024).toFixed(1)}MB</p>
              </Card>
              <Card className="p-4">
                <p className="text-sm text-gray-600">API Calls</p>
                <p className="text-2xl font-bold mt-1">{sysHealth.apiCalls}</p>
              </Card>
            </div>
          </div>

          <div>
            <h3 className="text-lg font-bold mb-4">Error Log</h3>
            <Card className="overflow-hidden">
              <div className="divide-y max-h-96 overflow-y-auto">
                {errors.length === 0 ? (
                  <div className="p-6 text-center text-gray-600">
                    No errors
                  </div>
                ) : (
                  errors.map((err, idx) => (
                    <div key={idx} className="p-4 hover:bg-gray-50">
                      <button
                        onClick={() => setExpandedError(expandedError === idx ? null : idx)}
                        className="w-full text-left"
                      >
                        <div className="flex justify-between items-start">
                          <div>
                            <p className="font-medium text-red-600">{err.error_type}</p>
                            <p className="text-sm text-gray-600 mt-1">{err.message}</p>
                            <p className="text-xs text-gray-500 mt-1">{new Date(err.timestamp).toLocaleString()}</p>
                          </div>
                          <span className="text-gray-400">{expandedError === idx ? '▼' : '▶'}</span>
                        </div>
                      </button>
                      {expandedError === idx && (
                        <div className="mt-3 p-3 bg-gray-100 rounded text-xs font-mono text-gray-700 overflow-auto max-h-48">
                          {err.stack_trace}
                        </div>
                      )}
                    </div>
                  ))
                )}
              </div>
            </Card>
          </div>

          <div>
            <h3 className="text-lg font-bold mb-4">Claude API Usage</h3>
            <Card className="overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="bg-gray-50 border-b">
                    <tr>
                      <th className="px-4 py-2 text-left">Model</th>
                      <th className="px-4 py-2 text-left">Calls</th>
                      <th className="px-4 py-2 text-left">Input Tokens</th>
                      <th className="px-4 py-2 text-left">Output Tokens</th>
                      <th className="px-4 py-2 text-left">Cost</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y">
                    {apiUsage.map((usage, idx) => (
                      <tr key={idx} className="hover:bg-gray-50">
                        <td className="px-4 py-2">{usage.model}</td>
                        <td className="px-4 py-2">{usage.call_count}</td>
                        <td className="px-4 py-2">{usage.input_tokens}</td>
                        <td className="px-4 py-2">{usage.output_tokens}</td>
                        <td className="px-4 py-2">${(usage.cost || 0).toFixed(4)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>
          </div>

          <div>
            <h3 className="text-lg font-bold mb-4">Feature Flags</h3>
            <Card className="p-4 space-y-3">
              {flags.map(flag => (
                <div key={flag.id} className="flex justify-between items-center p-3 bg-gray-50 rounded">
                  <div>
                    <p className="font-medium">{flag.name}</p>
                    <p className="text-sm text-gray-600">{flag.description}</p>
                  </div>
                  <button
                    onClick={() => handleToggleFlag(flag.id, flag.enabled)}
                    className={`px-4 py-2 rounded font-medium transition ${flag.enabled ? 'bg-green-600 text-white' : 'bg-gray-400 text-white'}`}
                  >
                    {flag.enabled ? 'ON' : 'OFF'}
                  </button>
                </div>
              ))}
            </Card>
          </div>

          <div>
            <h3 className="text-lg font-bold mb-4">Environment Info</h3>
            <Card className="p-6">
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <p className="text-gray-600">Version</p>
                  <p className="font-mono font-bold">{envInfo.version}</p>
                </div>
                <div>
                  <p className="text-gray-600">Environment</p>
                  <p className="font-mono font-bold">{envInfo.environment}</p>
                </div>
                <div>
                  <p className="text-gray-600">Python Version</p>
                  <p className="font-mono font-bold">{envInfo.python_version}</p>
                </div>
                <div>
                  <p className="text-gray-600">API Version</p>
                  <p className="font-mono font-bold">{envInfo.api_version}</p>
                </div>
              </div>
            </Card>
          </div>
        </>
      )}
    </div>
  )
}
