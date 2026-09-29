export interface FenceSpan {
  start: number
  end: number
  closed: boolean
  marker: '`' | '~'
  length: number
}

export interface FenceMark {
  marker: '`' | '~'
  length: number
}

export function openingFence(line: string): FenceMark | null {
  const match = /^ {0,3}(`{3,}|~{3,})(.*)$/.exec(line.replace(/\r$/, ''))
  if (!match) return null
  const marker = match[1]![0] as '`' | '~'
  if (marker === '`' && match[2]!.includes('`')) return null
  return { marker, length: match[1]!.length }
}

export function closingFence(line: string, open: FenceMark): boolean {
  const match = /^ {0,3}(`+|~+)[ \t]*$/.exec(line.replace(/\r$/, ''))
  return !!match && match[1]![0] === open.marker && match[1]!.length >= open.length
}

/** 29/9-2026: stabilisering og strukturfilter må se de samme fences.
 *  Inline backticks er prosa, og en kortere eller anden lukkemarkør må aldrig
 *  få rendererens tekst til at forsvinde. Åbne fences beskyttes frem til EOF. */
export function scanFences(md: string): FenceSpan[] {
  const spans: FenceSpan[] = []
  let open: FenceSpan | null = null
  let offset = 0
  for (const rawLine of md.split('\n')) {
    if (open) {
      if (closingFence(rawLine, open)) {
        open.end = offset + rawLine.length
        open.closed = true
        spans.push(open)
        open = null
      }
    } else {
      const start = openingFence(rawLine)
      if (start) {
        open = { start: offset, end: md.length, closed: false, ...start }
      }
    }
    offset += rawLine.length + 1
  }
  if (open) spans.push(open)
  return spans
}
