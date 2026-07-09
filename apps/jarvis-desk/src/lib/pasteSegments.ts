/** Split en bruger-besked i tekst- og paste-reference-segmenter til render.
 *  En besked med `[paste:<id> +N linjer]` viser en chip (lazy-udfoldelig) i stedet
 *  for referencens råtekst. Ren logik → testbar uden DOM.
 */

export type PasteSegment =
  | { kind: 'text'; text: string }
  | { kind: 'paste'; pasteId: string; lineCount: number }

const PASTE_RE = /\[paste:([A-Za-z0-9_-]+)\s+\+(\d+)\s+linjer\]/g

/** Segmentér: tekst mellem referencer bevares; hver reference bliver et paste-segment. */
export function splitPasteSegments(content: string): PasteSegment[] {
  const raw = content || ''
  const segments: PasteSegment[] = []
  let lastIndex = 0
  PASTE_RE.lastIndex = 0
  let m: RegExpExecArray | null
  while ((m = PASTE_RE.exec(raw)) !== null) {
    if (m.index > lastIndex) {
      segments.push({ kind: 'text', text: raw.slice(lastIndex, m.index) })
    }
    segments.push({ kind: 'paste', pasteId: m[1] ?? '', lineCount: Number(m[2]) || 0 })
    lastIndex = m.index + m[0].length
  }
  if (lastIndex < raw.length) {
    segments.push({ kind: 'text', text: raw.slice(lastIndex) })
  }
  return segments
}

/** Har beskeden mindst én paste-reference? */
export function hasPasteReference(content: string): boolean {
  PASTE_RE.lastIndex = 0
  return PASTE_RE.test(content || '')
}
