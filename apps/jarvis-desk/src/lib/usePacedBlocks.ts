import { useEffect, useRef, useState } from 'react'
import type { ContentBlock } from './sseProtocol'

const TICK_MS = 33
const MIN_CHARS = 5
const MAX_CHARS = 18
const SHORT_TEXT = 32
/** Hvor langt visningen må sakke bagud, før vi springer frem til grænsen.
 *  Loftet på MAX_CHARS pr. tick kan ikke følge en hurtigere kilde alene, og
 *  uden en grænse hober forskellen sig op for evigt — målt 10/10-2026:
 *  679 tegns efterslæb efter 90 frames ved 25 tegn pr. frame. */
const BACKLOG_MAX = 330

/** Paces only the current text block. The source blocks remain authoritative. */
export function usePacedBlocks(blocks: ContentBlock[], live: boolean): ContentBlock[] {
  const index = live && blocks.length > 0 && blocks[blocks.length - 1]?.type === 'text'
    ? blocks.length - 1 : -1
  const target = index >= 0 ? (blocks[index] as Extract<ContentBlock, { type: 'text' }>).text : ''
  const latest = useRef({ index, target })
  latest.current = { index, target }
  const short = useRef({ index: -1, text: '' })
  if (!live) short.current = { index: -1, text: '' }
  else if (index >= 0 && target.length <= SHORT_TEXT) short.current = { index, text: target }
  const [cursor, setCursor] = useState({ index: -1, shown: '' })

  useEffect(() => {
    if (!live || index < 0) return
    const timer = setInterval(() => {
      const { index: currentIndex, target: currentTarget } = latest.current
      setCursor((previous) => {
        const previousShown = previous.index === currentIndex && currentTarget.startsWith(previous.shown)
          ? previous.shown : ''
        const shortText = short.current.index === currentIndex && currentTarget.startsWith(short.current.text)
          ? short.current.text : ''
        const shown = previousShown.length >= shortText.length ? previousShown : shortText
        const pending = currentTarget.length - shown.length
        if (pending <= 0) return previous
        // Jævn kadence: små trin så længe vi kan følge kilden.
        const step = Math.min(MAX_CHARS, Math.max(MIN_CHARS, Math.ceil(pending / 8)))
        // …og grænsen der gør at vi ALTID indhenter: er vi mere end
        // BACKLOG_MAX bagud, springer vi frem til grænsen i stedet.
        const from = Math.max(shown.length + step, currentTarget.length - BACKLOG_MAX)
        return { index: currentIndex, shown: currentTarget.slice(0, from) }
      })
    }, TICK_MS)
    return () => clearInterval(timer)
  }, [live, index >= 0])

  if (index < 0 || target.length <= SHORT_TEXT) return blocks
  const previousShown = cursor.index === index && target.startsWith(cursor.shown) ? cursor.shown : ''
  const shortText = short.current.index === index && target.startsWith(short.current.text)
    ? short.current.text : ''
  const shown = previousShown.length >= shortText.length ? previousShown : shortText
  if (shown === target) return blocks
  return blocks.map((block, i) => i === index ? { ...block, text: shown } as ContentBlock : block)
}
