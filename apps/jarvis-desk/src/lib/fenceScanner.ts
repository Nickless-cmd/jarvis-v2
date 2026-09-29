export interface FenceSpan {
  start: number
  end: number
  closed: boolean
  marker: '`' | '~'
  length: number
}

/** 29/9-2026: stabilisering og strukturfilter må se de samme fences.
 *  Inline backticks er prosa, og en kortere eller anden lukkemarkør må aldrig
 *  få rendererens tekst til at forsvinde. Åbne fences beskyttes frem til EOF. */
export function scanFences(md: string): FenceSpan[] {
  const spans: FenceSpan[] = []
  let open: FenceSpan | null = null
  let offset = 0
  for (const rawLine of md.split('\n')) {
    const line = rawLine.endsWith('\r') ? rawLine.slice(0, -1) : rawLine
    if (open) {
      const close = /^ {0,3}(`+|~+)[ \t]*$/.exec(line)
      if (close && close[1]![0] === open.marker && close[1]!.length >= open.length) {
        open.end = offset + rawLine.length
        open.closed = true
        spans.push(open)
        open = null
      }
    } else {
      const start = /^ {0,3}(`{3,}|~{3,})(.*)$/.exec(line)
      if (start) {
        const marker = start[1]![0] as '`' | '~'
        // CommonMark: en backtick-fence kan ikke have backticks i infostrengen.
        if (marker !== '`' || !start[2]!.includes('`')) {
          open = { start: offset, end: md.length, closed: false, marker, length: start[1]!.length }
        }
      }
    }
    offset += rawLine.length + 1
  }
  if (open) spans.push(open)
  return spans
}
