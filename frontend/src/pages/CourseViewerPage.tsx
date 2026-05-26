import { useNavigate, useParams } from 'react-router-dom'
import { CoursePlayer } from '@/components/player/CoursePlayer'

export const CourseViewerPage = () => {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  return <CoursePlayer courseId={Number(id)} mode="learner" onExit={() => navigate('/')} />
}
