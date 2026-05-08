import { useState, useEffect } from 'react'
import { api } from '@/services/api'
import { useToast } from '@/context/ToastContext'
import { Modal } from '@/components/common/Modal'
import { Button } from '@/components/common/Button'
import { Card } from '@/components/common/Card'
import { Badge } from '@/components/common/Badge'
import { Input } from '@/components/common/Input'
import { Select } from '@/components/common/Select'

interface User {
  id: string
  username: string
  email: string
  role: string
  is_active: boolean
}

interface UserFormData {
  username: string
  email: string
  password: string
  role: string
}

export const UserManagementPage = () => {
  const [users, setUsers] = useState<User[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [roleFilter, setRoleFilter] = useState('')
  const [page, setPage] = useState(1)
  const [modalOpen, setModalOpen] = useState(false)
  const [editingUser, setEditingUser] = useState<User | null>(null)
  const [formData, setFormData] = useState<UserFormData>({ username: '', email: '', password: '', role: 'trainee' })
  const [, setTotalUsers] = useState(0)
  const [formError, setFormError] = useState('')
  const { showToast } = useToast()

  const pageSize = 10

  useEffect(() => {
    fetchUsers()
  }, [page, search, roleFilter])

  const fetchUsers = async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams({
        skip: String((page - 1) * pageSize),
        limit: String(pageSize),
      })
      if (search) params.append('search', search)
      if (roleFilter) params.append('role', roleFilter)

      const res = await api.get(`/users?${params}`)
      if (res.ok) {
        const data = await res.json()
        setUsers(Array.isArray(data) ? data : data.items || [])
        if (data.total !== undefined) setTotalUsers(data.total)
      }
    } catch (err) {
      console.error('Failed to fetch users:', err)
      showToast('Failed to load users', 'error')
    } finally {
      setLoading(false)
    }
  }

  const handleSaveUser = async () => {
    setFormError('')
    if (!formData.username || !formData.email || (!editingUser && !formData.password)) {
      setFormError('Please fill all required fields')
      return
    }

    try {
      const endpoint = editingUser ? `/users/${editingUser.id}` : '/users'
      const method = editingUser ? 'put' : 'post'
      const res = await api[method](endpoint, formData)

      if (res.ok) {
        showToast(editingUser ? 'User updated' : 'User created', 'success')
        setModalOpen(false)
        setEditingUser(null)
        setFormData({ username: '', email: '', password: '', role: 'trainee' })
        fetchUsers()
      } else {
        const err = await res.json()
        const detail = err.detail
        setFormError(
          Array.isArray(detail)
            ? detail.map((e: { msg?: string }) => e.msg || JSON.stringify(e)).join('; ')
            : detail || 'Failed to save user'
        )
      }
    } catch (err) {
      setFormError((err as Error).message)
    }
  }

  const handleDeleteUser = async (userId: string) => {
    if (confirm('Are you sure? This cannot be undone.')) {
      try {
        const res = await api.delete(`/users/${userId}`)
        if (res.ok) {
          showToast('User deleted', 'success')
          fetchUsers()
        } else {
          showToast('Failed to delete user', 'error')
        }
      } catch (err) {
        showToast((err as Error).message, 'error')
      }
    }
  }

  const handleEditUser = (user: User) => {
    setEditingUser(user)
    setFormData({ username: user.username, email: user.email, password: '', role: user.role })
    setModalOpen(true)
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div className="flex gap-4 flex-1">
          <input
            type="text"
            placeholder="Search users..."
            value={search}
            onChange={(e) => {
              setSearch(e.target.value)
              setPage(1)
            }}
            className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <select
            value={roleFilter}
            onChange={(e) => {
              setRoleFilter(e.target.value)
              setPage(1)
            }}
            className="px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="">All Roles</option>
            <option value="admin">Admin</option>
            <option value="creator">Creator</option>
            <option value="trainee">Trainee</option>
          </select>
        </div>
        <Button onClick={() => {
          setEditingUser(null)
          setFormData({ username: '', email: '', password: '', role: 'trainee' })
          setModalOpen(true)
        }}>
          ➕ New User
        </Button>
      </div>

      {loading ? (
        <div className="text-center py-12"><div className="spin text-4xl inline-block">⏳</div></div>
      ) : (
        <Card className="overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50 border-b">
                <tr>
                  <th className="px-6 py-3 text-left text-sm font-semibold">Name</th>
                  <th className="px-6 py-3 text-left text-sm font-semibold">Email</th>
                  <th className="px-6 py-3 text-left text-sm font-semibold">Role</th>
                  <th className="px-6 py-3 text-left text-sm font-semibold">Status</th>
                  <th className="px-6 py-3 text-left text-sm font-semibold">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {users.map(user => (
                  <tr key={user.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 font-medium">{user.username}</td>
                    <td className="px-6 py-4 text-gray-600">{user.email}</td>
                    <td className="px-6 py-4">
                      <Badge variant={user.role === 'admin' ? 'danger' : 'info'}>
                        {user.role}
                      </Badge>
                    </td>
                    <td className="px-6 py-4">
                      <Badge variant={user.is_active ? 'success' : 'warning'}>
                        {user.is_active ? 'Active' : 'Inactive'}
                      </Badge>
                    </td>
                    <td className="px-6 py-4 text-sm space-x-2">
                      <button onClick={() => handleEditUser(user)} className="text-blue-600 hover:underline">
                        Edit
                      </button>
                      <button onClick={() => handleDeleteUser(user.id)} className="text-red-600 hover:underline">
                        Delete
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="px-6 py-4 border-t flex justify-between items-center">
            <p className="text-sm text-gray-600">Page {page}</p>
            <div className="space-x-2">
              <Button variant="secondary" size="sm" onClick={() => setPage(Math.max(1, page - 1))}>
                ← Prev
              </Button>
              <Button variant="secondary" size="sm" onClick={() => setPage(page + 1)}>
                Next →
              </Button>
            </div>
          </div>
        </Card>
      )}

      <Modal open={modalOpen} onClose={() => setModalOpen(false)} title={editingUser ? 'Edit User' : 'Create User'}>
        <div className="space-y-4">
          <Input
            label="Username"
            value={formData.username}
            onChange={(e) => setFormData({ ...formData, username: e.target.value })}
            disabled={!!editingUser}
          />
          <Input
            label="Email"
            type="email"
            value={formData.email}
            onChange={(e) => setFormData({ ...formData, email: e.target.value })}
          />
          {!editingUser && (
            <Input
              label="Password"
              type="password"
              value={formData.password}
              onChange={(e) => setFormData({ ...formData, password: e.target.value })}
            />
          )}
          <Select
            label="Role"
            value={formData.role}
            onChange={(e) => setFormData({ ...formData, role: e.target.value })}
            options={[
              { value: 'trainee', label: 'Trainee' },
              { value: 'creator', label: 'Creator' },
              { value: 'admin', label: 'Admin' },
            ]}
          />
          {formError && (
            <div className="p-3 bg-red-50 border border-red-200 rounded text-red-700 text-sm">
              {formError}
            </div>
          )}
          <div className="flex gap-2 justify-end">
            <Button variant="secondary" onClick={() => setModalOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleSaveUser}>
              Save
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  )
}
