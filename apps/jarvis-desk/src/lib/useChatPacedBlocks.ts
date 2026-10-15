import { useEffect, useRef, useState } from 'react'
import type { ContentBlock } from './sseProtocol'

const MIN_CODE_POINTS = 5
const MAX_CODE_POINTS = 30
const MAX_BACKLOG_CODE_POINTS = 300

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
    const end = Math.min(
      targetPoints.length,
      Math.max(shownPoints.length + ordinaryStep, targetPoints.length - MAX_BACKLOG_CODE_POINTS),
    )
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
