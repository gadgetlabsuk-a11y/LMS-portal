import { useState, useEffect, useCallback } from 'react'
import { api } from '@/services/api'
import { useToast } from '@/context/ToastContext'
import { Card } from '@/components/common/Card'
import { Badge } from '@/components/common/Badge'
import { Select } from '@/components/common/Select'

interface Reminder {
  user_id: number
  username: string
  email: string
  content_type: 'course' | 'broadcast'
  course_id: number | null
  broadcast_id: number | null
  title: string
  due_date: string | null
  status: 'overdue' | 'in_progress' | 'not_started'
}

export const RemindersPage = () => {
  const [rows, setRows] = useState<Reminder[]>([])
  const [loading, setLoading] = useState(true)
  const [withinDays, setWithinDays] = useState('14')
  const { showToast } = useToast()

  const fetchReminders = useCallback(async () => {
    setLoading(true)
    try {
      const res = await api.get(`/departments/reminders?within_days=${withinDays}`)
      if (res.ok) setRows(await res.json())
      else showToast('Failed to load reminders', 'error')
    } catch {
      showToast('Failed to load reminders', 'error')
    } finally {
      setLoading(false)
    }
  }, [withinDays])

  useEffect(() => { fetchReminders() }, [fetchReminders])

  // overdue first, then by due date
  const sorted = [...rows].sort((a, b) => {
    if ((a.status === 'overdue') !== (b.status === 'overdue')) return a.status === 'overdue' ? -1 : 1
    return (a.due_date ?? '').localeCompare(b.due_date ?? '')
  })

  return (
    <div>
      <div className="flex justify-between items-center mb-1">
        <h1 className="text-2xl font-bold text-brand-dark">Training Reminders</h1>
        <div className="w-48">
          <Select
            label="Window"
            aria-label="Window"
            value={withinDays}
            onChange={e => setWithinDays(e.target.value)}
            options={[{ value: '7', label: 'Due within 7 days' }, { value: '14', label: 'Due within 14 days' }, { value: '30', label: 'Due within 30 days' }]}
          />
        </div>
      </div>
      <p className="text-gray-600 mb-6">Learners with mandatory training that is past due or due soon.</p>

      {loading ? (
        <p className="text-gray-500">Loading…</p>
      ) : sorted.length === 0 ? (
        <Card className="p-6"><p className="text-gray-600">No one is overdue or due soon. 🎉</p></Card>
      ) : (
        <Card className="p-0 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-gray-600 text-left">
              <tr>
                <th className="px-4 py-2">Learner</th>
                <th className="px-4 py-2">Item</th>
                <th className="px-4 py-2">Due</th>
                <th className="px-4 py-2">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {sorted.map((r, i) => (
                <tr key={`${r.user_id}-${r.content_type}-${r.course_id ?? r.broadcast_id ?? i}`}>
                  <td className="px-4 py-2">
                    <div className="font-medium">{r.username}</div>
                    <div className="text-gray-400 text-xs">{r.email}</div>
                  </td>
                  <td className="px-4 py-2">
                    {r.title}
                    <span className="ml-2 text-xs rounded px-2 py-0.5 bg-gray-100 text-gray-600">{r.content_type === 'broadcast' ? 'Podcast' : 'Course'}</span>
                  </td>
                  <td className="px-4 py-2">{r.due_date ? r.due_date.slice(0, 10) : '—'}</td>
                  <td className="px-4 py-2">
                    {r.status === 'overdue'
                      ? <Badge variant="danger">Overdue</Badge>
                      : <Badge variant="warning">Due soon</Badge>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}
    </div>
  )
}
