export interface BuilderModule {
  id: number
  course_id?: number
  order_index: number
  title: string
  description?: string | null
  status: string | null
  learning_objectives?: unknown[] | null
  estimated_duration_minutes?: number | null
  unlock_rule?: string | null
}

export interface BuilderVideo {
  id: number
  module_id: number
  order_index: number
  title: string
  video_type?: string | null
  status: string | null
}

export interface BuilderQuiz {
  id: number
  module_id: number | null
  order_index?: number
  title: string
  status?: string | null
}
