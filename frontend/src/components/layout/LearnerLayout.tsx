import { ReactNode } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '@/context/AuthContext'
import stadlerLogo from '@/assets/stadler-logo.png'

export const LearnerLayout = ({ children }: { children: ReactNode }) => {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <nav className="bg-white border-b border-gray-200 sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-14">
            <img
              src={stadlerLogo}
              alt="SRSUK Learning Portal"
              className="h-7 w-auto cursor-pointer"
              onClick={() => navigate('/learn')}
            />
            <div className="flex items-center gap-6 text-sm">
              <button onClick={() => navigate('/learn')} className="text-gray-600 hover:text-brand">Catalogue</button>
              <button onClick={() => navigate('/learn/my-training')} className="text-gray-600 hover:text-brand">My Training</button>
            </div>
            <div className="flex items-center gap-4">
              <span className="text-sm text-gray-500">{user?.username}</span>
              <button
                onClick={handleLogout}
                className="text-sm text-gray-600 hover:text-brand px-3 py-1 rounded border border-gray-300 hover:border-brand transition-colors"
              >
                Logout
              </button>
            </div>
          </div>
        </div>
      </nav>
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {children}
      </main>
    </div>
  )
}
