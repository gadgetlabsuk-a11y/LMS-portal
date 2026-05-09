import type { BuilderModule, BuilderVideo, BuilderQuiz } from '@/components/builder/types'

interface AISuggestionsRailProps {
  modules: BuilderModule[]
  videos: Record<number, BuilderVideo[]>
  quizzes: Record<number, BuilderQuiz[]>
}

interface Nudge {
  testId: string
  title: string
  description: string
}

function computeNudges(
  modules: BuilderModule[],
  videos: Record<number, BuilderVideo[]>,
  quizzes: Record<number, BuilderQuiz[]>
): Nudge[] {
  const nudges: Nudge[] = []

  if (modules.length === 0) {
    nudges.push({
      testId: 'suggestion-no-modules',
      title: 'Add your first module',
      description: 'Start building your course by adding a module.',
    })
    return nudges
  }

  for (const mod of modules) {
    if (!mod.description || mod.description.trim() === '') {
      nudges.push({
        testId: `suggestion-missing-description-${mod.id}`,
        title: `Add description to "${mod.title}"`,
        description: 'A clear description helps learners understand what to expect.',
      })
    }

    const hasVideos = (videos[mod.id] ?? []).length > 0
    const hasQuizzes = (quizzes[mod.id] ?? []).length > 0
    if (!hasVideos && !hasQuizzes) {
      nudges.push({
        testId: `suggestion-empty-module-${mod.id}`,
        title: `Add content to "${mod.title}"`,
        description: 'This module has no videos or quizzes yet.',
      })
    }
  }

  return nudges
}

export function AISuggestionsRail({ modules, videos, quizzes }: AISuggestionsRailProps) {
  const nudges = computeNudges(modules, videos, quizzes)

  if (nudges.length === 0) {
    return (
      <div className="p-3 text-sm text-gray-500">
        No suggestions — course looks complete!
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-2 p-3">
      <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">
        AI Suggestions
      </p>
      {nudges.map(nudge => (
        <div
          key={nudge.testId}
          data-testid={nudge.testId}
          className="rounded border border-blue-100 bg-blue-50 p-3"
        >
          <p className="text-sm font-medium text-blue-900">{nudge.title}</p>
          <p className="text-xs text-blue-700 mt-0.5">{nudge.description}</p>
          <button className="mt-2 text-xs bg-blue-600 text-white px-2 py-1 rounded hover:bg-blue-700">
            Generate
          </button>
        </div>
      ))}
    </div>
  )
}
