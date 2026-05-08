import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '@/context/AuthContext'
import { useToast } from '@/context/ToastContext'
import { Button } from '@/components/common/Button'
import { Input } from '@/components/common/Input'
import { Card } from '@/components/common/Card'

const API_BASE = import.meta.env.PROD ? '/lms' : ''

interface BrandConfig {
  brand_name: string
  primary_color?: string
  secondary_color?: string
  accent_color?: string
  bg_color?: string
  text_color?: string
  font_family?: string
  heading_font?: string
  border_radius?: number
}

export const LoginPage = () => {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [mfaCode, setMfaCode] = useState('')
  const [requiresMfa, setRequiresMfa] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')
  const [brandConfig, setBrandConfig] = useState<BrandConfig>({ brand_name: 'LMS Course Builder' })
  const navigate = useNavigate()
  const { login } = useAuth()
  const { showToast } = useToast()

  useEffect(() => {
    const fetchBrandConfig = async () => {
      try {
        const res = await fetch(API_BASE + '/api/whitelabel/preview')
        if (res.ok) {
          const data: BrandConfig = await res.json()
          setBrandConfig(data)
          applyTheme(data)
        }
      } catch (err) {
        console.error('Failed to fetch brand config:', err)
      }
    }
    fetchBrandConfig()
  }, [])

  const applyTheme = (config: BrandConfig) => {
    if (config.primary_color) document.documentElement.style.setProperty('--primary', config.primary_color)
    if (config.secondary_color) document.documentElement.style.setProperty('--secondary', config.secondary_color)
    if (config.accent_color) document.documentElement.style.setProperty('--accent', config.accent_color)
    if (config.bg_color) document.documentElement.style.setProperty('--bg', config.bg_color)
    if (config.text_color) document.documentElement.style.setProperty('--text', config.text_color)
    if (config.font_family) document.documentElement.style.setProperty('--font-family', config.font_family)
    if (config.heading_font) document.documentElement.style.setProperty('--heading-font', config.heading_font)
    if (config.border_radius) document.documentElement.style.setProperty('--border-radius', `${config.border_radius}px`)
  }

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsLoading(true)
    setError('')

    const result = await login(username, password, requiresMfa ? mfaCode : undefined)

    if (result.success) {
      showToast('Login successful!', 'success')
      navigate('/')
    } else if (result.requiresMfa) {
      setRequiresMfa(true)
      setPassword('')
      setError('')
    } else {
      const errMsg = result.error ?? 'Login failed'
      setError(errMsg)
      showToast(errMsg, 'error')
    }

    setIsLoading(false)
  }

  return (
    <div className="min-h-screen flex items-center justify-center" style={{ backgroundColor: 'var(--bg)' }}>
      <Card className="w-full max-w-md">
        <div className="p-8">
          <div className="text-center mb-8">
            <h1 className="text-3xl font-bold mb-2" style={{ color: 'var(--text)' }}>
              {brandConfig.brand_name}
            </h1>
            <p className="text-gray-600">Admin Portal</p>
          </div>

          <form onSubmit={handleLogin}>
            {!requiresMfa ? (
              <>
                <Input
                  type="text"
                  label="Username"
                  placeholder="Enter your username"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  required
                />
                <Input
                  type="password"
                  label="Password"
                  placeholder="Enter your password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                />
              </>
            ) : (
              <Input
                type="text"
                label="MFA Code"
                placeholder="Enter 6-digit code"
                value={mfaCode}
                onChange={(e) => setMfaCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                maxLength={6}
                required
              />
            )}

            {error && (
              <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded text-red-700 text-sm">
                {error}
              </div>
            )}

            <Button
              type="submit"
              fullWidth
              disabled={isLoading}
            >
              {isLoading ? '⏳ Processing...' : (requiresMfa ? 'Verify MFA' : 'Sign In')}
            </Button>

            {requiresMfa && (
              <Button
                type="button"
                variant="ghost"
                fullWidth
                onClick={() => {
                  setRequiresMfa(false)
                  setMfaCode('')
                  setPassword('')
                }}
                className="mt-2"
              >
                Back to Login
              </Button>
            )}
          </form>
        </div>
      </Card>
    </div>
  )
}
