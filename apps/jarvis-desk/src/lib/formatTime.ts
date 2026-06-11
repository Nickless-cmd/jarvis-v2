/** Relativ tid på dansk: "nu", "5 min siden", "2 t siden", ellers dato. */
export function formatRelativeTime(iso: string): string {
  try {
    const date = new Date(iso)
    const diffMs = Date.now() - date.getTime()
    const min = Math.round(diffMs / 60_000)
    if (min < 1) return 'nu'
    if (min < 60) return `${min} min siden`
    const hr = Math.round(min / 60)
    if (hr < 24) return `${hr} t siden`
    return date.toLocaleDateString('da-DK', { day: 'numeric', month: 'short' })
  } catch {
    return ''
  }
}

/** Udtræk ren tekst fra content-blocks (til kopiér/læs op). */
export function blocksToPlainText(blocks: { type: string; text?: string; thinking?: string }[]): string {
  return blocks
    .map((b) => (b.type === 'text' ? b.text ?? '' : ''))
    .filter(Boolean)
    .join('\n\n')
}
