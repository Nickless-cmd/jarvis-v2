import { useEffect, useRef, useState } from 'react'
import type { ContentBlock } from './sseProtocol'
import { naesteRate, PACE_GULV, PACE_ANKOMST_VINDUE_S } from './paceRate'

/** Læsbar grundhastighed. Et svar der lander i ét hug må ikke blinke frem. */
const BASE_CODE_POINTS_PER_SECOND = PACE_GULV
/** Hårdt loft pr. frame — men det er et GULV for hvor lille et trin må være,
 *  ikke et tag: den effektive grænse er `rate × MAX_FRAME_DELTA_S`. Uden det
 *  ville 6 tegn/frame ved 60 fps klippe kurven ved 360 tegn/s og gøre den
 *  adaptive rate uhåndhævet. */
const MAX_CODE_POINTS_PER_FRAME = 6
/** Længste frame-afstand vi regner med. En lang pause må ikke give et spring. */
const MAX_FRAME_DELTA_S = 0.1

export interface ChatPacingOptions {
  live: boolean
  finalAnswerStarted: boolean
  paceAllText?: boolean
  runId?: string | null
}

function codePoints(value: string): string[] { return Array.from(value) }

/**
 * Chat-fladens pace.
 *
 * ## Det faste hastighedsloft er VÆK (18/11-2026)
 *
 * Her stod `Math.min(180, pending / 3)` med `CATCH_UP_SECONDS = 3`. Det er
 * ordret det loft desk fjernede 29/10-2026, efter at have målt at 2000 tegn
 * tog 15,07 s at rulle ud mens serveren havde sendt alt på under et sekund.
 * Loftet var sat for at undgå et hængevindue — det ramte rigtigt, men det
 * ramte ikke problemet: skrev kilden hurtigere end 180 tegn/s, voksede
 * efterslæbet gennem HELE svaret, og pacen indhentede aldrig.
 *
 * Hastigheden bor nu i `paceRate.ts` og følger ANKOMSTEN, justeret mod
 * efterslæbet. Den kan ikke komme bagud, og derfor er der intet vindue at
 * skjule. MÅLT 18/11-2026 med den gamle regel: 5000 tegn tog 6,53 s selv om
 * alt allerede var ankommet.
 *
 * ## Hvorfor hastigheden er tidsbaseret
 *
 * Et loft på «N kodepunkter pr. frame» er en hastighed der afhænger af
 * skærmens opdateringsfrekvens. Nu måles der i kodepunkter pr. SEKUND, og
 * efterslæbet fordeles over `PACE_CATCH_UP_SECONDS` i stedet for at blive
 * sprunget over.
 */
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
  // Ankomstmålingen: hvor mange kodepunkter kom der siden sidste måling, og
  // hvad er den glattede rate. `maal`/`tid` er den forrige måling —
  // forskellen ER ankomsthastigheden, og `rate` bærer historikken ind i
  // `naesteRate`, så ét stort delta ikke kaster kurven.
  const ankomst = useRef({ maal: 0, tid: 0, rate: BASE_CODE_POINTS_PER_SECOND })
  const lastKey = useRef('')
  if (lastKey.current !== key) {
    lastKey.current = key
    last.current = 0
    credit.current = 0
    ankomst.current = { maal: 0, tid: 0, rate: BASE_CODE_POINTS_PER_SECOND }
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

    // Ankomsten måles over et VINDUE, ikke pr. frame: en chunk på 100 tegn der
    // lander i én 16,7 ms-frame ville ellers blive målt som 6000 tegn/s, og
    // EMA'en ville løfte raten til 643 tegn/s hvor den blev stående.
    const a = ankomst.current
    const vokset = targetPoints.length - a.maal
    const dtAnkomst = a.tid > 0 ? (now - a.tid) / 1000 : 0
    const vindueUde = dtAnkomst >= PACE_ANKOMST_VINDUE_S
    const maaltAnkomst = vokset > 0 && vindueUde ? vokset / dtAnkomst : null
    if (vindueUde || a.tid === 0) {
      // Vinduet starter forfra fra NU — også når intet nyt landede, så et
      // dødt vindue ikke akkumuleres ind i det næste.
      a.maal = targetPoints.length
      a.tid = now
    }
    const rate = naesteRate({ pending, forrigeRate: a.rate, ankomst: maaltAnkomst, dt })
    a.rate = rate

    // Bevar brøkdelen mellem frames. `ceil` eller et fast minimum pr. frame
    // gør ellers 48 tegn/s til mindst 60 tegn/s på en 60 Hz-skærm. Loftet
    // FØLGER raten — et fast 6 ville klippe kurven ved 360 tegn/s.
    const maksPrFrame = Math.max(
      MAX_CODE_POINTS_PER_FRAME,
      Math.ceil(rate * MAX_FRAME_DELTA_S),
    )
    credit.current = Math.min(maksPrFrame, credit.current + rate * dt)
    const step = Math.min(maksPrFrame, Math.floor(credit.current))
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
