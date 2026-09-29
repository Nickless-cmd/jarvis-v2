import { scanFences } from './fenceScanner'

/** 29/9-2026: kun en reel, åben linje-fence må holdes tilbage. At tælle
 *  delstrengen ``` slettede almindelig prosa og klippede 4-backtick-blokke.
 *  Afsluttede kodelinjer vises straks; den ufuldstændige sidste linje skjules,
 *  så parseren ikke skifter layout for hvert tegn midt i en linje. */
export function stabilizeStreamingMarkdown(md: string): string {
  const spans = scanFences(md)
  const last = spans[spans.length - 1]
  if (!last || last.closed) return md
  const openerEnd = md.indexOf('\n', last.start)
  const completeEnd = md.lastIndexOf('\n')
  if (openerEnd >= 0 && completeEnd > openerEnd) {
    return md.slice(0, completeEnd + 1) + last.marker.repeat(last.length)
  }
  return md.slice(0, last.start).replace(/\n+$/, '')
}
