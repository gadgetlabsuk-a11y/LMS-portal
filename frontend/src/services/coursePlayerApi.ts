import { api } from './api'

async function unwrap<T>(r: Response): Promise<T> {
  if (!r.ok) throw new Error((await r.json().catch(() => ({}))).detail || `Request failed (${r.status})`)
  return r.json() as Promise<T>
}

export interface PlayerQuestion { id: number; type: string; prompt: string; options: string[] | null; points: number; order_index: number }
export interface PlayerQuiz { id: number; title: string; pass_rate: number; attempts_allowed: number; attempts_remaining: number; attempts_used: number; passed: boolean; last_score: number | null; questions: PlayerQuestion[] }
export interface PlayerSlide { id: number; order_index: number; narration_audio_url: string | null; duration_seconds: number | null; blocks: { id: number; type: string; content: Record<string, unknown> | null; order_index: number }[] }
export interface PlayerVideo { id: number; title: string; order_index: number; slides: PlayerSlide[]; quizzes: PlayerQuiz[] }
export interface PlayerModule { id: number; title: string; order_index: number; videos: PlayerVideo[] }
export interface PlayerCourse { id: number; title: string; progress: number; completed: boolean; modules: PlayerModule[] }
export interface AttemptResult { score: number; passed: boolean; attempts_remaining: number; feedback: { question_id: number; correct: boolean; explanation: string | null }[] | null }

export const coursePlayerApi = {
  getLearnerPlayer: (id: number) => api.get(`/learn/courses/${id}/player`).then((r) => unwrap<PlayerCourse>(r)),
  getPreviewTree: (id: number) => api.get(`/courses/${id}/preview`).then((r) => unwrap<PlayerCourse>(r)),
  postProgress: (id: number, slideId: number) => api.post(`/learn/courses/${id}/progress`, { slide_id: slideId }).then((r) => unwrap<{ progress: number; completed: boolean }>(r)),
  getQuiz: (quizId: number) => api.get(`/learn/quizzes/${quizId}`).then((r) => unwrap<PlayerQuiz>(r)),
  submitAttempt: (quizId: number, answers: Record<string, unknown>) => api.post(`/learn/quizzes/${quizId}/attempt`, { answers }).then((r) => unwrap<AttemptResult>(r)),
}
