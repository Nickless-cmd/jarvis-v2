import type { ContentBlock } from './sseProtocol'
import { describeTool } from './toolSummary'
import { prikker } from './prikSekvens'
import { tankeFragment } from './tankeFragment'

/**
 * Hvad linjen lige over skrivefeltet siger lige nu.
 *
 * ## Hvorfor den ikke bare viser den sidste tanke
 *
 * Bjørn 12/9-2026: linjen «ligner noget der staller under en lang kommando».
 * Den viste den seneste tanke — og under en kommando der kører i fem minutter
 * er den seneste tanke fem minutter gammel og står bomstille. Skærmen sagde
 * altså «han tænker» mens han i virkeligheden ventede på en `sleep 270`.
 *
 * ## Hvorfor rækkefølgen afgør det, ikke tidsstempler
 *
 * Blokkene kommer i den rækkefølge de skete. Den SIDSTE blok er derfor hvad
 * han er i gang med nu, og det er hele beslutningen:
 *
 * - sidste blok er et værktøj der kører  → vis værktøjets metadata
 * - sidste blok er en tanke              → vis tankestrømmen igen
 * - sidste blok er et FÆRDIGT værktøj    → «Arbejder», for han er på vej
 *                                          tilbage til modellen og har endnu
 *                                          ikke sagt noget nyt
 *
 * Et tidsstempel ville sige det samme og kræve et ur; rækkefølgen ligger der
 * allerede.
 */
export function arbejdsLinje(blocks: ContentBlock[] | null, trin: number): string {
  const sidste = sidsteRelevante(blocks ?? [])
  if (!sidste) return `Tænker${prikker(trin)}`
  if (sidste.type === 'tool_use') {
    if (sidste.status === 'running' || sidste.foreloebig) {
      // Værktøjets egen metadata — «Kører kommando: sleep», «Læser fil: x».
      return describeTool(sidste.name, argTekst(sidste.input), true)
    }
    // Værktøjet er færdigt, men modellen har ikke sagt noget endnu.
    return `Arbejder${prikker(trin)}`
  }
  const fragment = tankeFragment(sidste.thinking)
  return fragment || `Tænker${prikker(trin)}`
}

/**
 * Den sidste blok der siger noget om hvad han LAVER.
 *
 * Tekst-blokke springes over med vilje: svaret står allerede i tråden, og en
 * linje der gentager det sidste stykke svar fortæller intet nyt om arbejdet.
 */
function sidsteRelevante(blocks: ContentBlock[]) {
  for (let i = blocks.length - 1; i >= 0; i--) {
    const b = blocks[i]
    if (!b) continue
    if (b.type === 'tool_use') return b
    if (b.type === 'thinking' && b.thinking.trim()) return b
  }
  return null
}

function argTekst(input: unknown): string {
  if (typeof input === 'string') return input
  try {
    return JSON.stringify(input ?? {})
  } catch {
    return '{}'
  }
}
