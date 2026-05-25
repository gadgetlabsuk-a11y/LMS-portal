import { useState, useEffect, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { api } from '@/services/api'
import { useToast } from '@/context/ToastContext'
import { Card } from '@/components/common/Card'
import { Button } from '@/components/common/Button'
import { Select } from '@/components/common/Select'
import { Input } from '@/components/common/Input'

interface Member { id: number; username: string; email: string; role: string }
interface Content {
  id: number; content_type: string; course_id: number | null; broadcast_id: number | null
  title: string; is_podcast: boolean
  mandatory: boolean; due_mode: string | null; due_date: string | null; due_days: number | null
}
interface Detail { id: number; name: string; description: string | null; is_active: boolean; members: Member[]; content: Content[] }
interface ComplianceItem {
  content_id: number; content_type: string; title: string; mandatory: boolean
  total_members: number; not_started: number; in_progress: number; completed: number; overdue: number
}
interface Option { id: number; title: string }

export const DepartmentDetailPage = () => {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { showToast } = useToast()

  const [detail, setDetail] = useState<Detail | null>(null)
  const [allUsers, setAllUsers] = useState<{ id: number; username: string }[]>([])
  const [courses, setCourses] = useState<Option[]>([])
  const [broadcasts, setBroadcasts] = useState<Option[]>([])
  const [compliance, setCompliance] = useState<ComplianceItem[]>([])

  const [memberToAdd, setMemberToAdd] = useState('')
  const [target, setTarget] = useState('')   // 'course:3' | 'broadcast:11'
  const [mandatory, setMandatory] = useState(false)
  const [dueMode, setDueMode] = useState('')
  const [dueDate, setDueDate] = useState('')
  const [dueDays, setDueDays] = useState('')

  const load = useCallback(async () => {
    const res = await api.get(`/departments/${id}`)
    if (res.ok) setDetail(await res.json())
    const cres = await api.get(`/departments/${id}/compliance`)
    if (cres.ok) setCompliance((await cres.json()).items || [])
  }, [id])

  useEffect(() => {
    load()
    api.get('/users?page=1&page_size=100').then(async r => {
      if (r.ok) { const d = await r.json(); setAllUsers(Array.isArray(d) ? d : d.items || []) }
    })
    api.get('/courses').then(async r => {
      if (r.ok) { const d = await r.json(); setCourses(Array.isArray(d) ? d : d.items || []) }
    })
    api.get('/ilb/broadcasts').then(async r => {
      if (r.ok) { const d = await r.json(); setBroadcasts(Array.isArray(d) ? d : d.items || []) }
    })
  }, [id, load])

  const addMember = async () => {
    if (!memberToAdd) return
    const res = await api.post(`/departments/${id}/members`, { user_ids: [Number(memberToAdd)] })
    if (res.ok) { showToast('Member added', 'success'); setMemberToAdd(''); load() }
    else showToast('Failed to add member', 'error')
  }

  const removeMember = async (userId: number) => {
    const res = await api.delete(`/departments/${id}/members/${userId}`)
    if (res.ok) { showToast('Member removed', 'success'); load() }
    else showToast('Failed to remove member', 'error')
  }

  const assignContent = async () => {
    if (!target) { showToast('Pick a course or podcast', 'error'); return }
    const [kind, rawId] = target.split(':')
    const payload: Record<string, unknown> = { mandatory }
    if (kind === 'broadcast') payload.broadcast_id = Number(rawId)
    else payload.course_id = Number(rawId)
    if (mandatory && dueMode) {
      payload.due_mode = dueMode
      if (dueMode === 'fixed') payload.due_date = dueDate
      if (dueMode === 'relative') payload.due_days = Number(dueDays)
    }
    const res = await api.post(`/departments/${id}/content`, payload)
    if (res.ok) {
      showToast('Content assigned', 'success')
      setTarget(''); setMandatory(false); setDueMode(''); setDueDate(''); setDueDays('')
      load()
    } else {
      const err = await res.json().catch(() => ({}))
      showToast(err.detail || 'Failed to assign content', 'error')
    }
  }

  const unassign = async (contentId: number) => {
    const res = await api.delete(`/departments/${id}/content/${contentId}`)
    if (res.ok) { showToast('Content unassigned', 'success'); load() }
    else showToast('Failed to unassign', 'error')
  }

  if (!detail) return <p className="text-gray-500">Loading…</p>

  const contentOptions = [
    ...courses.map(c => ({ value: `course:${c.id}`, label: c.title })),
    ...broadcasts.map(b => ({ value: `broadcast:${b.id}`, label: `${b.title} (podcast)` })),
  ]
  const complianceFor = (contentId: number) => compliance.find(c => c.content_id === contentId)

  return (
    <div className="space-y-6">
      <div>
        <button onClick={() => navigate('/admin/departments')} className="text-sm text-blue-600 hover:underline">← All departments</button>
        <h1 className="text-2xl font-bold text-brand-dark mt-1">{detail.name}</h1>
        {detail.description && <p className="text-gray-600">{detail.description}</p>}
      </div>

      <Card className="p-4">
        <h2 className="font-semibold text-lg mb-3">Members</h2>
        <div className="flex gap-2 items-end mb-4">
          <div className="flex-1">
            <Select label="Add user" aria-label="Add user" value={memberToAdd} onChange={e => setMemberToAdd(e.target.value)}
              options={allUsers.map(u => ({ value: String(u.id), label: u.username }))} />
          </div>
          <div className="mb-4"><Button onClick={addMember}>Add</Button></div>
        </div>
        {detail.members.length === 0 ? (
          <p className="text-gray-500 text-sm">No members yet.</p>
        ) : (
          <ul className="divide-y">
            {detail.members.map(m => (
              <li key={m.id} className="flex justify-between items-center py-2">
                <span>{m.username} <span className="text-gray-400 text-sm">({m.email})</span></span>
                <button onClick={() => removeMember(m.id)} className="text-red-500 text-sm hover:underline">Remove</button>
              </li>
            ))}
          </ul>
        )}
      </Card>

      <Card className="p-4">
        <h2 className="font-semibold text-lg mb-3">Assigned content</h2>
        <div className="grid md:grid-cols-2 gap-2 items-start mb-4">
          <Select label="Content to assign" aria-label="Content to assign" value={target} onChange={e => setTarget(e.target.value)}
            options={contentOptions} />
          <div className="flex flex-col gap-2">
            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" aria-label="Mandatory" checked={mandatory} onChange={e => setMandatory(e.target.checked)} />
              Mandatory
            </label>
            {mandatory && (
              <Select label="Deadline type" aria-label="Deadline type" value={dueMode} onChange={e => setDueMode(e.target.value)}
                options={[{ value: 'fixed', label: 'Fixed date' }, { value: 'relative', label: 'Relative (days from joining)' }]} />
            )}
            {mandatory && dueMode === 'fixed' && (
              <Input label="Due date" aria-label="Due date" type="date" value={dueDate} onChange={e => setDueDate(e.target.value)} />
            )}
            {mandatory && dueMode === 'relative' && (
              <Input label="Days to complete" aria-label="Days to complete" type="number" value={dueDays} onChange={e => setDueDays(e.target.value)} />
            )}
          </div>
        </div>
        <Button onClick={assignContent}>Assign</Button>

        {detail.content.length === 0 ? (
          <p className="text-gray-500 text-sm mt-4">No content assigned yet.</p>
        ) : (
          <ul className="divide-y mt-4">
            {detail.content.map(c => {
              const stats = complianceFor(c.id)
              return (
                <li key={c.id} className="py-3">
                  <div className="flex justify-between items-start">
                    <div>
                      <span className="font-medium">{c.title}</span>
                      <span className="ml-2 text-xs rounded px-2 py-0.5 bg-gray-100 text-gray-600">{c.content_type === 'broadcast' ? 'Podcast' : 'Course'}</span>
                      {c.mandatory && <span className="ml-2 text-xs rounded px-2 py-0.5 bg-amber-100 text-amber-700">Mandatory</span>}
                      <div className="text-sm text-gray-500 mt-1">
                        {c.mandatory && c.due_mode === 'fixed' && c.due_date && <>Due {c.due_date.slice(0, 10)}</>}
                        {c.mandatory && c.due_mode === 'relative' && c.due_days != null && <>Due {c.due_days} days after joining</>}
                        {c.mandatory && !c.due_mode && <>No deadline</>}
                      </div>
                    </div>
                    <button onClick={() => unassign(c.id)} className="text-red-500 text-sm hover:underline">Unassign</button>
                  </div>
                  {stats && c.mandatory && (
                    <div className="flex gap-3 mt-2 text-xs text-gray-600">
                      <span className="text-green-600">{stats.completed} completed</span>
                      <span className="text-red-600">{stats.overdue} overdue</span>
                      <span>{stats.in_progress} in progress</span>
                      <span>{stats.not_started} not started</span>
                    </div>
                  )}
                </li>
              )
            })}
          </ul>
        )}
      </Card>
    </div>
  )
}
