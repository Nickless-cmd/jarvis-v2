import { useEffect, useRef, useState } from 'react'
import type { ContentBlock } from './sseProtocol'
import { scanFences, type FenceSpan } from './fenceScanner'
import { naesteRate, PACE_GULV, PACE_ANKOMST_VINDUE_S } from './paceRate'

/** Læsbar grundhastighed. Et svar der lander i ét hug må ikke blinke frem. */
const BASE_CODE_POINTS_PER_SECOND = PACE_GULV
/** 29/10-2026: det faste hastighedsloft er VÆK.
 *
 *  Det hed `MAX_CODE_POINTS_PER_SECOND = 180` og var sat 20/10 for at undgå et
 *  18,8 s hængevindue. Det ramte rigtigt — men det ramte ikke problemet: skrev
 *  modellen hurtigere end 180 tegn/s, voksede efterslæbet gennem HELE svaret,
 *  og pacen indhentede aldrig. Målt: 2000 tegn tog 15,07 s at rulle ud mens
 *  serveren havde sendt alt på under et sekund. Det er den «svaret streames
 *  færdigt inde i hoved» Bjørn beskrev.
 *
 *  Hastigheden bor nu i `paceRate.ts` og følger ANKOMSTEN, justeret mod
 *  efterslæbet — samme model som Codex desktop bruger (målt 29/10-2026). Den
 *  kan ikke komme bagud, og derfor er der intet vindue at skjule. */
/** Hårdt loft pr. frame. En tabt frame må ikke blive et spring.
 *
 *  Loftet er nu et GULV for hvor lille et trin må være, ikke et tag: den
 *  effektive grænse beregnes som `rate × MAX_FRAME_DELTA_S` i tick'et. Uden
 *  det ville 6 tegn/frame ved 60 fps klippe kurven ved 360 tegn/s og dermed
 *  gøre den adaptive rate uhåndhævet — samme fælde som 20/10. */
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

/** Er denne fence en `jarvis-ui`-flade?
 *
 *  `FenceSpan` bærer ikke info-strengen, så den læses fra åbningslinjen.
 *  Uden dette tjek ville ALLE fences (mermaid, kode) blive sprunget over, og
 *  et almindeligt kodeblok-eksempel ville lande i ét hug midt i et svar der
 *  ellers ruller roligt. */
function erFlade(target: string, span: FenceSpan): boolean {
  const slut = target.indexOf('\n', span.start)
  const aabning = target.slice(span.start, slut < 0 ? target.length : slut)
  return aabning.includes('jarvis-ui')
}

/**
 * Hvor skal cursoren lande, hvis næste skridt rammer en `jarvis-ui`-flade?
 *
 * `null` = ingen flade i vejen, rul normalt.
 * `offset` = stå stille: fladen er ikke komplet, og halv JSON må ikke vises.
 * andet = spring hertil (fence-slut), så fladen lander i ét hug.
 *
 * Springet flytter cursoren FREM i den samme streng, så `shown` er stadig et
 * præfiks af `target` — kontrakten hele hooket bygger på.
 */
function fladeSpring(
  target: string,
  offset: number,
  step: number,
  hold: boolean,
): number | null {
  for (const span of scanFences(target)) {
    if (span.end <= offset) continue          // allerede passeret
    if (!erFlade(target, span)) continue      // ikke en flade — rør den ikke
    if (offset >= span.start) {
      // Inde i fladen. Kan kun ske hvis et tidligere spring blev klippet.
      if (span.closed) return span.end
      return hold ? offset : null
    }
    if (offset + step <= span.start) return null   // næste skridt rammer ikke
    // Næste skridt ville lande inde i fladen.
    if (span.closed) return span.end
    return hold ? span.start : null
  }
  return null
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
  // Nøglen er TUREN, ikke runnet (28/10-2026). Kalderen sender en nøgle der
  // er stabil gennem hele turen; et follow-up-run må ikke give en ny nøgle,
  // for så nulstilles cursoren og svaret paces FORFRA. Se `paceNoegle` i
  // `ChatFlowPresentation`. Herunder er reglen derfor simpel: nøglen skifter
  // → teksten er en anden → cursoren starter tom.
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

  const latest = useRef({ active, key, target, hold: options.live })
  latest.current = { active, key, target, hold: options.live }
  const frame = useRef<number | null>(null)
  const sidst = useRef(0)
  const kredit = useRef(0)
  // Ankomstmålingen (29/10-2026): hvor mange kodepunkter kom der siden sidste
  // frame, og hvad er den glattede rate. `maal`/`tid` er den forrige måling —
  // forskellen mellem dem ER ankomsthastigheden, og `rate` bærer historikken
  // ind i `naesteRate`, så ét stort delta ikke kaster kurven.
  const ankomst = useRef({ maal: 0, tid: 0, rate: BASE_CODE_POINTS_PER_SECOND })
  const sidsteKey = useRef('')
  if (sidsteKey.current !== key) {
    sidsteKey.current = key
    sidst.current = 0
    kredit.current = 0
    ankomst.current = { maal: 0, tid: 0, rate: BASE_CODE_POINTS_PER_SECOND }
  }
  const tickRef = useRef<FrameRequestCallback>(() => undefined)

  tickRef.current = (nu: number) => {
    frame.current = null
    const current = latest.current
    if (!current.active) return

    const previous = cursorRef.current
    // Nøglen kan skifte (nyt run) mens teksten fortsætter. Er den viste tekst
    // stadig et præfiks af målet, beholder vi den — ellers ville pacen starte
    // forfra midt i et svar brugeren allerede læser.
    const prefix = previous.key === current.key ? previous.shown : ''
    const targetPoints = codePoints(current.target)
    const shownPoints = codePoints(prefix)
    const pending = targetPoints.length - shownPoints.length
    if (pending <= 0) return

    // Sekunder siden sidste frame — grundlaget for et jævnt trin uanset fps.
    const dt = sidst.current > 0
      ? Math.min(MAX_FRAME_DELTA_S, Math.max(0.004, (nu - sidst.current) / 1000))
      : 1 / 60
    sidst.current = nu

    // ADAPTIV HASTIGHED (29/10-2026). Målt med den gamle, faste grænse:
    // 2000 tegn tog 15,07 s at rulle ud, fordi `Math.min(180, …)` klippede
    // indhentningen og efterslæbet derfor voksede gennem hele svaret.
    // Reglen bor i `paceRate.ts` og følger ankomsten, justeret mod
    // efterslæbet — samme model som Codex desktop (målt 29/10-2026).
    const a = ankomst.current
    // ADAPTIV HASTIGHED (29/10-2026). Målt med den gamle, faste grænse:
    // 2000 tegn tog 15,07 s at rulle ud, fordi `Math.min(180, …)` klippede
    // indhentningen og efterslæbet derfor voksede gennem hele svaret.
    // Reglen bor i `paceRate.ts` og følger ankomsten, justeret mod
    // efterslæbet — samme model som Codex desktop (målt 29/10-2026).
    //
    // 30/10-2026 (Bjørn: «Pacen løber for stærkt»): ankomsten måles nu over
    // et VINDUE, ikke pr. frame. Målt pr. frame blev en SSE-chunk på 100 tegn
    // der lander i én 16,7 ms-frame til 6000 tegn/s — ikke 100 tegn — og
    // EMA'en løftede raten til 643 tegn/s, 13,4x grundtempoet, hvor den blev
    // stående resten af svaret. Se `PACE_ANKOMST_VINDUE_S`.
    const vokset = targetPoints.length - a.maal
    const dtAnkomst = a.tid > 0 ? (nu - a.tid) / 1000 : 0
    const vindueUde = dtAnkomst >= PACE_ANKOMST_VINDUE_S
    const maaltAnkomst = vokset > 0 && vindueUde ? vokset / dtAnkomst : null
    if (vindueUde || a.tid === 0) {
      // Vinduet starter forfra fra NU — også når intet nyt landede, så et
      // dødt vindue ikke akkumuleres ind i det næste.
      a.maal = targetPoints.length
      a.tid = nu
    }
    const rate = naesteRate({ pending, forrigeRate: a.rate, ankomst: maaltAnkomst, dt })
    a.rate = rate
    // Bevar brøkdelen mellem frames. `ceil` eller et minimum pr. frame gør
    // ellers 48 tegn/s til mindst 60 tegn/s på en 60 Hz-skærm og endnu mere
    // på hurtigere paneler. Kreditten giver samme rolige tempo uanset fps.
    //
    // Loftet pr. frame FØLGER raten: et fast 6 ville klippe kurven ved 360
    // tegn/s og gøre den adaptive rate uhåndhævet — samme fælde som 20/10,
    // hvor et frame-loft på 2 gjorde hastighedsloftet virkningsløst.
    const maksPrFrame = Math.max(
      MAX_CODE_POINTS_PER_FRAME,
      Math.ceil(rate * MAX_FRAME_DELTA_S),
    )
    kredit.current = Math.min(maksPrFrame, kredit.current + rate * dt)
    const step = Math.min(maksPrFrame, Math.floor(kredit.current))
    if (step <= 0) {
      frame.current = requestAnimationFrame((time) => tickRef.current(time))
      return
    }
    kredit.current -= step

    // 29/10-2026 (Bjørn): «kode boksen der udvider sig og så blink».
    //
    // Paceren er blind for struktur: den rullede rå JSON ind i en åben fence,
    // og `stabilizeStreamingMarkdown` lukkede fencen midlertidigt, så
    // react-markdown så en LUKKET kodeblok med halv JSON og voksede en
    // kodeboks. Nu springes en komplet flade over i ét spring, og en ukomplet
    // flade holder cursoren stille — så JSON'en aldrig bliver synlig.
    //
    // Springet sker EFTER `step` er beregnet og er derfor ikke bundet af
    // `MAX_CODE_POINTS_PER_FRAME`: et loft pr. frame må ikke gøre et spring
    // umuligt. `prefix.length` er en UTF-16-offset (fence-scanneren regner i
    // UTF-16), mens cursoren tæller kodepunkter — derfor konverteres tilbage.
    const spring = fladeSpring(current.target, prefix.length, step, current.hold)
    if (spring !== null) {
      const springPoints = spring === prefix.length
        ? shownPoints.length
        : codePoints(current.target.slice(0, spring)).length
      if (springPoints <= shownPoints.length) {
        // Fladen er ikke komplet endnu. Kreditten gives tilbage, så
        // akkumulatoren ikke går i baglås mens cursoren venter.
        kredit.current = Math.min(maksPrFrame, kredit.current + step)
        frame.current = requestAnimationFrame((time) => tickRef.current(time))
        return
      }
      const sprunget = { key: current.key, shown: current.target.slice(0, spring) }
      cursorRef.current = sprunget
      setCursor(sprunget)
      if (springPoints < targetPoints.length) {
        frame.current = requestAnimationFrame((time) => tickRef.current(time))
      }
      return
    }

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
    const shown = previous.key === key ? previous.shown : ''
    if (shown !== target && frame.current === null) {
      frame.current = requestAnimationFrame((time) => tickRef.current(time))
    }
  }, [active, key, target])

  useEffect(() => () => {
    if (frame.current !== null) cancelAnimationFrame(frame.current)
    frame.current = null
  }, [])

  if (!active) return blocks as ContentBlock[]
  const shown = cursor.key === key ? cursor.shown : ''
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
