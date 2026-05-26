import { useParams } from 'react-router-dom'
import { CoursePlayer } from '@/components/player/CoursePlayer'

export const CourseViewerPage = () => {
  const { id } = useParams<{ id: string }>()
  return <CoursePlayer courseId={Number(id)} mode="learner" />
}
