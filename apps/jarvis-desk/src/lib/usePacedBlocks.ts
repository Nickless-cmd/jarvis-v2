import { useEffect, useRef, useState } from 'react'
import type { ContentBlock } from './sseProtocol'

const TICK_MS = 33
const MIN_CHARS = 5
const MAX_CHARS = 28
const SHORT_TEXT = 32

/** Paces only the current text block. The source blocks remain authoritative. */
export function usePacedBlocks(blocks: ContentBlock[], live: boolean): ContentBlock[] {
  const index = live && blocks.length > 0 && blocks[blocks.length - 1]?.type === 'text'
    ? blocks.length - 1 : -1
  const active = index >= 0
  const target = index >= 0 ? (blocks[index] as Extract<ContentBlock, { type: 'text' }>).text : ''
  const latest = useRef({ index, target })
  latest.current = { index, target }
  const short = useRef({ index: -1, text: '' })
  if (!live) short.current = { index: -1, text: '' }
  else if (index >= 0 && target.length <= SHORT_TEXT) short.current = { index, text: target }
  const [cursor, setCursor] = useState({ index: -1, shown: '' })

  useEffect(() => {
    if (!live) setCursor((previous) => previous.index < 0 ? previous : { index: -1, shown: '' })
  }, [live])

  useEffect(() => {
    if (!active) return
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
        // Keep pace with the measured fast runs while showing small steps.
        const step = Math.min(MAX_CHARS, Math.max(MIN_CHARS, Math.ceil(pending / 12)))
        let end = Math.min(currentTarget.length, shown.length + step)
        const code = currentTarget.charCodeAt(end - 1)
        if (end < currentTarget.length && code >= 0xD800 && code <= 0xDBFF) end++
        return { index: currentIndex, shown: currentTarget.slice(0, end) }
      })
    }, TICK_MS)
    return () => clearInterval(timer)
  }, [active])

  if (index < 0 || target.length <= SHORT_TEXT) return blocks
  const previousShown = cursor.index === index && target.startsWith(cursor.shown) ? cursor.shown : ''
  const shortText = short.current.index === index && target.startsWith(short.current.text)
    ? short.current.text : ''
  const shown = previousShown.length >= shortText.length ? previousShown : shortText
  if (shown === target) return blocks
  return blocks.map((block, i) => i === index ? { ...block, text: shown } as ContentBlock : block)
}
