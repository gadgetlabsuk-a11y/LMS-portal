import { useGenerateStore } from '@/store/generateFromContentStore'

export function OutlineReviewEditor() {
  const outline = useGenerateStore((s) => s.outline)
  const { removeModule, removeVideo, removeSlide, renameModule, renameVideo, renameSlide } =
    useGenerateStore.getState()

  return (
    <div data-testid="outline-review-editor" className="flex flex-col gap-4">
      {outline.map((m, mi) => (
        <div key={mi} className="border border-gray-200 rounded-lg p-3">
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold text-brand">Module {mi + 1}</span>
            <input
              value={m.title}
              onChange={(e) => renameModule(mi, e.target.value)}
              className="flex-1 border rounded px-2 py-1 text-sm font-medium"
            />
            <button
              data-testid={`remove-module-${mi}`}
              onClick={() => removeModule(mi)}
              className="text-gray-400 hover:text-red-500 text-sm"
              aria-label={`Remove module ${mi + 1}`}
            >&#x2715;</button>
          </div>
          <div className="mt-2 ml-4 flex flex-col gap-2">
            {m.videos.map((v, vi) => (
              <div key={vi} className="border-l-2 border-gray-100 pl-3">
                <div className="flex items-center gap-2">
                  <span className="text-[11px] text-gray-500">Video {vi + 1}</span>
                  <input
                    value={v.title}
                    onChange={(e) => renameVideo(mi, vi, e.target.value)}
                    className="flex-1 border rounded px-2 py-1 text-sm"
                  />
                  <button
                    data-testid={`remove-video-${mi}-${vi}`}
                    onClick={() => removeVideo(mi, vi)}
                    className="text-gray-400 hover:text-red-500 text-sm"
                    aria-label={`Remove video ${vi + 1}`}
                  >&#x2715;</button>
                </div>
                <ul className="mt-1 ml-4 flex flex-col gap-1">
                  {v.slides.map((s, si) => (
                    <li key={si} className="flex items-center gap-2">
                      <span className="text-[11px] text-gray-400 w-5 text-right">{si + 1}.</span>
                      <input
                        value={s.title}
                        onChange={(e) => renameSlide(mi, vi, si, e.target.value)}
                        className="flex-1 border rounded px-2 py-1 text-xs"
                      />
                      <button
                        data-testid={`remove-slide-${mi}-${vi}-${si}`}
                        onClick={() => removeSlide(mi, vi, si)}
                        className="text-gray-400 hover:text-red-500 text-xs"
                        aria-label={`Remove slide ${si + 1}`}
                      >&#x2715;</button>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  )
}
