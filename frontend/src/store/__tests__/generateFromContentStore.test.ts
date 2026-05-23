import { describe, it, expect, beforeEach } from 'vitest'
import { useGenerateStore, type OutlineModule } from '../generateFromContentStore'

const sampleOutline: OutlineModule[] = [
  { title: 'M1', description: '', videos: [
    { title: 'V1', description: '', slides: [{ title: 'S1', brief: 'b' }] },
  ]},
]

describe('generateFromContentStore', () => {
  beforeEach(() => {
    useGenerateStore.getState().reset()
  })

  it('starts at step "upload" with no files', () => {
    const s = useGenerateStore.getState()
    expect(s.step).toBe('upload')
    expect(s.files).toEqual([])
  })

  it('setFiles + setSettings update state', () => {
    const f = new File(['x'], 'a.pdf', { type: 'application/pdf' })
    useGenerateStore.getState().setFiles([f])
    useGenerateStore.getState().setSettings({ modules: 3 })
    expect(useGenerateStore.getState().files).toHaveLength(1)
    expect(useGenerateStore.getState().settings.modules).toBe(3)
  })

  it('removeModule/removeVideo/removeSlide edit the outline', () => {
    const st = useGenerateStore.getState()
    st.setOutline(JSON.parse(JSON.stringify(sampleOutline)))
    st.removeSlide(0, 0, 0)
    expect(useGenerateStore.getState().outline[0].videos[0].slides).toHaveLength(0)
    st.removeVideo(0, 0)
    expect(useGenerateStore.getState().outline[0].videos).toHaveLength(0)
    st.removeModule(0)
    expect(useGenerateStore.getState().outline).toHaveLength(0)
  })

  it('renameSlide updates a slide title', () => {
    const st = useGenerateStore.getState()
    st.setOutline(JSON.parse(JSON.stringify(sampleOutline)))
    st.renameSlide(0, 0, 0, 'New Title')
    expect(useGenerateStore.getState().outline[0].videos[0].slides[0].title).toBe('New Title')
  })
})
