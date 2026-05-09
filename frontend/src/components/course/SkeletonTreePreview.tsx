/**
 * SkeletonTreePreview
 * Pure client-side component for Modal 1B.
 * Renders a tree preview of the course structure from number inputs.
 * No API calls — re-renders synchronously on every prop change.
 */

interface SkeletonTreePreviewProps {
  moduleCount: number
  videosPerModule: number
  quizPerModule: boolean
}

interface SkeletonNode {
  type: 'module' | 'video' | 'quiz'
  label: string
  depth: number
}

function buildSkeletonNodes(
  moduleCount: number,
  videosPerModule: number,
  quizPerModule: boolean
): SkeletonNode[] {
  const nodes: SkeletonNode[] = []
  const safeMods = Math.max(0, Math.min(moduleCount, 20))
  const safeVids = Math.max(0, Math.min(videosPerModule, 20))

  for (let mi = 0; mi < safeMods; mi++) {
    nodes.push({ type: 'module', label: `Module ${mi + 1}`, depth: 0 })
    for (let vi = 0; vi < safeVids; vi++) {
      nodes.push({ type: 'video', label: `Video ${vi + 1}`, depth: 1 })
    }
    if (quizPerModule) {
      nodes.push({ type: 'quiz', label: 'Quiz', depth: 1 })
    }
  }
  return nodes
}

const NODE_ICONS: Record<SkeletonNode['type'], string> = {
  module: '\u{1F4E6}',
  video: '▶',
  quiz: '✓',
}

const NODE_BADGE: Record<SkeletonNode['type'], string> = {
  module: 'module',
  video: 'video',
  quiz: 'assessment',
}

const NODE_COLORS: Record<SkeletonNode['type'], string> = {
  module: '#6366f1',   // indigo
  video: '#0ea5e9',    // sky
  quiz: '#10b981',     // emerald
}

export function SkeletonTreePreview({
  moduleCount,
  videosPerModule,
  quizPerModule,
}: SkeletonTreePreviewProps) {
  const nodes = buildSkeletonNodes(moduleCount, videosPerModule, quizPerModule)

  if (nodes.length === 0) {
    return (
      <div style={{ padding: '12px', color: '#9ca3af', fontSize: '14px' }}>
        Set module and video counts above to preview the structure.
      </div>
    )
  }

  return (
    <ul
      style={{
        listStyle: 'none',
        padding: '0',
        margin: '0',
        fontFamily: 'inherit',
        fontSize: '14px',
      }}
    >
      {nodes.map((node, idx) => (
        <li
          key={idx}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            paddingLeft: `${node.depth * 20 + 8}px`,
            paddingTop: '6px',
            paddingBottom: '6px',
            borderBottom: '1px solid #f3f4f6',
            color: node.type === 'module' ? '#1f2937' : '#6b7280',
            fontWeight: node.type === 'module' ? 600 : 400,
          }}
        >
          <span style={{ color: NODE_COLORS[node.type], fontSize: '12px', width: '16px' }}>
            {NODE_ICONS[node.type]}
          </span>
          <span>{node.label}</span>
          <span
            style={{
              marginLeft: 'auto',
              fontSize: '11px',
              padding: '1px 6px',
              borderRadius: '9999px',
              backgroundColor: '#f3f4f6',
              color: '#9ca3af',
              textTransform: 'capitalize',
            }}
          >
            {NODE_BADGE[node.type]}
          </span>
        </li>
      ))}
    </ul>
  )
}
