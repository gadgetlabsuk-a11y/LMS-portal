import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '@/context/AuthContext'

export const SmartRedirect = () => {
  const { user, loading } = useAuth()
  const navigate = useNavigate()

  useEffect(() => {
    if (loading) return
    if (!user) { navigate('/login', { replace: true }); return }
    if (user.role === 'admin') navigate('/admin', { replace: true })
    else if (user.role === 'creator') navigate('/creator', { replace: true })
    else navigate('/learn', { replace: true })
  }, [user, loading, navigate])

  return null
}
