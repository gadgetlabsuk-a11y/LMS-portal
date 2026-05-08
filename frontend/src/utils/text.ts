/**
 * Strip markdown code fences / raw JSON from descriptions before display.
 * Migrated from frontend/index.html.monolith.bak lines 249–258.
 */
export const safeDesc = (text: string | null | undefined, maxLen = 160): string => {
  if (!text) return ''
  let t = text.trim()
  // Strip ```json ... ``` or ``` ... ``` blocks
  t = t.replace(/^```(?:json)?\s*/i, '').replace(/```[\s\S]*$/, '').trim()
  // If what remains looks like raw JSON, don't show it
  if (t.startsWith('{') || t.startsWith('[')) return 'Course content generated.'
  return t.length > maxLen ? t.slice(0, maxLen) + '…' : t
}
