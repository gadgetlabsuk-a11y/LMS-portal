import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '@/services/api'
import { useToast } from '@/context/ToastContext'
import { Card } from '@/components/common/Card'
import { Badge } from '@/components/common/Badge'

interface RequiredItem {
  content_type: 'course' | 'broadcast'
  course_id: number | null
  broadcast_id: number | null
  title: string
  is_podcast: boolean
  due_date: string | null
  status: 'not_started' | 'in_progress' | 'completed' | 'overdue'
}

const STATUS_VARIANT: Record<RequiredItem['status'], 'info' | 'success' | 'warning' | 'danger'> = {
  not_started: 'info',
  in_progress: 'warning',
  completed: 'success',
  overdue: 'danger',
}

const STATUS_LABEL: Record<RequiredItem['status'], string> = {
  not_started: 'Not started',
  in_progress: 'In progress',
  completed: 'Completed',
  overdue: 'Overdue',
}

export const MyTraining = () => {
  const [items, setItems] = useState<RequiredItem[]>([])
  const [loading, setLoading] = useState(true)
  const { showToast } = useToast()
  const navigate = useNavigate()

  useEffect(() => {
    ;(async () => {
      try {
        const res = await api.get('/learn/required-training')
        if (res.ok) setItems(await res.json())
        else showToast('Failed to load your training', 'error')
      } catch {
        showToast('Failed to load your training', 'error')
      } finally {
        setLoading(false)
      }
    })()
  }, [])

  const launch = (item: RequiredItem) => {
    if (item.content_type === 'course' && item.course_id != null) navigate(`/learn/${item.course_id}`)
    else navigate('/learn/broadcasts')
  }

  return (
    <div>
      <h1 className="text-2xl font-bold text-brand-dark mb-1">My Required Training</h1>
      <p className="text-gray-600 mb-6">Courses and podcasts your department requires you to complete.</p>

      {loading ? (
        <p className="text-gray-500">Loading…</p>
      ) : items.length === 0 ? (
        <Card className="p-6"><p className="text-gray-600">You have no mandatory training right now. 🎉</p></Card>
      ) : (
        <div className="space-y-3">
          {items.map((item, i) => (
            <Card key={`${item.content_type}-${item.course_id ?? item.broadcast_id ?? i}`} className="p-4">
              <div className="flex items-center justify-between gap-4">
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="font-medium truncate">{item.title}</span>
                    <span className="text-xs rounded px-2 py-0.5 bg-gray-100 text-gray-600">{item.is_podcast ? 'Podcast' : 'Course'}</span>
                    <Badge variant={STATUS_VARIANT[item.status]}>{STATUS_LABEL[item.status]}</Badge>
                  </div>
                  <div className="text-sm text-gray-500 mt-1">
                    {item.due_date ? `Due ${item.due_date.slice(0, 10)}` : 'No deadline'}
                  </div>
                </div>
                <button
                  onClick={() => launch(item)}
                  className="text-sm text-blue-600 hover:underline whitespace-nowrap"
                >
                  {item.status === 'completed' ? 'Review' : 'Start'}
                </button>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
