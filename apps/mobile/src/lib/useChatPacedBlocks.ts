import { useEffect, useRef, useState } from 'react'
import type { ContentBlock } from './sseProtocol'

const BASE_CODE_POINTS_PER_SECOND = 48
const MAX_CODE_POINTS_PER_SECOND = 180
const CATCH_UP_SECONDS = 3
const MAX_CODE_POINTS_PER_FRAME = 6
const MAX_FRAME_DELTA_S = 0.1

export interface ChatPacingOptions {
  live: boolean
  finalAnswerStarted: boolean
  paceAllText?: boolean
  runId?: string | null
}

function codePoints(value: string): string[] { return Array.from(value) }

/** Chat-fladens tidsbaserede Desk-pace, uafhængig af skærmens billedfrekvens. */
export function useChatPacedBlocks(
  blocks: readonly ContentBlock[], options: ChatPacingOptions,
): ContentBlock[] {
  const key = `${options.runId ?? 'current'}:chat-text`
  const hasText = blocks.some((block) => block?.type === 'text' && block.text)
  const paceNow = options.paceAllText || options.finalAnswerStarted
  // En tekst der faktisk begyndte at pace live, skal rulle færdig selv hvis
  // final_answer_start udebliver og live bliver falsk ved message_stop.
  const liveRef = useRef('')
  if (options.live && paceNow && hasText) liveRef.current = key
  const wasLive = liveRef.current === key
  const textIndices = paceNow || wasLive
    ? blocks.flatMap((block, index) => block?.type === 'text' ? [index] : [])
    : []
  const target = textIndices.map((index) =>
    (blocks[index] as Extract<ContentBlock, { type: 'text' }>).text).join('')
  const [cursor, setCursor] = useState({ key: '', shown: '' })
  const cursorRef = useRef(cursor)
  cursorRef.current = cursor
  const active = textIndices.length > 0 && target.length > 0
    && (options.live || wasLive)
  const latest = useRef({ active, key, target })
  latest.current = { active, key, target }
  const frame = useRef<number | null>(null)
  const last = useRef(0)
  const credit = useRef(0)
  const lastKey = useRef('')
  if (lastKey.current !== key) {
    lastKey.current = key
    last.current = 0
    credit.current = 0
  }
  const tickRef = useRef<FrameRequestCallback>(() => undefined)

  tickRef.current = (now: number) => {
    frame.current = null
    const current = latest.current
    if (!current.active) return
    const previous = cursorRef.current
    const prefix = previous.key === current.key && current.target.startsWith(previous.shown)
      ? previous.shown : ''
    const targetPoints = codePoints(current.target)
    const shownPoints = codePoints(prefix)
    const pending = targetPoints.length - shownPoints.length
    if (pending <= 0) return
    const dt = last.current > 0
      ? Math.min(MAX_FRAME_DELTA_S, Math.max(0.004, (now - last.current) / 1000))
      : 1 / 60
    last.current = now
    const rate = Math.min(MAX_CODE_POINTS_PER_SECOND,
      Math.max(BASE_CODE_POINTS_PER_SECOND, pending / CATCH_UP_SECONDS))
    credit.current = Math.min(MAX_CODE_POINTS_PER_FRAME, credit.current + rate * dt)
    const step = Math.min(MAX_CODE_POINTS_PER_FRAME, Math.floor(credit.current))
    if (step <= 0) {
      frame.current = requestAnimationFrame((time) => tickRef.current(time))
      return
    }
    credit.current -= step
    const end = Math.min(targetPoints.length, shownPoints.length + step)
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
  let remaining = codePoints(shown).length
  return blocks.map((block) => {
    if (block?.type !== 'text') return block
    const points = codePoints(block.text)
    const count = Math.min(remaining, points.length)
    remaining -= count
    return { ...block, text: points.slice(0, count).join('') } as ContentBlock
  })
}
