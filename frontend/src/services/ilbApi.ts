import { api } from './api'

// ILB (Interactive Learning Broadcast) API client.
// Thin typed wrappers over the authed fetch helper in api.ts.

export interface BroadcastSession {
  id: number
  enrollment_id: number
  mode: string
  completion_status: string
  started_at: string
  completed_at: string | null
  final_score: number | null
}

export interface LiveTransport {
  provider: string
  avatar_id: string
  livekit_url: string
  token: string
  session_id: string
}

export interface StartSessionResult {
  session: BroadcastSession
  live: LiveTransport
}

export interface AskResult {
  answer: string
  source_refs: string[]
  confidence: number
  covered: boolean
  escalated: boolean
  disclaimer: string
}

export interface Attestation {
  sequence: number
  content_hash: string
  prev_hash: string | null
  timestamp_token: string | null
  anchor_ref: string | null
}

export interface CompleteResult {
  session: BroadcastSession
  attestation: Attestation
}

export interface PodcastScript {
  script: string
  segments: string[]
}

export interface PodcastConfig {
  course_id: number
  script: string | null
  host_persona: string | null
  avatar_id: string | null
  voice_id: string | null
  segments: string[] | null
  segment_audio: string[] | null
  published: boolean
}

export interface Voice {
  voice_id: string
  name: string
  description: string
}

async function unwrap<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let detail = `Request failed (${res.status})`
    try {
      const body = await res.json()
      if (body?.detail) detail = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail)
    } catch {
      /* non-JSON error body */
    }
    throw new Error(detail)
  }
  return res.json() as Promise<T>
}

export const ilbApi = {
  startSession: (courseId: number, mode: string): Promise<StartSessionResult> =>
    api.post('/ilb/sessions', { course_id: courseId, mode }).then((r) => unwrap<StartSessionResult>(r)),

  getSession: (sessionId: number): Promise<BroadcastSession> =>
    api.get(`/ilb/sessions/${sessionId}`).then((r) => unwrap<BroadcastSession>(r)),

  ask: (sessionId: number, question: string, inputMode: 'text' | 'voice' = 'text'): Promise<AskResult> =>
    api
      .post(`/ilb/sessions/${sessionId}/ask`, { question, input_mode: inputMode })
      .then((r) => unwrap<AskResult>(r)),

  complete: (sessionId: number, finalScore?: number): Promise<CompleteResult> =>
    api
      .post(`/ilb/sessions/${sessionId}/complete`, { final_score: finalScore ?? null })
      .then((r) => unwrap<CompleteResult>(r)),

  getAuditPack: (sessionId: number): Promise<Record<string, unknown>> =>
    api.get(`/ilb/sessions/${sessionId}/audit-pack`).then((r) => unwrap<Record<string, unknown>>(r)),

  generatePodcastScript: (courseId: number, hostPersona: string, targetMinutes: number): Promise<PodcastScript> =>
    api
      .post(`/ilb/courses/${courseId}/podcast-script`, { host_persona: hostPersona, target_minutes: targetMinutes })
      .then((r) => unwrap<PodcastScript>(r)),

  getPodcast: (courseId: number): Promise<PodcastConfig> =>
    api.get(`/ilb/courses/${courseId}/podcast`).then((r) => unwrap<PodcastConfig>(r)),

  savePodcast: (courseId: number, script: string, hostPersona: string, avatarId: string, voiceId: string): Promise<PodcastConfig> =>
    api
      .put(`/ilb/courses/${courseId}/podcast`, { script, host_persona: hostPersona, avatar_id: avatarId, voice_id: voiceId })
      .then((r) => unwrap<PodcastConfig>(r)),

  publishPodcast: (courseId: number, published = true): Promise<PodcastConfig> =>
    api
      .post(`/ilb/courses/${courseId}/podcast/publish`, { published })
      .then((r) => unwrap<PodcastConfig>(r)),

  listVoices: (): Promise<Voice[]> => api.get('/ilb/voices').then((r) => unwrap<Voice[]>(r)),

  renderAudio: (courseId: number): Promise<{ segment_audio: string[] }> =>
    api.post(`/ilb/courses/${courseId}/podcast/render-audio`, {}).then((r) => unwrap<{ segment_audio: string[] }>(r)),
}
