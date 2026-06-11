/** Hold ufærdige code-fences tilbage under streaming så rendering ikke flasher
 *  mellem brækket og helt layout. Hvis antallet af ``` er ulige, er der en åben
 *  fence — klip fra den sidste fence (og fjern foregående newlines). */
export function stabilizeStreamingMarkdown(md: string): string {
  const fenceCount = (md.match(/```/g) || []).length
  if (fenceCount % 2 === 0) return md
  const lastFence = md.lastIndexOf('```')
  return md.slice(0, lastFence).replace(/\n+$/, '')
}
