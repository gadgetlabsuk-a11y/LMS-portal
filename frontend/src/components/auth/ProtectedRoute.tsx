import { ReactNode } from 'react'
import { Navigate } from 'react-router-dom'
import { useAuth } from '@/context/AuthContext'

interface ProtectedRouteProps {
  children: ReactNode
  adminOnly?: boolean
  creatorRoute?: boolean
}

export const ProtectedRoute = ({
  children,
  adminOnly = false,
  creatorRoute = false,
}: ProtectedRouteProps) => {
  const { auth, loading, user } = useAuth()

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="spin text-4xl">⏳</div>
      </div>
    )
  }

  if (!auth) return <Navigate to="/login" replace />

  // Admin-only routes: trainees go to /learn, creators go to /creator
  if (adminOnly) {
    if (user?.role === 'trainee') return <Navigate to="/learn" replace />
    if (user?.role === 'creator') return <Navigate to="/creator" replace />
  }

  // Creator routes: trainees are redirected to /learn
  if (creatorRoute && user?.role === 'trainee') return <Navigate to="/learn" replace />

  return <>{children}</>
}
