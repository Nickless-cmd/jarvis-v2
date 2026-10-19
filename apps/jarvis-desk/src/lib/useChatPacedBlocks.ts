import { useEffect, useRef, useState } from 'react'
import type { ContentBlock } from './sseProtocol'

/** Læsbar grundhastighed. Et svar der lander i ét hug må ikke blinke frem. */
const BASE_CODE_POINTS_PER_SECOND = 48
/** Selv en stor replay-backlog må ikke forvandle strømmen til et dump. */
const MAX_CODE_POINTS_PER_SECOND = 72
/** Hele efterslæbet forsøges fordelt over så mange sekunder, men det hårde
 *  hastighedsloft vinder altid. En hurtig server-replay må gerne skabe lidt
 *  forsinkelse; den må ikke gøre teksten ulæseligt hurtig. */
const CATCH_UP_SECONDS = 12
/** Hårdt loft pr. frame. En tabt frame må ikke blive et spring. */
const MAX_CODE_POINTS_PER_FRAME = 2
/** Længste frame-afstand vi regner med. En lang pause må ikke give et spring. */
const MAX_FRAME_DELTA_S = 0.1

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

/**
 * Paces only the newest final text block; every non-text block stays immediate.
 *
 * ## Hvorfor pacingen ikke må slippe ved `message_stop`
 *
 * Første udgave krævede `live` for at fortsætte. Men `live` bliver falsk i det
 * øjeblik turen slutter, og så faldt resten af svaret ud i ÉN tegning — det er
 * «slutbeskeden bliver dumpet» (Bjørn 17/10-2026). Et svar der er ved at rulle
 * færdig skal rulle færdig; strømmens slutning er ikke en grund til at kaste
 * det sidste op på skærmen.
 *
 * Undtagelsen er en PERSISTERET besked, der monteres efter turen. Den blev
 * ikke streamet for øjnene af nogen og skal vise hele svaret straks — derfor
 * fortsætter vi kun hvis blokken faktisk blev set live i denne mount.
 *
 * ## Hvorfor hastigheden er tidsbaseret
 *
 * Et loft på «N kodepunkter pr. frame» er en hastighed der afhænger af
 * skærmens opdateringsfrekvens, og ved 60 fps betød 60/frame 3.600 tegn i
 * sekundet: hele svaret på under et sekund, hvilket læses som et dump. Nu
 * måles der i kodepunkter pr. SEKUND, og efterslæbet fordeles over
 * `CATCH_UP_SECONDS` i stedet for at blive sprunget over.
 */
export function useChatPacedBlocks(
  blocks: readonly ContentBlock[],
  options: ChatPacingOptions,
): ContentBlock[] {
  let index = -1
  if (options.finalAnswerStarted) {
    for (let candidate = blocks.length - 1; candidate >= 0; candidate -= 1) {
      if (blocks[candidate]?.type === 'text') {
        index = candidate
        break
      }
    }
  }

  const target = index >= 0
    ? (blocks[index] as Extract<ContentBlock, { type: 'text' }>).text
    : ''
  const key = `${options.runId ?? 'current'}:${index}`
  const [cursor, setCursor] = useState<Cursor>({ key: '', shown: '' })
  const cursorRef = useRef(cursor)
  cursorRef.current = cursor

  // Blev denne blok set LIVE? Kun da må pacingen fortsætte efter `message_stop`.
  const liveRef = useRef('')
  if (options.live && index >= 0) liveRef.current = key
  const harVaeretLive = liveRef.current === key

  const active = index >= 0 && target.length > 0 && (options.live || harVaeretLive)

  const latest = useRef({ active, index, key, target })
  latest.current = { active, index, key, target }
  const frame = useRef<number | null>(null)
  const sidst = useRef(0)
  const kredit = useRef(0)
  const sidsteKey = useRef('')
  if (sidsteKey.current !== key) {
    sidsteKey.current = key
    sidst.current = 0
    kredit.current = 0
  }
  const tickRef = useRef<FrameRequestCallback>(() => undefined)

  tickRef.current = (nu: number) => {
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

    // Sekunder siden sidste frame — grundlaget for et jævnt trin uanset fps.
    const dt = sidst.current > 0
      ? Math.min(MAX_FRAME_DELTA_S, Math.max(0.004, (nu - sidst.current) / 1000))
      : 1 / 60
    sidst.current = nu

    // Efterslæbet bestemmer hvor STORT trinnet må være — aldrig hvor vi lander.
    const rate = Math.min(
      MAX_CODE_POINTS_PER_SECOND,
      Math.max(BASE_CODE_POINTS_PER_SECOND, pending / CATCH_UP_SECONDS),
    )
    // Bevar brøkdelen mellem frames. `ceil` eller et minimum pr. frame gør
    // ellers 48 tegn/s til mindst 60 tegn/s på en 60 Hz-skærm og endnu mere
    // på hurtigere paneler. Kreditten giver samme rolige tempo uanset fps.
    kredit.current = Math.min(
      MAX_CODE_POINTS_PER_FRAME,
      kredit.current + rate * dt,
    )
    const step = Math.min(MAX_CODE_POINTS_PER_FRAME, Math.floor(kredit.current))
    if (step <= 0) {
      frame.current = requestAnimationFrame((time) => tickRef.current(time))
      return
    }
    kredit.current -= step
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
  return blocks.map((block, blockIndex) => blockIndex === index
    ? { ...block, text: shown } as ContentBlock
    : block)
}
