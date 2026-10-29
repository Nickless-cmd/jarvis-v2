import { useEffect, useRef, useState } from 'react'
import type { ContentBlock } from './sseProtocol'
import { naesteRate, PACE_GULV } from './paceRate'

const TICK_MS = 33
const MIN_CHARS = 5
const MAX_CHARS = 28
const SHORT_TEXT = 32
/** Et HOP = mere end denne andel af det ventende indhold landede i ÉT tick.
 *
 *  ## Hvorfor loftet skal gælde hop og ikke jævn ankomst (29/10-2026)
 *
 *  `MAX_CHARS` blev vedtaget 20/10 efter «glitch bump»: pacen fortsatte et
 *  par sekunder, gik glitch, og så var resten af beskeden der. Det var et
 *  ægte hak — men hakket opstod fordi reglen sprang frem til `target - 330`
 *  uanset hvordan teksten var ankommet.
 *
 *  Loftet beskytter altså mod ÉN ting: at et helt svar lander i én frame og
 *  bliver kastet op. Det beskytter ikke mod noget når kilden selv leverer
 *  jævnt — for der er der intet at skjule, og loftet gør bare at visningen
 *  ikke kan følge kilden.
 *
 *  MÅLT 29/10-2026: `pending / 3 s` kræver 44 tegn/tick ved 4000 tegn, men
 *  loftet klipper til 28. Kurven blev derfor konstant 848 tegn/s — flad,
 *  fordi den var KLIPPET, ikke fordi den indhentede.
 *
 *  Gaten herunder skelner de to: lander en stor andel af efterslæbet i dette
 *  ene tick, er det et hop, og loftet gælder. Kommer teksten jævnt, må
 *  visningen følge raten helt op til `PACE_LOFT`.
 */
const HOP_ANDEL = 0.5
/** Code Mode bruger nu SAMME adaptive regel som chat mode (29/10-2026).
 *
 *  MÅLT med den rigtige hook og et deterministisk ur, FØR ændringen:
 *
 *    2000 tegn → 3,00 s
 *    5000 tegn → 6,53 s
 *    100 tegn  → 0,59 s
 *
 *  Kurven er lineær, og det er beviset: `step = min(28, max(5, ceil(pending/12)))`
 *  rammer loftet på 28 tegn pr. 33 ms-tick = **848 tegn/s** og bliver der.
 *  Er kilden hurtigere, vokser efterslæbet gennem hele svaret — præcis den
 *  klage chat mode fik løst med `paceRate.ts`, men Code Mode blev aldrig
 *  koblet på. Bjørn 29/10-2026: «det køre stadig mærkeligt».
 *
 *  Reglen er nu den samme som i chat-laget: grundtempoet er et GULV, ankomsten
 *  glattes, og indhentningskravet (`pending / 3 s`) sætter den nedre grænse
 *  der gør at pacen ikke kan komme bagud. `MAX_CHARS` er derfor ikke længere
 *  et loft — kun en størrelse på det tidsrum et tick dækker.
 */
/** Der er MED VILJE intet backlog-loft længere (målt 20/10-2026).
 *
 *  Den gamle regel sprang frem til `target - BACKLOG_MAX` når efterslæbet
 *  oversteg 330 tegn. Den blev indført 10/10 fordi `MAX_CHARS` pr. tick ikke
 *  alene kunne følge en hurtigere kilde — men den kurerede symptomet med et
 *  hak: ved fold lander resten af svaret i ét hop, efterslæbet eksploderer,
 *  og reglen kastede op til 330+ tegn ind i ÉN tick (målt +545).
 *
 *  Et pacing-lag må aldrig springe; det må kun accelerere. Accelerationen
 *  ligger i `step`-beregningen nedenfor, som glider fra 5 til 28 tegn pr.
 *  tick — den indhenter 900 tegn på ca. 32 ticks (≈1 s) uden ét eneste hak.
 */

/**
 * Paces Code-fladens tekst.
 *
 * ## Kontrakten er den samme som chat-lagets (rettet 20/10-2026)
 *
 * Bjørn så et «hurtigt svar» der landede oven på pacen — men KUN i det ene
 * miljø. Målt i en probe på denne fil (20/10-2026):
 *
 *   FASE2 efter 5 ticks len=81   (target 249)
 *   FASE3 FOLD (live=false) len=249   ← 168 tegn dumpet i ÉN frame
 *
 * Årsagen var at laget dumpede rå tekst ad to veje, som chat-laget allerede
 * havde fået lukket:
 *
 *  1. `live` bliver falsk ved `message_stop` → `index` blev -1 → `return
 *     blocks`. HELE svaret blev kastet op i samme frame som foldet.
 *  2. Kun den SIDSTE tekstblok blev paced. Deltes svaret over flere blokke,
 *     stod alt før den sidste råt på skærmen — målt: vist 82 af 167 tegn.
 *
 * Begge er nu lukket med samme mønster som `useChatPacedBlocks`: ét samlet
 * mål over ALLE tekstblokke, og en cursor der fortsætter efter `message_stop`
 * hvis blokken faktisk blev set live. En persisteret besked (monteret efter
 * turen, aldrig streamet for øjnene af nogen) vises stadig straks — den skal
 * ikke rulle for nogens skyld.
 *
 * Kurven er UÆNDRET: 33 ms-tick, 5–28 tegn pr. tick. Det er hastigheden Bjørn
 * kender; kun dump-vejene er fjernet.
 */
export function usePacedBlocks(blocks: ContentBlock[], live: boolean): ContentBlock[] {
  const textIndices = blocks.flatMap((block, index) => (block?.type === 'text' ? [index] : []))
  // Serveren kan dele ét markdown-svar over flere content blocks. Én samlet
  // målstreng giver ét ur og én læsekurve hen over samtlige tekstblokke.
  const target = textIndices
    .map((index) => (blocks[index] as Extract<ContentBlock, { type: 'text' }>).text)
    .join('')

  const [cursor, setCursor] = useState<{ key: string; shown: string }>({ key: '', shown: '' })
  const cursorRef = useRef(cursor)
  cursorRef.current = cursor

  // Blev blokken set LIVE? Kun da må pacingen fortsætte efter `message_stop`.
  // En persisteret besked rører aldrig dette flag og vises derfor straks.
  const liveRef = useRef(false)
  if (live && textIndices.length > 0) liveRef.current = true
  const harVaeretLive = liveRef.current

  // Cursoren må ikke genbruges på tværs af to svar. Et NYT svar begynder når
  // `live` går fra falsk til sand igen — det er den eneste kant der betyder
  // «en ny stream starter». Fold-kanten (sand → falsk) er den modsatte vej og
  // må netop IKKE nulstille noget: det var dér teksten blev dumpet.
  const generation = useRef(0)
  const forrigeLive = useRef(live)
  if (forrigeLive.current !== live) {
    forrigeLive.current = live
    if (live) generation.current += 1
  }
  const key = String(generation.current)

  const active = textIndices.length > 0 && target.length > 0 && (live || harVaeretLive)

  const latest = useRef({ active, target, key })
  latest.current = { active, target, key }

  // Ankomstmålingen: hvor mange tegn kom der ind siden sidste tick? Det er
  // kilden, og det er den raten skal følge. `null` = intet nyt delta, så
  // målingen står stille — et færdigankommet svar må ikke nulstille raten
  // midt i udrulningen.
  const rateRef = useRef(PACE_GULV)
  const forrigeLaengde = useRef<number | null>(null)

  // MÅLT 29/10-2026: uden denne nulstilling starter et NYT svar i fuld
  // hastighed. `forrigeLaengde` stod tilbage fra det forrige svar, så det
  // første tick målte `4000 - 3000 = 1000` tegn som «ankomst» — et hop der
  // aldrig skete — og raten sprang til loftet. Målt: 28 tegn i FØRSTE tick
  // i stedet for grundtempoets 5. Det er «det kører stadig mærkeligt»: svaret
  // skvulper ud i stedet for at begynde roligt.
  //
  // `key` er generationen og skifter præcis når en ny stream begynder, så det
  // er den rigtige kant at nulstille på — ikke `active`, som også bliver sand
  // igen efter en fold af SAMME svar.
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
        const shown = current.target.startsWith(previous.shown) ? previous.shown : ''
        const pending = current.target.length - shown.length
        if (pending <= 0) return previous

        // Ankomst siden sidste tick, målt i kodepunkter pr. sekund.
        const laengde = current.target.length
        const foer = forrigeLaengde.current
        forrigeLaengde.current = laengde
        const delta = foer === null ? laengde : Math.max(0, laengde - foer)
        const ankomst = foer === null ? null : (delta * 1000) / TICK_MS

        // Er dette tick et HOP? Tre tilfælde, og kun det sidste lemper loftet:
        //
        //  · FØRSTE tick efter et nyt svar (`foer === null`): vi ved ikke om
        //    teksten kom jævnt eller dumpede, så vi vælger det sikre — loft.
        //  · `delta === 0`: kilden er stoppet, men der ligger stadig et
        //    efterslæb. Det efterslæb blev skabt af et hop, så loftet gælder.
        //    (MÅLT 29/10: uden denne gren slap 78 tegn igennem i ét tick.)
        //  · `delta >= pending * HOP_ANDEL`: mere end halvdelen af efterslæbet
        //    landede i dette ene tick — det ER et hop.
        const erHop = foer === null || delta === 0 || delta >= pending * HOP_ANDEL

        // Samme regel som chat mode: grundtempo er gulv, ankomst glattes,
        // indhentningskravet (pending / 3 s) er den nedre grænse. Uden det
        // sidste ville et svar på 5000 tegn tage 6,5 s — målt.
        rateRef.current = naesteRate({
          pending,
          forrigeRate: rateRef.current,
          ankomst,
        })

        // Ratens tidsrum er ét tick. Gulvet på MIN_CHARS bevarer den rolige
        // kadence på korte svar.
        //
        // Loftet afhænger af HVORDAN teksten kom ind (målt 29/10-2026):
        //
        //  · HOP: `MAX_CHARS` — den hårde 20/10-kontrakt. Et svar der lander
        //    i ét hug må accelerere, aldrig springe.
        //  · JÆVN ANKOMST: `max(MAX_CHARS, delta)`. Visningen må aldrig vise
        //    mere end kilden lige leverede i dette tick — så er et spring
        //    strukturelt umuligt, uanset hvor stort efterslæbet er. Kom der
        //    200 tegn ind, må der vises op til 200; kom der 5, bliver det 28.
        const prTick = (rateRef.current * TICK_MS) / 1000
        const loft = erHop ? MAX_CHARS : Math.max(MAX_CHARS, delta)
        const step = Math.max(MIN_CHARS, Math.min(loft, Math.ceil(prTick)))

        // INGEN spring (målt 20/10-2026). Den gamle regel sprang frem til
        // `target - BACKLOG_MAX` når efterslæbet oversteg 330 tegn. Ved fold
        // lander resten af svaret i ét hop, så efterslæbet eksploderede og
        // reglen kastede op til 330+ tegn ind i ÉN tick — målt +545 tegn.
        // Det er «glitch bump»: Bjørn 20/10-2026, «pacen forsætter lige et
        // sekund eller 2 og går glitch og så er resten af beskeden der».
        // Et pacing-lag må aldrig springe; det må kun accelerere.
        let end = Math.min(current.target.length, shown.length + step)
        // Kløv aldrig et surrogate-par: en halv emoji er en ødelagt glyph.
        const code = current.target.charCodeAt(end - 1)
        if (end < current.target.length && code >= 0xD800 && code <= 0xDBFF) end++
        return { key: current.key, shown: current.target.slice(0, end) }
      })
    }, TICK_MS)
    return () => clearInterval(timer)
  }, [active])

  if (!active) return blocks
  // Et kort svar skal ikke rulle — der er intet at læse hen over.
  if (target.length <= SHORT_TEXT) return blocks

  const shown = cursor.key === key && target.startsWith(cursor.shown) ? cursor.shown : ''
  if (shown === target) return blocks
  let resterende = shown.length
  return blocks.map((block) => {
    if (block?.type !== 'text') return block
    const antal = Math.min(resterende, block.text.length)
    resterende -= antal
    return { ...block, text: block.text.slice(0, antal) } as ContentBlock
  })
}
