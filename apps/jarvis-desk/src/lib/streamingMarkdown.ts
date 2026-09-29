import { scanFences } from './fenceScanner'

/** 29/9-2026: kun en reel, åben linje-fence må holdes tilbage. At tælle
 *  delstrengen ``` slettede almindelig prosa og klippede 4-backtick-blokke. */
export function stabilizeStreamingMarkdown(md: string): string {
  const spans = scanFences(md)
  const last = spans[spans.length - 1]
  if (!last || last.closed) return md
  return md.slice(0, last.start).replace(/\n+$/, '')
}
