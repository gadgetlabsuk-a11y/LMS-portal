import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '@/services/api'
import { useToast } from '@/context/ToastContext'
import { Modal } from '@/components/common/Modal'
import { Button } from '@/components/common/Button'
import { Card } from '@/components/common/Card'
import { Input } from '@/components/common/Input'

interface Department {
  id: number
  name: string
  description: string | null
  is_active: boolean
  member_count: number
  content_count: number
}

export const DepartmentsPage = () => {
  const [departments, setDepartments] = useState<Department[]>([])
  const [loading, setLoading] = useState(true)
  const [modalOpen, setModalOpen] = useState(false)
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [formError, setFormError] = useState('')
  const { showToast } = useToast()
  const navigate = useNavigate()

  useEffect(() => { fetchDepartments() }, [])

  const fetchDepartments = async () => {
    setLoading(true)
    try {
      const res = await api.get('/departments')
      if (res.ok) setDepartments(await res.json())
    } catch {
      showToast('Failed to load departments', 'error')
    } finally {
      setLoading(false)
    }
  }

  const handleCreate = async () => {
    setFormError('')
    if (!name.trim()) { setFormError('Name is required'); return }
    const res = await api.post('/departments', { name, description })
    if (res.ok) {
      showToast('Department created', 'success')
      setModalOpen(false); setName(''); setDescription('')
      fetchDepartments()
    } else {
      const err = await res.json().catch(() => ({}))
      setFormError(err.detail || 'Failed to create department')
    }
  }

  const handleDelete = async (id: number) => {
    if (!confirm('Delete this department? Members and assignments are removed; learner progress is kept.')) return
    const res = await api.delete(`/departments/${id}`)
    if (res.ok) { showToast('Department deleted', 'success'); fetchDepartments() }
    else showToast('Failed to delete department', 'error')
  }

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold text-brand-dark">Departments</h1>
        <Button onClick={() => setModalOpen(true)}>+ New Department</Button>
      </div>

      {loading ? (
        <p className="text-gray-500">Loading…</p>
      ) : departments.length === 0 ? (
        <Card><p className="text-gray-500 p-4">No departments yet. Create one to start assigning training.</p></Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {departments.map(d => (
            <Card key={d.id} className="p-4">
              <div className="flex justify-between items-start">
                <button className="text-left" onClick={() => navigate(`/admin/departments/${d.id}`)}>
                  <h3 className="font-semibold text-lg text-brand-dark hover:underline">{d.name}</h3>
                </button>
                <button onClick={() => handleDelete(d.id)} className="text-red-500 text-sm hover:underline">Delete</button>
              </div>
              {d.description && <p className="text-sm text-gray-600 mt-1">{d.description}</p>}
              <div className="flex gap-4 mt-3 text-sm text-gray-500">
                <span>{d.member_count} members</span>
                <span>{d.content_count} assignments</span>
              </div>
            </Card>
          ))}
        </div>
      )}

      <Modal open={modalOpen} onClose={() => setModalOpen(false)} title="New Department">
        <div className="space-y-2">
          {formError && <p className="text-red-500 text-sm">{formError}</p>}
          <Input label="Name" value={name} onChange={e => setName(e.target.value)} placeholder="e.g. Operations" />
          <Input label="Description" value={description} onChange={e => setDescription(e.target.value)} placeholder="Optional" />
          <div className="flex justify-end gap-2">
            <Button variant="secondary" onClick={() => setModalOpen(false)}>Cancel</Button>
            <Button onClick={handleCreate}>Create</Button>
          </div>
        </div>
      </Modal>
    </div>
  )
}
