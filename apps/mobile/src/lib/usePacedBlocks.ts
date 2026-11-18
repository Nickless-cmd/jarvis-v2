import { useEffect, useRef, useState } from 'react'
import type { ContentBlock } from './sseProtocol'
import { naesteRate, PACE_GULV } from './paceRate'

const TICK_MS = 33
const MIN_CHARS = 5
/** Den hårde 20/10-kontrakt: et svar der lander i ÉT hug må accelerere,
 *  aldrig springe. Gælder derfor kun når tick'et faktisk ER et hop — se
 *  `erHop` i tick-løkken. Ved jævn ankomst er grænsen `delta` i stedet. */
const MAX_CHARS = 28
const SHORT_TEXT = 32

/** Et HOP = mere end denne andel af det ventende indhold landede i ÉT tick. */
const HOP_ANDEL = 0.5

/**
 * Code-fladens pace.
 *
 * ## Hvorfor den ikke er `step = min(28, …)` længere
 *
 * Den gamle regel ramte loftet på 28 tegn pr. 33 ms-tick = **848 tegn/s** og
 * blev der. MÅLT 18/11-2026 med den ægte kurve: 2000 tegn tog **3,00 s** og
 * 5000 tegn **6,53 s**, selv når alt allerede var ankommet. Kurven var lineær,
 * og det er beviset: den var KLIPPET, ikke indhentende. Det er præcis den
 * klage desk løste 29/10, men som mobilen aldrig blev koblet på.
 *
 * Nu er reglen den samme som desks: grundtempoet er et GULV, ankomsten
 * glattes, og indhentningskravet (`pending / 2 s`) er en NEDRE grænse der gør
 * at pacen ikke kan komme bagud. `MAX_CHARS` er derfor ikke længere et loft
 * over kurven — kun en størrelse på det tidsrum ét tick dækker, og kun når
 * teksten landede i et hop.
 */
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

  // Ankomstmålingen: hvor mange tegn kom der ind siden sidste tick? Det er
  // kilden, og det er den raten skal følge. `null` = intet nyt delta, så
  // målingen står stille — et færdigankommet svar må ikke nulstille raten.
  const rateRef = useRef(PACE_GULV)
  const forrigeLaengde = useRef<number | null>(null)

  // Uden denne nulstilling starter et NYT svar i fuld hastighed:
  // `forrigeLaengde` stod tilbage fra det forrige svar, så første tick målte
  // hele forskellen som «ankomst» — et hop der aldrig skete. `key` er
  // generationen og skifter præcis når en ny stream begynder.
  const maaltForKey = useRef<string | null>(null)
  if (maaltForKey.current !== key) {
    maaltForKey.current = key
    forrigeLaengde.current = null
    rateRef.current = PACE_GULV
  }

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

        const laengde = current.target.length
        const foer = forrigeLaengde.current
        forrigeLaengde.current = laengde
        const delta = foer === null ? laengde : Math.max(0, laengde - foer)
        const ankomst = foer === null ? null : (delta * 1000) / TICK_MS

        // Er dette tick et HOP? Tre tilfælde, og kun det sidste lemper loftet:
        //   · FØRSTE tick efter et nyt svar: vi ved ikke om teksten kom jævnt
        //     eller dumpede, så vi vælger det sikre — loftet.
        //   · `delta === 0`: kilden er stoppet, men efterslæbet ligger der
        //     stadig, og det blev skabt af et hop.
        //   · `delta >= pending * HOP_ANDEL`: mere end halvdelen af
        //     efterslæbet landede i dette ene tick — det ER et hop.
        const erHop = foer === null || delta === 0 || delta >= pending * HOP_ANDEL

        rateRef.current = naesteRate({
          pending,
          forrigeRate: rateRef.current,
          ankomst,
          // MÅLT 18/11-2026: desks code-hook giver IKKE `dt` her, så
          // tilbagefaldet regnes med standarden 1/60. Gav jeg tickets rette
          // 33 ms, blev tilbagefaldet dobbelt så hurtigt og mobilen målte
          // 5,61 s mod desks 3,20 s ved 2000 tegn — med identisk kode.
          // Paritet kræver samme form, ikke samme intention.
          dt: 1 / 60,
        })

        // Ved jævn ankomst må visningen aldrig vise mere end kilden lige
        // leverede i dette tick — så er et spring strukturelt umuligt, uanset
        // hvor stort efterslæbet er.
        const prTick = (rateRef.current * TICK_MS) / 1000
        const loft = erHop ? MAX_CHARS : Math.max(MAX_CHARS, delta)
        const step = Math.max(MIN_CHARS, Math.min(loft, Math.ceil(prTick)))

        let end = Math.min(current.target.length, shown.length + step)
        // Kløv aldrig et surrogate-par: en halv emoji er en ødelagt glyph.
        const code = current.target.charCodeAt(end - 1)
        if (end < current.target.length && code >= 0xD800 && code <= 0xDBFF) end += 1
        return { key: current.key, shown: current.target.slice(0, end) }
      })
    }, TICK_MS)
    return () => clearInterval(timer)
  }, [active])

  if (!active) return blocks
  if (target.length <= SHORT_TEXT) return blocks
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
