import { useEffect, useRef } from 'react'

/** Drives one <audio>/<video> element: play while `playing`, pause otherwise, and
 *  advance via the returned onEnded handler; timer fallback when there's no media URL. */
export function useSegmentAutoplay(opts: {
  playing: boolean
  index: number
  mediaUrl: string | null
  text: string | null
  isLast: boolean
  onAdvance: () => void
  enableTimer?: boolean   // default true (broadcast). Course player sets false: no-audio slides wait for Next.
}) {
  const ref = useRef<HTMLMediaElement | null>(null)
  const enableTimer = opts.enableTimer !== false

  useEffect(() => {
    const el = ref.current
    if (!el) return
    if (opts.playing) void el.play().catch(() => {})
    else el.pause()
  }, [opts.playing, opts.index, opts.mediaUrl])

  useEffect(() => {
    if (!enableTimer || !opts.playing || opts.mediaUrl || opts.isLast) return
    const words = (opts.text ?? '').trim().split(/\s+/).filter(Boolean).length
    const seconds = Math.min(20, Math.max(6, words / 2.5))
    const t = setTimeout(opts.onAdvance, seconds * 1000)
    return () => clearTimeout(t)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [opts.playing, opts.mediaUrl, opts.text, opts.index, opts.isLast])

  const onEnded = () => { if (opts.playing && !opts.isLast) opts.onAdvance() }
  return { ref, onEnded }
}
