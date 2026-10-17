import { useEffect, useRef, useState } from 'react'
import type { ContentBlock } from './sseProtocol'

const MIN_CODE_POINTS = 5
/** Loft pr. frame. Var 30 — men et efterslæb på flere tusinde tegn kan ikke
 *  indhentes med 30/frame uden at springe, og springet VAR dumpet: backlog-
 *  reglen satte `end` til `target - 300`, så 2700 af 3000 tegn kom i første
 *  frame (målt 17/10-2026). 60/frame indhenter 3000 tegn på ~50 frames
 *  (~0,8 s ved 60 fps), hvilket læses som en strøm — ikke som en klump. */
const MAX_CODE_POINTS = 60

export interface ChatPacingOptions {
  live: boolean
  finalAnswerStarted: boolean
  runId?: string | null
}

interface Cursor {
  key: string
  shown: string
}

function codePoints(value: string): string[] {
  return Array.from(value)
}

/** Paces only the newest final text block; every non-text block stays immediate. */
export function useChatPacedBlocks(
  blocks: readonly ContentBlock[],
  options: ChatPacingOptions,
): ContentBlock[] {
  let index = -1
  if (options.live && options.finalAnswerStarted) {
    for (let candidate = blocks.length - 1; candidate >= 0; candidate -= 1) {
      if (blocks[candidate]?.type === 'text') {
        index = candidate
        break
      }
    }
  }

  const active = index >= 0
  const target = active
    ? (blocks[index] as Extract<ContentBlock, { type: 'text' }>).text
    : ''
  const key = `${options.runId ?? 'current'}:${index}`
  const [cursor, setCursor] = useState<Cursor>({ key: '', shown: '' })
  const cursorRef = useRef(cursor)
  cursorRef.current = cursor
  const latest = useRef({ active, index, key, target })
  latest.current = { active, index, key, target }
  const frame = useRef<number | null>(null)
  const tickRef = useRef<FrameRequestCallback>(() => undefined)

  tickRef.current = () => {
    frame.current = null
    const current = latest.current
    if (!current.active) return

    const previous = cursorRef.current
    const prefix = previous.key === current.key && current.target.startsWith(previous.shown)
      ? previous.shown
      : ''
    const targetPoints = codePoints(current.target)
    const shownPoints = codePoints(prefix)
    const pending = targetPoints.length - shownPoints.length
    if (pending <= 0) return

    const ordinaryStep = Math.min(
      MAX_CODE_POINTS,
      Math.max(MIN_CODE_POINTS, Math.ceil(pending / 12)),
    )
    // Ingen «spring til target - N»-regel. Den var årsagen: landede hele
    // svaret på én gang, satte den `end` til `target - 300`, og 90 % af
    // teksten kom i FØRSTE frame (Bjørn 17/10-2026: «slutbeskeden bliver
    // dumpet i stedet for streamet»). Nu bestemmer efterslæbet kun hvor
    // stort trinnet må være, aldrig hvor vi lander — så alt kommer i trin.
    const end = Math.min(targetPoints.length, shownPoints.length + ordinaryStep)
    const next = { key: current.key, shown: targetPoints.slice(0, end).join('') }
    cursorRef.current = next
    setCursor(next)

    if (end < targetPoints.length) {
      frame.current = requestAnimationFrame((time) => tickRef.current(time))
    }
  }

  useEffect(() => {
    if (!active || !target) return
    const previous = cursorRef.current
    const shown = previous.key === key && target.startsWith(previous.shown) ? previous.shown : ''
    if (shown !== target && frame.current === null) {
      frame.current = requestAnimationFrame((time) => tickRef.current(time))
    }
  }, [active, key, target])

  useEffect(() => () => {
    if (frame.current !== null) cancelAnimationFrame(frame.current)
    frame.current = null
  }, [])

  if (!active) return blocks as ContentBlock[]
  const shown = cursor.key === key && target.startsWith(cursor.shown) ? cursor.shown : ''
  if (shown === target) return blocks as ContentBlock[]
  return blocks.map((block, blockIndex) => blockIndex === index
    ? { ...block, text: shown } as ContentBlock
    : block)
}
