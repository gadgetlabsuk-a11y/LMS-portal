import { useState, useEffect } from 'react'
import { api } from '@/services/api'
import { useToast } from '@/context/ToastContext'
import { Button } from '@/components/common/Button'
import { Card } from '@/components/common/Card'
import { Badge } from '@/components/common/Badge'

interface SecurityStats {
  activeSessions: number
  failedLogins24h: number
  lockedAccounts: number
}

interface Session {
  id: string
  user_id: string
  ip_address: string
  user_agent: string
  created_at: string
}

interface LoginAttempt {
  username: string
  ip_address: string
  success: boolean
  timestamp: string
}

interface AuditLogEntry {
  admin_id: string
  action_type: string
  resource_type: string
  resource_id: string
  timestamp: string
}

interface IpAllowlistItem {
  id: string
  ip_address: string
  created_at: string
}

interface StatCardProps {
  title: string
  value: number
  icon: string
}

const StatCard = ({ title, value, icon }: StatCardProps) => (
  <Card className="p-4">
    <div className="flex items-center justify-between">
      <div>
        <p className="text-gray-600 text-xs uppercase">{title}</p>
        <p className="text-2xl font-bold mt-1">{value}</p>
      </div>
      <span className="text-3xl">{icon}</span>
    </div>
  </Card>
)

export const SecurityPage = () => {
  const [activeTab, setActiveTab] = useState('sessions')
  const [sessions, setSessions] = useState<Session[]>([])
  const [loginAttempts, setLoginAttempts] = useState<LoginAttempt[]>([])
  const [auditLog, setAuditLog] = useState<AuditLogEntry[]>([])
  const [ipAllowlist, setIpAllowlist] = useState<IpAllowlistItem[]>([])
  const [stats, setStats] = useState<SecurityStats>({ activeSessions: 0, failedLogins24h: 0, lockedAccounts: 0 })
  const [loading, setLoading] = useState(true)
  const [newIp, setNewIp] = useState('')
  const { showToast } = useToast()

  useEffect(() => {
    fetchSecurityData()
  }, [activeTab])

  const fetchSecurityData = async () => {
    setLoading(true)
    try {
      const [statsRes, sessionsRes, attemptsRes, auditRes, ipRes] = await Promise.all([
        api.get('/security/dashboard'),
        api.get('/security/sessions'),
        api.get('/security/login-attempts'),
        api.get('/admin/audit-log?limit=50'),
        api.get('/security/ip-allowlist'),
      ])

      if (statsRes.ok) {
        const sd = await statsRes.json()
        setStats({
          activeSessions: sd.active_sessions ?? 0,
          failedLogins24h: sd.failed_logins_24h ?? 0,
          lockedAccounts: sd.locked_accounts ?? 0,
        })
      }
      if (sessionsRes.ok) { const d = await sessionsRes.json(); setSessions(Array.isArray(d) ? d : d.items || []) }
      if (attemptsRes.ok) { const d = await attemptsRes.json(); setLoginAttempts(Array.isArray(d) ? d : d.items || []) }
      if (auditRes.ok) { const d = await auditRes.json(); setAuditLog(Array.isArray(d) ? d : d.items || []) }
      if (ipRes.ok) { const d = await ipRes.json(); setIpAllowlist(Array.isArray(d) ? d : d.items || []) }
    } catch (err) {
      showToast('Failed to load security data', 'error')
    } finally {
      setLoading(false)
    }
  }

  const handleKillSession = async (sessionId: string) => {
    try {
      const res = await api.delete(`/security/sessions/${sessionId}`)
      if (res.ok) {
        showToast('Session terminated', 'success')
        fetchSecurityData()
      } else {
        showToast('Failed to terminate session', 'error')
      }
    } catch (err) {
      showToast((err as Error).message, 'error')
    }
  }

  const handleAddIp = async () => {
    if (!newIp) return
    try {
      const res = await api.post('/security/ip-allowlist', { ip_address: newIp })
      if (res.ok) {
        showToast('IP added to allowlist', 'success')
        setNewIp('')
        fetchSecurityData()
      } else {
        showToast('Failed to add IP', 'error')
      }
    } catch (err) {
      showToast((err as Error).message, 'error')
    }
  }

  const handleRemoveIp = async (ipId: string) => {
    try {
      const res = await api.delete(`/security/ip-allowlist/${ipId}`)
      if (res.ok) {
        showToast('IP removed', 'success')
        fetchSecurityData()
      } else {
        showToast('Failed to remove IP', 'error')
      }
    } catch (err) {
      showToast((err as Error).message, 'error')
    }
  }

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <StatCard title="Active Sessions" value={stats.activeSessions} icon="👥" />
        <StatCard title="Failed Logins (24h)" value={stats.failedLogins24h} icon="🚫" />
        <StatCard title="Locked Accounts" value={stats.lockedAccounts} icon="🔒" />
      </div>

      <div className="border-b">
        <div className="flex space-x-4">
          {['sessions', 'attempts', 'audit', 'iplist'].map(tab => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-4 py-2 font-medium border-b-2 transition ${activeTab === tab ? 'border-blue-600 text-blue-600' : 'border-transparent text-gray-600 hover:text-gray-900'}`}
            >
              {tab === 'sessions' && 'Sessions'}
              {tab === 'attempts' && 'Login Attempts'}
              {tab === 'audit' && 'Audit Log'}
              {tab === 'iplist' && 'IP Allowlist'}
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <div className="text-center py-12"><div className="spin text-4xl inline-block">⏳</div></div>
      ) : (
        <>
          {activeTab === 'sessions' && (
            <Card className="overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-gray-50 border-b">
                    <tr>
                      <th className="px-6 py-3 text-left text-sm font-semibold">User</th>
                      <th className="px-6 py-3 text-left text-sm font-semibold">IP Address</th>
                      <th className="px-6 py-3 text-left text-sm font-semibold">User Agent</th>
                      <th className="px-6 py-3 text-left text-sm font-semibold">Created</th>
                      <th className="px-6 py-3 text-left text-sm font-semibold">Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y">
                    {sessions.map(session => (
                      <tr key={session.id} className="hover:bg-gray-50">
                        <td className="px-6 py-4 font-medium">{session.user_id}</td>
                        <td className="px-6 py-4 text-sm">{session.ip_address}</td>
                        <td className="px-6 py-4 text-sm text-gray-600 truncate">{session.user_agent}</td>
                        <td className="px-6 py-4 text-sm">{new Date(session.created_at).toLocaleString()}</td>
                        <td className="px-6 py-4">
                          <button onClick={() => handleKillSession(session.id)} className="text-red-600 hover:underline text-sm">
                            Terminate
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>
          )}

          {activeTab === 'attempts' && (
            <Card className="overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-gray-50 border-b">
                    <tr>
                      <th className="px-6 py-3 text-left text-sm font-semibold">Username</th>
                      <th className="px-6 py-3 text-left text-sm font-semibold">IP Address</th>
                      <th className="px-6 py-3 text-left text-sm font-semibold">Status</th>
                      <th className="px-6 py-3 text-left text-sm font-semibold">Timestamp</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y">
                    {loginAttempts.map((attempt, idx) => (
                      <tr key={idx} className="hover:bg-gray-50">
                        <td className="px-6 py-4 font-medium">{attempt.username}</td>
                        <td className="px-6 py-4 text-sm">{attempt.ip_address}</td>
                        <td className="px-6 py-4">
                          <Badge variant={attempt.success ? 'success' : 'danger'}>
                            {attempt.success ? 'Success' : 'Failed'}
                          </Badge>
                        </td>
                        <td className="px-6 py-4 text-sm">{new Date(attempt.timestamp).toLocaleString()}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>
          )}

          {activeTab === 'audit' && (
            <Card className="overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-gray-50 border-b">
                    <tr>
                      <th className="px-6 py-3 text-left text-sm font-semibold">Admin</th>
                      <th className="px-6 py-3 text-left text-sm font-semibold">Action</th>
                      <th className="px-6 py-3 text-left text-sm font-semibold">Resource</th>
                      <th className="px-6 py-3 text-left text-sm font-semibold">Timestamp</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y">
                    {auditLog.map((log, idx) => (
                      <tr key={idx} className="hover:bg-gray-50">
                        <td className="px-6 py-4 font-medium text-sm">{log.admin_id}</td>
                        <td className="px-6 py-4 text-sm">{log.action_type}</td>
                        <td className="px-6 py-4 text-sm text-gray-600">{log.resource_type}: {log.resource_id}</td>
                        <td className="px-6 py-4 text-sm">{new Date(log.timestamp).toLocaleString()}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>
          )}

          {activeTab === 'iplist' && (
            <div className="space-y-4">
              <Card className="p-4">
                <div className="flex gap-2">
                  <input
                    type="text"
                    placeholder="e.g., 192.168.1.0/24"
                    value={newIp}
                    onChange={(e) => setNewIp(e.target.value)}
                    className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                  <Button onClick={handleAddIp}>Add IP</Button>
                </div>
              </Card>

              {ipAllowlist.length === 0 ? (
                <Card className="p-12 text-center">
                  <p className="text-gray-600">No IPs in allowlist</p>
                </Card>
              ) : (
                <Card className="overflow-hidden">
                  <div className="divide-y">
                    {ipAllowlist.map(item => (
                      <div key={item.id} className="p-4 flex justify-between items-center hover:bg-gray-50">
                        <div>
                          <p className="font-medium">{item.ip_address}</p>
                          <p className="text-sm text-gray-600">Added: {new Date(item.created_at).toLocaleString()}</p>
                        </div>
                        <button onClick={() => handleRemoveIp(item.id)} className="text-red-600 hover:underline text-sm">
                          Remove
                        </button>
                      </div>
                    ))}
                  </div>
                </Card>
              )}
            </div>
          )}
        </>
      )}
    </div>
  )
}
