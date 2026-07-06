import { ReactNode, useState, useEffect } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { useAuth } from '@/context/AuthContext'
import brandLogo from '@/assets/logo.svg'

const API_BASE = import.meta.env.PROD ? '/lms' : ''

interface NavItem {
  label: string
  path: string
  icon: string
}

const navItems: NavItem[] = [
  { label: 'Dashboard', path: '/creator', icon: '📊' },
  { label: 'My Courses', path: '/creator/courses', icon: '📚' },
  { label: 'Podcasts', path: '/creator/podcasts', icon: '🎙️' },
  { label: 'Learners', path: '/creator/learners', icon: '👥' },
]

export const CreatorLayout = ({ children }: { children: ReactNode }) => {
  const { user, logout } = useAuth()
  const location = useLocation()
  const navigate = useNavigate()
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [brandName, setBrandName] = useState('Learning Portal')
  const [logoUrl, setLogoUrl] = useState('')

  useEffect(() => {
    fetch(API_BASE + '/api/whitelabel/preview')
      .then(r => r.ok ? r.json() : null)
      .then(d => {
        if (d) {
          setBrandName(d.brand_name || 'Learning Portal')
          setLogoUrl(d.logo_url || '')
        }
      })
      .catch(() => {})
  }, [])

  const getPageTitle = () => {
    const item = navItems.find(n => n.path === location.pathname)
    return item ? item.label : 'Creator Portal'
  }

  return (
    <div className="flex h-screen bg-gray-100">
      {/* Sidebar */}
      <div className={`${sidebarOpen ? 'w-64' : 'w-20'} bg-brand-dark text-white transition-all duration-200 flex flex-col`}>
        <div className="p-4 border-b border-white/15 flex items-center justify-center h-16">
          <img
            src={logoUrl || brandLogo}
            alt={brandName}
            className={`${sidebarOpen ? 'h-7' : 'h-6 w-6 object-left'} w-auto max-w-full object-contain`}
            style={logoUrl ? undefined : { filter: 'brightness(0) invert(1)' }}
          />
        </div>

        <nav className="flex-1 p-4 space-y-2">
          {navItems.map(item => (
            <button
              key={item.path}
              onClick={() => navigate(item.path)}
              className={`w-full flex items-center space-x-3 px-3 py-2 rounded-lg border-l-4 transition ${location.pathname === item.path ? 'bg-blue-600 border-brand-accent' : 'border-transparent hover:bg-white/10'}`}
            >
              <span className="text-xl">{item.icon}</span>
              {sidebarOpen && <span>{item.label}</span>}
            </button>
          ))}
        </nav>

        <div className="p-4 border-t border-white/15 space-y-2">
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="w-full flex items-center justify-center px-3 py-2 rounded-lg hover:bg-white/10 transition text-sm"
          >
            {sidebarOpen ? '◀' : '▶'}
          </button>
          <button
            onClick={() => { logout(); navigate('/login') }}
            className="w-full flex items-center space-x-3 px-3 py-2 rounded-lg hover:bg-white/10 transition text-red-400"
          >
            <span className="text-xl">🚪</span>
            {sidebarOpen && <span>Logout</span>}
          </button>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col">
        {/* Top Bar */}
        <div className="bg-white border-b border-gray-200 p-4 flex justify-between items-center shadow-sm">
          <h2 className="text-2xl font-bold text-brand-dark border-b-2 border-brand-accent pb-1">{getPageTitle()}</h2>
          <div className="flex items-center space-x-4">
            {user && (
              <div className="flex items-center space-x-2">
                <div className="w-10 h-10 rounded-full bg-blue-600 text-white flex items-center justify-center font-bold">
                  {user.username?.charAt(0).toUpperCase()}
                </div>
                <div className="text-sm">
                  <p className="font-medium">{user.username}</p>
                  <p className="text-gray-500 text-xs">{user.role}</p>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Page Content */}
        <div className="flex-1 overflow-auto p-6">
          {children}
        </div>
      </div>
    </div>
  )
}
