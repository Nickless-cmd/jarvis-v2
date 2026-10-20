import { useEffect, useRef, useState } from 'react'
import type { ContentBlock } from './sseProtocol'

/** Læsbar grundhastighed. Et svar der lander i ét hug må ikke blinke frem. */
const BASE_CODE_POINTS_PER_SECOND = 48
/** Selv en stor replay-backlog må ikke forvandle strømmen til et dump.
 *
 *  20/10-2026 (Bjørn): «synket mellem den ægte stream og pacen [skal] ikk
 *  være så stort». Loftet var 72, hvilket betød at et svar på 1000 tegn tog
 *  18,8 s at rulle færdigt — længe efter serveren havde leveret alt, så
 *  skærmen og sandheden var ude af trit i hele det vindue. Målt kurve ved
 *  1000 tegn efterslæb: 72 → 18,8 s, 180 → 9,5 s. Korte svar (100 tegn) er
 *  UÆNDREDE, fordi de aldrig når loftet — grundtempoet er stadig 48. */
const MAX_CODE_POINTS_PER_SECOND = 180
/** Hele efterslæbet forsøges fordelt over så mange sekunder, men det hårde
 *  hastighedsloft vinder altid. 12 s betød at et efterslæb på 300 tegn blev
 *  fordelt ud over 6,2 s selv om der var plads til at gøre det hurtigere.
 *  3 s gør kontrakten enkel: pacen indhenter et efterslæb på op til ~540 tegn
 *  på cirka tre sekunder, og ligger derfor aldrig langt bagefter serveren. */
const CATCH_UP_SECONDS = 3
/** Hårdt loft pr. frame. En tabt frame må ikke blive et spring.
 *
 *  Hævet fra 2 til 6 sammen med hastighedsloftet: ved 60 fps klippede et loft
 *  på 2 kurven ved 120 tegn/s, så `MAX_CODE_POINTS_PER_SECOND` ikke kunne
 *  slå igennem uanset hvad den blev sat til. 6 × 60 = 360 tegn/s er over
 *  loftet og derfor ikke længere den bindende grænse. */
const MAX_CODE_POINTS_PER_FRAME = 6
/** Længste frame-afstand vi regner med. En lang pause må ikke give et spring. */
const MAX_FRAME_DELTA_S = 0.1

export interface ChatPacingOptions {
  live: boolean
  finalAnswerStarted: boolean
  /** Pace også levende synteser før serveren kender slutsvarsgrænsen. */
  paceAllText?: boolean
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
 * Paces all final text blocks as one continuous stream; every non-text block
 * stays immediate.
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
  const key = `${options.runId ?? 'current'}:chat-text`
  const harTekst = blocks.some((block) => block?.type === 'text' && block.text)
  const paceNu = options.paceAllText || options.finalAnswerStarted

  // Blev denne tekst faktisk PACET live? — ikke «var komponenten live?».
  //
  // Målt 20/10-2026 (Bjørn: «det rå svar vises over det pacede svar»): `active`
  // krævede `textIndices.length > 0`, og den var afledt af `finalAnswerStarted`.
  // Et run hvor fold-signalet aldrig blev sat faldt derfor tilbage til
  // `return blocks` i det øjeblik `streaming` blev falsk — hele svaret i ÉN
  // frame, oven på den pacede linje der stadig rullede. Samme familie som
  // tom-tekstkøen i SSE-relæet: et signal der kan udeblive må ikke styre om
  // noget allerede synligt bliver revet væk.
  const liveRef = useRef('')
  if (options.live && paceNu && harTekst) liveRef.current = key
  const harVaeretLive = liveRef.current === key

  const paceTekst = paceNu || harVaeretLive
  const textIndices = paceTekst
    ? blocks.flatMap((block, index) => block?.type === 'text' ? [index] : [])
    : []
  // Serveren kan dele ét markdown-svar over flere content blocks. Den gamle
  // kode pacede kun den SIDSTE blok; alt før den blev derfor dumpet ind, og
  // kun de sidste linjer så streamede ud. Én samlet målstreng giver ét ur og
  // én læsekurve hen over samtlige tekstblokke.
  const target = textIndices.map((index) =>
    (blocks[index] as Extract<ContentBlock, { type: 'text' }>).text).join('')
  const [cursor, setCursor] = useState<Cursor>({ key: '', shown: '' })
  const cursorRef = useRef(cursor)
  cursorRef.current = cursor

  const active = textIndices.length > 0 && target.length > 0 && (options.live || harVaeretLive)

  const latest = useRef({ active, key, target })
  latest.current = { active, key, target }
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
  let resterende = codePoints(shown).length
  return blocks.map((block) => {
    if (block?.type !== 'text') return block
    const punkter = codePoints(block.text)
    const antal = Math.min(resterende, punkter.length)
    resterende -= antal
    return { ...block, text: punkter.slice(0, antal).join('') } as ContentBlock
  })
}
