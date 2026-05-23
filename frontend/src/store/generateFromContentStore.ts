import { create } from 'zustand'

export interface OutlineSlide { title: string; brief: string }
export interface OutlineVideo { title: string; description: string; slides: OutlineSlide[] }
export interface OutlineModule { title: string; description: string; videos: OutlineVideo[] }

export type WizardStep = 'upload' | 'settings' | 'generating' | 'review' | 'creating' | 'filling' | 'done'

export interface GenSettings {
  modules: number
  videos_per_module: number
  slides_per_video: number
  tone: string
  difficulty: string
}

interface GenerateState {
  step: WizardStep
  files: File[]
  settings: GenSettings
  outline: OutlineModule[]
  courseTitle: string
  courseDescription: string
  error: string | null
  setStep: (s: WizardStep) => void
  setFiles: (f: File[]) => void
  setSettings: (patch: Partial<GenSettings>) => void
  setOutline: (o: OutlineModule[]) => void
  setCourseMeta: (title: string, description: string) => void
  setError: (e: string | null) => void
  removeModule: (mi: number) => void
  removeVideo: (mi: number, vi: number) => void
  removeSlide: (mi: number, vi: number, si: number) => void
  renameModule: (mi: number, title: string) => void
  renameVideo: (mi: number, vi: number, title: string) => void
  renameSlide: (mi: number, vi: number, si: number, title: string) => void
  reset: () => void
}

const DEFAULT_SETTINGS: GenSettings = {
  modules: 3, videos_per_module: 2, slides_per_video: 4,
  tone: 'formal', difficulty: 'intermediate',
}

export const useGenerateStore = create<GenerateState>((set) => ({
  step: 'upload',
  files: [],
  settings: { ...DEFAULT_SETTINGS },
  outline: [],
  courseTitle: '',
  courseDescription: '',
  error: null,
  setStep: (step) => set({ step }),
  setFiles: (files) => set({ files }),
  setSettings: (patch) => set((s) => ({ settings: { ...s.settings, ...patch } })),
  setOutline: (outline) => set({ outline }),
  setCourseMeta: (courseTitle, courseDescription) => set({ courseTitle, courseDescription }),
  setError: (error) => set({ error }),
  removeModule: (mi) => set((s) => ({ outline: s.outline.filter((_, i) => i !== mi) })),
  removeVideo: (mi, vi) => set((s) => ({
    outline: s.outline.map((m, i) =>
      i === mi ? { ...m, videos: m.videos.filter((_, j) => j !== vi) } : m),
  })),
  removeSlide: (mi, vi, si) => set((s) => ({
    outline: s.outline.map((m, i) => i === mi ? {
      ...m, videos: m.videos.map((v, j) => j === vi ?
        { ...v, slides: v.slides.filter((_, k) => k !== si) } : v),
    } : m),
  })),
  renameModule: (mi, title) => set((s) => ({
    outline: s.outline.map((m, i) => i === mi ? { ...m, title } : m),
  })),
  renameVideo: (mi, vi, title) => set((s) => ({
    outline: s.outline.map((m, i) => i === mi ? {
      ...m, videos: m.videos.map((v, j) => j === vi ? { ...v, title } : v),
    } : m),
  })),
  renameSlide: (mi, vi, si, title) => set((s) => ({
    outline: s.outline.map((m, i) => i === mi ? {
      ...m, videos: m.videos.map((v, j) => j === vi ? {
        ...v, slides: v.slides.map((sl, k) => k === si ? { ...sl, title } : sl),
      } : v),
    } : m),
  })),
  reset: () => set({
    step: 'upload', files: [], settings: { ...DEFAULT_SETTINGS },
    outline: [], courseTitle: '', courseDescription: '', error: null,
  }),
}))
