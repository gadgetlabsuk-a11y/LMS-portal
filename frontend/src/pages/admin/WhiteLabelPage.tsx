import { useState, useEffect } from 'react'
import { api } from '@/services/api'
import { useToast } from '@/context/ToastContext'
import { Button } from '@/components/common/Button'
import { Card } from '@/components/common/Card'
import { Input } from '@/components/common/Input'
import { Select } from '@/components/common/Select'
import { Textarea } from '@/components/common/Textarea'

interface WhiteLabelConfig {
  brand_name: string
  primary_color: string
  secondary_color: string
  accent_color: string
  bg_color: string
  text_color: string
  font_family: string
  heading_font: string
  border_radius: number
  custom_css: string
  logo_url: string
  favicon_url: string
}

const DEFAULT_CONFIG: WhiteLabelConfig = {
  brand_name: 'Learning Portal',
  primary_color: '#2563EB',
  secondary_color: '#1E3A8A',
  accent_color: '#F59E0B',
  bg_color: '#F8FAFC',
  text_color: '#1E293B',
  font_family: 'system-ui',
  heading_font: 'system-ui',
  border_radius: 8,
  custom_css: '',
  logo_url: '',
  favicon_url: '',
}

export const WhiteLabelPage = () => {
  const [config, setConfig] = useState<WhiteLabelConfig>(DEFAULT_CONFIG)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const { showToast } = useToast()

  useEffect(() => {
    fetchWhitelabelConfig()
  }, [])

  const fetchWhitelabelConfig = async () => {
    try {
      const res = await api.get('/whitelabel/preview')
      if (res.ok) {
        const data = await res.json()
        setConfig(data)
        applyTheme(data)
      }
    } catch (err) {
      showToast('Failed to load config', 'error')
    } finally {
      setLoading(false)
    }
  }

  const applyTheme = (data: WhiteLabelConfig) => {
    if (data.primary_color) document.documentElement.style.setProperty('--primary', data.primary_color)
    if (data.secondary_color) document.documentElement.style.setProperty('--secondary', data.secondary_color)
    if (data.accent_color) document.documentElement.style.setProperty('--accent', data.accent_color)
    if (data.bg_color) document.documentElement.style.setProperty('--bg', data.bg_color)
    if (data.text_color) document.documentElement.style.setProperty('--text', data.text_color)
    if (data.font_family) document.documentElement.style.setProperty('--font-family', data.font_family + ', sans-serif')
    if (data.heading_font) document.documentElement.style.setProperty('--heading-font', data.heading_font + ', sans-serif')
    if (data.border_radius) document.documentElement.style.setProperty('--border-radius', data.border_radius + 'px')
  }

  const handleSave = async () => {
    setSaving(true)
    try {
      const res = await api.put('/whitelabel/config', config)
      if (res.ok) {
        applyTheme(config)
        showToast('Configuration saved!', 'success')
      } else {
        showToast('Failed to save configuration', 'error')
      }
    } catch (err) {
      showToast((err as Error).message, 'error')
    } finally {
      setSaving(false)
    }
  }

  const handleReset = () => {
    if (confirm('Reset to defaults?')) {
      setConfig(DEFAULT_CONFIG)
      applyTheme(DEFAULT_CONFIG)
    }
  }

  const handleExportTheme = () => {
    const json = JSON.stringify(config, null, 2)
    const blob = new Blob([json], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'theme.json'
    a.click()
    URL.revokeObjectURL(url)
  }

  if (loading) {
    return <div className="text-center py-12"><div className="spin text-4xl inline-block">⏳</div></div>
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <div className="lg:col-span-2 space-y-6">
        <Card className="p-6">
          <h3 className="text-lg font-bold mb-4">Branding</h3>
          <Input
            label="Brand Name"
            value={config.brand_name}
            onChange={(e) => setConfig({ ...config, brand_name: e.target.value })}
          />
          <Input
            label="Logo URL"
            type="url"
            value={config.logo_url}
            onChange={(e) => setConfig({ ...config, logo_url: e.target.value })}
          />
          <Input
            label="Favicon URL"
            type="url"
            value={config.favicon_url}
            onChange={(e) => setConfig({ ...config, favicon_url: e.target.value })}
          />
        </Card>

        <Card className="p-6">
          <h3 className="text-lg font-bold mb-4">Colors</h3>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium mb-2">Primary Color</label>
              <div className="flex gap-2">
                <input
                  type="color"
                  value={config.primary_color}
                  onChange={(e) => setConfig({ ...config, primary_color: e.target.value })}
                  className="w-12 h-10 rounded cursor-pointer"
                />
                <input
                  type="text"
                  value={config.primary_color}
                  onChange={(e) => setConfig({ ...config, primary_color: e.target.value })}
                  className="flex-1 px-2 py-1 border rounded text-sm"
                />
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium mb-2">Secondary Color</label>
              <div className="flex gap-2">
                <input
                  type="color"
                  value={config.secondary_color}
                  onChange={(e) => setConfig({ ...config, secondary_color: e.target.value })}
                  className="w-12 h-10 rounded cursor-pointer"
                />
                <input
                  type="text"
                  value={config.secondary_color}
                  onChange={(e) => setConfig({ ...config, secondary_color: e.target.value })}
                  className="flex-1 px-2 py-1 border rounded text-sm"
                />
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium mb-2">Accent Color</label>
              <div className="flex gap-2">
                <input
                  type="color"
                  value={config.accent_color}
                  onChange={(e) => setConfig({ ...config, accent_color: e.target.value })}
                  className="w-12 h-10 rounded cursor-pointer"
                />
                <input
                  type="text"
                  value={config.accent_color}
                  onChange={(e) => setConfig({ ...config, accent_color: e.target.value })}
                  className="flex-1 px-2 py-1 border rounded text-sm"
                />
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium mb-2">Background Color</label>
              <div className="flex gap-2">
                <input
                  type="color"
                  value={config.bg_color}
                  onChange={(e) => setConfig({ ...config, bg_color: e.target.value })}
                  className="w-12 h-10 rounded cursor-pointer"
                />
                <input
                  type="text"
                  value={config.bg_color}
                  onChange={(e) => setConfig({ ...config, bg_color: e.target.value })}
                  className="flex-1 px-2 py-1 border rounded text-sm"
                />
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium mb-2">Text Color</label>
              <div className="flex gap-2">
                <input
                  type="color"
                  value={config.text_color}
                  onChange={(e) => setConfig({ ...config, text_color: e.target.value })}
                  className="w-12 h-10 rounded cursor-pointer"
                />
                <input
                  type="text"
                  value={config.text_color}
                  onChange={(e) => setConfig({ ...config, text_color: e.target.value })}
                  className="flex-1 px-2 py-1 border rounded text-sm"
                />
              </div>
            </div>
          </div>
        </Card>

        <Card className="p-6">
          <h3 className="text-lg font-bold mb-4">Typography & Layout</h3>
          <Select
            label="Font Family"
            value={config.font_family}
            onChange={(e) => setConfig({ ...config, font_family: e.target.value })}
            options={[
              { value: 'Arial', label: 'Arial' },
              { value: 'Inter', label: 'Inter' },
              { value: 'Roboto', label: 'Roboto' },
              { value: 'Open Sans', label: 'Open Sans' },
              { value: 'Lato', label: 'Lato' },
              { value: 'Poppins', label: 'Poppins' },
              { value: 'Montserrat', label: 'Montserrat' },
              { value: 'system-ui', label: 'System UI' },
            ]}
          />
          <Select
            label="Heading Font"
            value={config.heading_font}
            onChange={(e) => setConfig({ ...config, heading_font: e.target.value })}
            options={[
              { value: 'Arial', label: 'Arial' },
              { value: 'Inter', label: 'Inter' },
              { value: 'Roboto', label: 'Roboto' },
              { value: 'Open Sans', label: 'Open Sans' },
              { value: 'Lato', label: 'Lato' },
              { value: 'Poppins', label: 'Poppins' },
              { value: 'Montserrat', label: 'Montserrat' },
              { value: 'system-ui', label: 'System UI' },
            ]}
          />
          <div className="mb-4">
            <label className="block text-sm font-medium mb-2">Border Radius: {config.border_radius}px</label>
            <input
              type="range"
              min="0"
              max="24"
              value={config.border_radius}
              onChange={(e) => setConfig({ ...config, border_radius: parseInt(e.target.value) })}
              className="w-full"
            />
          </div>
        </Card>

        <Card className="p-6">
          <h3 className="text-lg font-bold mb-4">Custom CSS</h3>
          <Textarea
            value={config.custom_css}
            onChange={(e) => setConfig({ ...config, custom_css: e.target.value })}
            placeholder="Enter custom CSS here..."
            rows={6}
          />
        </Card>

        <div className="flex gap-2">
          <Button onClick={handleSave} disabled={saving} className="flex-1">
            {saving ? '💾 Saving...' : '💾 Save Configuration'}
          </Button>
          <Button variant="secondary" onClick={handleReset} className="flex-1">
            🔄 Reset
          </Button>
          <Button variant="ghost" onClick={handleExportTheme} className="flex-1">
            ⬇️ Export
          </Button>
        </div>
      </div>

      <div className="lg:col-span-1">
        <Card className="p-6 sticky top-6">
          <h3 className="text-lg font-bold mb-4">Preview</h3>
          <div
            className="space-y-3 p-4 rounded-lg"
            style={{
              backgroundColor: config.bg_color,
              color: config.text_color,
              fontFamily: config.font_family + ', sans-serif',
              borderRadius: config.border_radius + 'px',
            }}
          >
            <div>
              <h2
                className="text-lg font-bold mb-2"
                style={{
                  fontFamily: config.heading_font + ', sans-serif',
                  color: config.primary_color,
                }}
              >
                {config.brand_name}
              </h2>
            </div>

            {config.logo_url && (
              <img src={config.logo_url} alt="Logo" className="w-full max-h-20 object-contain mb-2" />
            )}

            <div className="space-y-2">
              <button
                className="w-full py-2 rounded-lg font-medium text-white transition"
                style={{
                  backgroundColor: config.primary_color,
                  borderRadius: config.border_radius + 'px',
                }}
              >
                Primary Button
              </button>
              <button
                className="w-full py-2 rounded-lg font-medium text-white transition"
                style={{
                  backgroundColor: config.secondary_color,
                  borderRadius: config.border_radius + 'px',
                }}
              >
                Secondary Button
              </button>
              <button
                className="w-full py-2 rounded-lg font-medium text-white transition"
                style={{
                  backgroundColor: config.accent_color,
                  borderRadius: config.border_radius + 'px',
                }}
              >
                Accent Button
              </button>
            </div>

            <div className="pt-3 border-t" style={{ borderColor: config.text_color + '33' }}>
              <p className="text-xs opacity-75">
                This is a preview of your theme. Colors and fonts are applied in real-time.
              </p>
            </div>
          </div>
        </Card>
      </div>
    </div>
  )
}
