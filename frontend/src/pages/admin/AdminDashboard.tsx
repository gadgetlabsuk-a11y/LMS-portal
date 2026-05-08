import { useState, useEffect } from 'react'
import { api } from '@/services/api'
import { useAuth } from '@/context/AuthContext'
import { Card } from '@/components/common/Card'

interface DashboardStats {
  users: number
  courses: number
  completionRate: number
  apiCalls: number
}

interface AuditLogEntry {
  action: string
  resource_type: string
  resource_id: string
  timestamp: string
}

interface StatCardProps {
  title: string
  value: number | string
  icon: string
}

const StatCard = ({ title, value, icon }: StatCardProps) => (
  <Card className="p-6">
    <div className="flex items-center justify-between">
      <div>
        <p className="text-gray-600 text-sm">{title}</p>
        <p className="text-3xl font-bold mt-2">{value}</p>
      </div>
      <div className="text-4xl">{icon}</div>
    </div>
  </Card>
)

export const AdminDashboard = () => {
  const [stats, setStats] = useState<DashboardStats>({ users: 0, courses: 0, completionRate: 0, apiCalls: 0 })
  const [activity, setActivity] = useState<AuditLogEntry[]>([])
  const [loading, setLoading] = useState(true)
  const { user } = useAuth()

  useEffect(() => {
    fetchDashboardData()
  }, [])

  const fetchDashboardData = async () => {
    try {
      const [statsRes, activityRes] = await Promise.all([
        api.get('/admin/stats'),
        api.get('/admin/audit-log?limit=5'),
      ])

      if (statsRes.ok) {
        const s = await statsRes.json()
        setStats({
          users: s.total_users ?? s.users ?? 0,
          courses: s.active_courses ?? s.courses ?? 0,
          completionRate: s.completion_rate ?? s.completionRate ?? 0,
          apiCalls: s.api_calls_today ?? s.apiCalls ?? 0,
        })
      }
      if (activityRes.ok) {
        setActivity(await activityRes.json())
      }
    } catch (err) {
      console.error('Failed to fetch dashboard data:', err)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return <div className="text-center py-12"><div className="spin text-4xl inline-block">⏳</div></div>
  }

  return (
    <div className="space-y-6">
      <div className="bg-blue-50 border-l-4 border-blue-500 p-4 rounded">
        <p className="text-lg font-semibold">
          Welcome, {user?.username}! 👋
        </p>
        <p className="text-gray-600 text-sm mt-1">
          Here's what's happening with your LMS today.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard title="Total Users" value={stats.users} icon="👥" />
        <StatCard title="Active Courses" value={stats.courses} icon="📚" />
        <StatCard title="Completion Rate" value={`${stats.completionRate}%`} icon="✅" />
        <StatCard title="API Calls (24h)" value={stats.apiCalls} icon="📡" />
      </div>

      <Card className="p-6">
        <h3 className="text-lg font-bold mb-4">Recent Activity</h3>
        {activity.length === 0 ? (
          <p className="text-gray-500 text-center py-8">No recent activity</p>
        ) : (
          <div className="space-y-3">
            {activity.map((item, idx) => (
              <div key={idx} className="flex items-start space-x-3 pb-3 border-b last:border-b-0">
                <span className="text-2xl">{item.action === 'LOGIN' ? '🔑' : item.action === 'CREATE' ? '➕' : '✏️'}</span>
                <div className="flex-1">
                  <p className="font-medium">{(item.action || '').toUpperCase()}</p>
                  <p className="text-sm text-gray-600">{item.resource_type}: {item.resource_id}</p>
                  <p className="text-xs text-gray-500 mt-1">{new Date(item.timestamp).toLocaleString()}</p>
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  )
}
