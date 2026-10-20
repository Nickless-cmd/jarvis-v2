import { useEffect, useRef, useState } from 'react'
import type { ContentBlock } from './sseProtocol'

const TICK_MS = 33
const MIN_CHARS = 5
const MAX_CHARS = 28
const SHORT_TEXT = 32

/** Code-fladens Desk-kurve. Laget må accelerere, aldrig dumpe resten. */
export function usePacedBlocks(blocks: ContentBlock[], live: boolean): ContentBlock[] {
  const textIndices = blocks.flatMap((block, index) => (block?.type === 'text' ? [index] : []))
  const target = textIndices
    .map((index) => (blocks[index] as Extract<ContentBlock, { type: 'text' }>).text)
    .join('')
  const [cursor, setCursor] = useState<{ key: string; shown: string }>({ key: '', shown: '' })
  const liveRef = useRef(false)
  if (live && textIndices.length > 0) liveRef.current = true

  const generation = useRef(0)
  const previousLive = useRef(live)
  if (previousLive.current !== live) {
    previousLive.current = live
    if (live) {
      generation.current += 1
      liveRef.current = textIndices.length > 0
    }
  }
  const key = String(generation.current)
  const active = textIndices.length > 0 && target.length > 0 && (live || liveRef.current)
  const latest = useRef({ active, target, key })
  latest.current = { active, target, key }

  useEffect(() => {
    if (!active) return
    const timer = setInterval(() => {
      const current = latest.current
      if (!current.active) return
      setCursor((previous) => {
        const shown = previous.key === current.key && current.target.startsWith(previous.shown)
          ? previous.shown : ''
        const pending = current.target.length - shown.length
        if (pending <= 0) return previous
        const step = Math.min(MAX_CHARS, Math.max(MIN_CHARS, Math.ceil(pending / 12)))
        let end = Math.min(current.target.length, shown.length + step)
        const code = current.target.charCodeAt(end - 1)
        if (end < current.target.length && code >= 0xD800 && code <= 0xDBFF) end += 1
        return { key: current.key, shown: current.target.slice(0, end) }
      })
    }, TICK_MS)
    return () => clearInterval(timer)
  }, [active])

  if (!active || target.length <= SHORT_TEXT) return blocks
  const shown = cursor.key === key && target.startsWith(cursor.shown) ? cursor.shown : ''
  if (shown === target) return blocks
  let remaining = shown.length
  return blocks.map((block) => {
    if (block?.type !== 'text') return block
    const count = Math.min(remaining, block.text.length)
    remaining -= count
    return { ...block, text: block.text.slice(0, count) } as ContentBlock
  })
}
