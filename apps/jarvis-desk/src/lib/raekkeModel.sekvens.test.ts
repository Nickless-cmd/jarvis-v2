import { describe, it, expect } from 'vitest'
import { opdel } from './raekkeModel'
import type { ContentBlock } from './sseProtocol'

/**
 * Bjørns sekvens, ordret (27/11-2026):
 *
 *     runde → syntese → fold → slutbesked → runde → syntese
 *
 * Den er ikke en abstraktion. Det er den form en rigtig tur har, og hvert
 * led har sin egen ejer:
 *
 *   runde 1     → arbejde (folden)
 *   syntese 1   → mellemsvar i arbejde (folden)
 *   fold        → finalAnswerStarted bliver sand
 *   slutbesked  → svar
 *   runde 2     → svar, tegnet af `Arbejdsrunde` (efterFold)
 *   syntese 2   → svar, efter runden
 *
 * ## Hvorfor den skal maales som en HEL sekvens
 *
 * `opdel` kaldes forfra ved hver render, og dens to flag ændrer sig MIDT i
 * turen: `underArbejde` falder til falsk i det øjeblik foldet sker. En blok
 * der lå i arbejde kan derfor skifte side uden at nogen har rørt den — og det
 * er usynligt i en test der kun maaler én fase.
 */

const kald = (navn: string, id: string, status: 'running' | 'done' = 'done'): ContentBlock => ({
  type: 'tool_use', id, name: navn,
  input: { command: 'git status' },
  status,
  ...(status === 'done' ? { result: 'ok' } : {}),
})

const syntese = (t: string): ContentBlock => ({ type: 'text', text: t })
const slutbesked = (t: string): ContentBlock => ({ type: 'text', text: t, phase: 'final_answer' })

/** Sekvensen som den ser ud FØR foldet: kun de tre første led er landet. */
const foerFold: ContentBlock[] = [kald('bash', 'b1'), syntese('Lad mig se på filen.')]

/** Og som den ser ud når hele turen er landet. */
const hele: ContentBlock[] = [
  ...foerFold,
  slutbesked('Sådan ser det ud.'),
  kald('remember_this', 'b2'),
  syntese('Gemt.'),
]

const erIArbejde = (liste: readonly unknown[], blok: unknown) =>
  liste.some((e) => {
    const el = e as { slags?: string; blok?: unknown; tekst?: string }
    return el.blok === blok || (el.slags === 'mellemsvar' && el.tekst === (blok as ContentBlock & { text?: string }).text)
  })

describe('sekvensen runde → syntese → fold → slutbesked → runde → syntese', () => {
  it('FØR foldet: runden og dens syntese ligger begge i arbejdet', () => {
    const { arbejde, svar } = opdel(foerFold, true, false)

    expect(erIArbejde(arbejde, foerFold[0])).toBe(true)
    expect(arbejde.some((e) => e.slags === 'mellemsvar' && e.tekst === 'Lad mig se på filen.')).toBe(true)
    expect(svar).toHaveLength(0)
  })

  it('EFTER foldet: syntesen bliver i folden — den flytter sig ikke', () => {
    // DETTE er den maaling der afgør om sekvensen holder. `underArbejde`
    // skifter til falsk når foldet sker; hvis syntesen så falder i `svar`,
    // er den teleporteret ud af folden mens brugeren så på den.
    const { arbejde, svar } = opdel(hele, false, true)

    const synteseErIArbejde = arbejde.some(
      (e) => e.slags === 'mellemsvar' && e.tekst === 'Lad mig se på filen.',
    )
    const synteseErISvar = svar.some(
      (b) => b.type === 'text' && b.text === 'Lad mig se på filen.',
    )

    expect(synteseErIArbejde, 'syntesen før foldet hører til i folden').toBe(true)
    expect(synteseErISvar, 'den må ikke også stå i svaret').toBe(false)
  })

  it('EFTER foldet: runden efter svaret ligger i svar, ikke i arbejde', () => {
    const { arbejde, svar } = opdel(hele, false, true)

    expect(erIArbejde(arbejde, hele[3])).toBe(false)
    expect(svar).toContain(hele[3])
  })

  it('EFTER foldet: svarSektionerne bevarer rækkefølgen — tekst, runde, tekst', () => {
    const { svarSektioner } = opdel(hele, false, true)

    const form = svarSektioner.map((s) => s.slags)
    expect(form).toEqual(['blokke', 'runde', 'blokke'])

    // Den første blokke-sektion er slutbeskeden — IKKE den flyttede syntese.
    const foerste = svarSektioner[0]!
    expect(foerste.slags).toBe('blokke')
    if (foerste.slags === 'blokke') {
      expect(foerste.blokke.some((b) => b.type === 'text' && b.text === 'Sådan ser det ud.')).toBe(true)
      expect(foerste.blokke.some((b) => b.type === 'text' && b.text === 'Lad mig se på filen.')).toBe(false)
    }

    // Runden i midten er den sene runde.
    const midt = svarSektioner[1]!
    expect(midt.slags).toBe('runde')
    if (midt.slags === 'runde') {
      expect(midt.elementer.some((e) => e.slags === 'blok' && e.blok === hele[3])).toBe(true)
    }

    // Og den sidste er syntesen EFTER runden.
    const sidste = svarSektioner[2]!
    expect(sidste.slags).toBe('blokke')
    if (sidste.slags === 'blokke') {
      expect(sidste.blokke.some((b) => b.type === 'text' && b.text === 'Gemt.')).toBe(true)
    }
  })
})
