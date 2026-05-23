import { useRef, useState } from 'react'
import { api, API_BASE } from '@/services/api'
import { useGenerateStore } from '@/store/generateFromContentStore'
import { OutlineReviewEditor } from './OutlineReviewEditor'

const ALLOWED = ['.pptx', '.docx', '.pdf']
const MAX_FILES = 10

interface Props {
  open: boolean
  onClose: () => void
  onCreated: (courseId: number) => void
}

export function GenerateFromContentWizard({ open, onClose, onCreated }: Props) {
  const s = useGenerateStore()
  const [uploadError, setUploadError] = useState<string | null>(null)
  const [progress, setProgress] = useState({ done: 0, total: 0 })
  const abortRef = useRef<AbortController | null>(null)

  if (!open) return null

  const handleClose = () => {
    abortRef.current?.abort()
    onClose()
  }

  const handleFiles = (fileList: FileList | null) => {
    setUploadError(null)
    if (!fileList) return
    const incoming = Array.from(fileList)
    const bad = incoming.find(f => !ALLOWED.some(ext => f.name.toLowerCase().endsWith(ext)))
    if (bad) {
      setUploadError(`Unsupported file: ${bad.name}. Allowed: .pptx, .docx, .pdf`)
      return
    }
    const combined = [...s.files, ...incoming].slice(0, MAX_FILES)
    s.setFiles(combined)
  }

  const buildSettingsForm = (): FormData => {
    const fd = new FormData()
    s.files.forEach(f => fd.append('files', f))
    fd.append('modules', String(s.settings.modules))
    fd.append('videos_per_module', String(s.settings.videos_per_module))
    fd.append('slides_per_video', String(s.settings.slides_per_video))
    fd.append('tone', s.settings.tone)
    fd.append('difficulty', s.settings.difficulty)
    return fd
  }

  const handleGenerateOutline = async () => {
    s.setError(null)
    s.setStep('generating')
    try {
      const res = await api.postForm('/courses/ai/outline-from-content', buildSettingsForm())
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const outline = await res.json()
      s.setCourseMeta(outline.title || '', outline.description || '')
      s.setOutline(outline.modules || [])
      s.setStep('review')
    } catch {
      s.setError('Could not generate an outline. Try different files or settings.')
      s.setStep('settings')
    }
  }

  const fillVideoContent = async (videoId: number, slideCount: number) => {
    const controller = new AbortController()
    abortRef.current = controller
    const token = localStorage.getItem('token')
    try {
      const res = await fetch(`${API_BASE}/api/videos/${videoId}/ai/generate-content`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({}),
        signal: controller.signal,
      })
      if (!res.body) { setProgress(p => ({ ...p, done: p.done + slideCount })); return }
      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        const chunk = decoder.decode(value)
        for (const line of chunk.split('\n')) {
          if (line.startsWith('data: ')) setProgress(p => ({ ...p, done: p.done + 1 }))
        }
      }
    } catch (e: unknown) {
      if (e instanceof Error && e.name === 'AbortError') throw e
      setProgress(p => ({ ...p, done: p.done + slideCount }))
    }
  }

  const handleCreate = async () => {
    s.setStep('creating')
    try {
      const fd = new FormData()
      s.files.forEach(f => fd.append('files', f))
      fd.append('outline', JSON.stringify({
        title: s.courseTitle, description: s.courseDescription, modules: s.outline,
      }))
      const res = await api.postForm('/courses/from-outline', fd)
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = await res.json()
      const totalSlides = data.videos.reduce(
        (n: number, v: { slide_ids: number[] }) => n + v.slide_ids.length, 0)
      setProgress({ done: 0, total: totalSlides })
      s.setStep('filling')
      for (const v of data.videos as { video_id: number; slide_ids: number[] }[]) {
        await fillVideoContent(v.video_id, v.slide_ids.length)
      }
      s.setStep('done')
      onCreated(data.course_id)
      s.reset()
    } catch (e: unknown) {
      if (e instanceof Error && e.name === 'AbortError') return
      s.setError('Could not create the course. Please try again.')
      s.setStep('review')
    }
  }

  return (
    <div
      data-testid="generate-content-wizard"
      className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
      onClick={(e) => e.target === e.currentTarget && handleClose()}
    >
      <div className="bg-white rounded-xl shadow-2xl w-[680px] max-h-[85vh] flex flex-col overflow-hidden">
        <div className="flex items-center justify-between px-6 py-4 border-b">
          <h2 className="text-lg font-semibold">Generate course from content</h2>
          <button onClick={handleClose} className="text-gray-400 hover:text-gray-700 text-xl">&#x2715;</button>
        </div>

        <div className="flex-1 overflow-y-auto p-6">
          {s.error && <p data-testid="wizard-error" className="text-sm text-red-500 mb-3">{s.error}</p>}

          {s.step === 'upload' && (
            <div className="flex flex-col gap-3">
              <label className="block text-sm font-medium">Upload source files (.pptx, .docx, .pdf)</label>
              <input
                data-testid="content-file-input"
                type="file"
                multiple
                onChange={(e) => handleFiles(e.target.files)}
                className="text-sm"
              />
              {uploadError && <p data-testid="upload-error" className="text-sm text-red-500">{uploadError}</p>}
              <ul className="text-sm text-gray-600 list-disc ml-5">
                {s.files.map((f, i) => <li key={i}>{f.name}</li>)}
              </ul>
              <p className="text-xs text-gray-400">This uses AI credits. Max {MAX_FILES} files.</p>
            </div>
          )}

          {s.step === 'settings' && (
            <div className="flex flex-col gap-3">
              <NumberField label="Modules" value={s.settings.modules} max={8}
                onChange={(v) => s.setSettings({ modules: v })} testid="set-modules" />
              <NumberField label="Videos per module" value={s.settings.videos_per_module} max={6}
                onChange={(v) => s.setSettings({ videos_per_module: v })} testid="set-videos" />
              <NumberField label="Slides per video" value={s.settings.slides_per_video} max={8}
                onChange={(v) => s.setSettings({ slides_per_video: v })} testid="set-slides" />
              <label className="text-sm font-medium">Tone</label>
              <select value={s.settings.tone} onChange={(e) => s.setSettings({ tone: e.target.value })}
                className="border rounded px-3 py-2 text-sm">
                <option value="formal">Formal</option>
                <option value="professional">Professional</option>
                <option value="casual">Casual</option>
              </select>
            </div>
          )}

          {s.step === 'generating' && (
            <div className="flex flex-col items-center gap-2 py-10">
              <div className="animate-spin w-8 h-8 border-4 border-brand border-t-transparent rounded-full" />
              <p className="text-sm text-gray-500">Generating outline…</p>
            </div>
          )}

          {s.step === 'review' && (
            <div className="flex flex-col gap-3">
              <p className="text-sm text-gray-600">Review and edit the proposed structure, then create.</p>
              <OutlineReviewEditor />
            </div>
          )}

          {(s.step === 'creating' || s.step === 'filling') && (
            <div className="flex flex-col items-center gap-3 py-10">
              <div className="animate-spin w-8 h-8 border-4 border-brand border-t-transparent rounded-full" />
              <p className="text-sm text-gray-500">
                {s.step === 'creating' ? 'Creating course…' : `Filling content… ${progress.done}/${progress.total} slides`}
              </p>
            </div>
          )}
        </div>

        <div className="flex items-center justify-between px-6 py-4 border-t bg-gray-50">
          <button onClick={handleClose} className="px-4 py-2 text-sm border rounded text-gray-600">Cancel</button>
          <div className="flex gap-2">
            {s.step === 'upload' && (
              <button
                data-testid="to-settings-btn"
                disabled={s.files.length === 0}
                onClick={() => s.setStep('settings')}
                className="px-4 py-2 text-sm bg-brand text-white rounded disabled:opacity-40"
              >Next</button>
            )}
            {s.step === 'settings' && (
              <>
                <button onClick={() => s.setStep('upload')} className="px-4 py-2 text-sm border rounded">Back</button>
                <button
                  data-testid="generate-outline-btn"
                  onClick={handleGenerateOutline}
                  className="px-4 py-2 text-sm bg-brand text-white rounded"
                >Generate outline</button>
              </>
            )}
            {s.step === 'review' && (
              <button
                data-testid="create-course-btn"
                onClick={handleCreate}
                disabled={s.outline.length === 0}
                className="px-4 py-2 text-sm bg-green-600 text-white rounded disabled:opacity-40"
              >Create course</button>
            )}
            {s.step === 'done' && (
              <button onClick={onClose} className="px-4 py-2 text-sm bg-brand text-white rounded">Done</button>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

function NumberField({ label, value, max, onChange, testid }: {
  label: string; value: number; max: number; onChange: (v: number) => void; testid: string
}) {
  return (
    <div>
      <label className="block text-sm font-medium mb-1">{label} (max {max})</label>
      <input
        data-testid={testid}
        type="number" min={1} max={max} value={value}
        onChange={(e) => onChange(Math.min(max, Math.max(1, parseInt(e.target.value) || 1)))}
        className="border rounded px-3 py-2 text-sm w-32"
      />
    </div>
  )
}
