import { useEffect, useRef, useState } from 'react'
import type { ContentBlock } from './sseProtocol'

const TICK_MS = 33
const MIN_CHARS = 5
const MAX_CHARS = 28
const SHORT_TEXT = 32
/** Hvor langt visningen må sakke bagud, før vi springer frem til grænsen.
 *  Loftet på MAX_CHARS pr. tick kan ikke følge en hurtigere kilde alene, og
 *  uden en grænse hober forskellen sig op for evigt — målt 10/10-2026:
 *  679 tegns efterslæb efter 90 frames ved 25 tegn pr. frame. */
const BACKLOG_MAX = 330

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

  useEffect(() => {
    if (!active) return
    const timer = setInterval(() => {
      const current = latest.current
      if (!current.active) return
      setCursor((previous) => {
        const shown = current.target.startsWith(previous.shown) ? previous.shown : ''
        const pending = current.target.length - shown.length
        if (pending <= 0) return previous
        // Jævn kadence: små trin så længe vi kan følge kilden.
        const step = Math.min(MAX_CHARS, Math.max(MIN_CHARS, Math.ceil(pending / 12)))
        // …og grænsen der gør at vi ALTID indhenter: er vi mere end
        // BACKLOG_MAX bagud, springer vi frem til grænsen i stedet.
        let end = Math.min(current.target.length,
          Math.max(shown.length + step, current.target.length - BACKLOG_MAX))
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
