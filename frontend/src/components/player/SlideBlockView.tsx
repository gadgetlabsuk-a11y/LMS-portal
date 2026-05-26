export interface PlayerBlock {
  id: number
  type: string
  content: Record<string, unknown> | null
  order_index: number
}

export function SlideBlockView({ block }: { block: PlayerBlock }) {
  const c = (block.content || {}) as Record<string, unknown>
  switch (block.type) {
    case 'heading':
    case 'text':
      return <div className="prose max-w-none text-gray-100" dangerouslySetInnerHTML={{ __html: String(c.html ?? '') }} />
    case 'image':
      return c.url ? <img src={String(c.url)} alt={c.alt ? String(c.alt) : undefined} className="max-w-full rounded" /> : null
    case 'code':
      return <pre className="bg-gray-900 text-green-400 text-sm p-3 rounded overflow-auto"><code>{String(c.code ?? '')}</code></pre>
    case 'quote':
      return <blockquote className="border-l-4 border-indigo-400 pl-4 italic text-gray-200">{String(c.text ?? '')}</blockquote>
    case 'callout':
      return <div className="bg-amber-100 text-amber-900 rounded p-3">{String(c.text ?? '')}</div>
    case 'list': {
      const items = Array.isArray(c.items) ? (c.items as unknown[]) : String(c.text ?? '').split('\n').filter(Boolean)
      return <ul className="list-disc pl-6 text-gray-100">{items.map((it, i) => <li key={i}>{String(it)}</li>)}</ul>
    }
    case 'video': {
      if (!c.url) return null
      const url = String(c.url)
      // YouTube links need an iframe embed (a native <video> tag can't play them).
      const yt = url.match(/(?:youtu\.be\/|youtube\.com\/(?:watch\?v=|embed\/|v\/|shorts\/))([\w-]{11})/)
      if (yt) {
        return (
          <div className="relative w-full max-w-3xl mx-auto overflow-hidden rounded" style={{ aspectRatio: '16 / 9' }}>
            <iframe
              className="absolute inset-0 h-full w-full border-0"
              src={`https://www.youtube.com/embed/${yt[1]}`}
              title="Video"
              allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
              allowFullScreen
            />
          </div>
        )
      }
      return <video controls src={url} className="max-w-full rounded" />
    }
    case 'divider':
      return <hr className="border-gray-600 my-4" />
    default:
      return <p className="text-gray-100">{String(c.text ?? c.html ?? '')}</p>
  }
}
