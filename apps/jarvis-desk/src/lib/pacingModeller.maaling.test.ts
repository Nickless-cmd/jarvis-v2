/**
 * MÅLING, ikke en vagt: to måder at få et svar til at lande roligt på.
 *
 * Bjørn 30/10-2026: «Prøv begge først». Baggrunden er at paceren er blevet
 * justeret frem og tilbage (29/10 «for langsom», 30/10 «for stærk»), og at
 * Codex-appens mekanisme er målt til at være en HELT ANDEN: de holder ikke
 * teksten tilbage, de toner hvert segment ind.
 *
 *   A — TIDSLIG (vores): teksten holdes tilbage og slippes i takt.
 *   B — RUMLIG (Codex): hele teksten er i DOM med det samme; hvert segment
 *       får `--fade-delay` og toner ind.
 *
 * Målingen svarer på tre spørgsmål for hver model:
 *
 *   1. Hvor lang tid går der før AL teksten er synlig?
 *   2. Hvor stort er det største spring i synligt indhold mellem to frames?
 *   3. Hvor lang tid er der hvor INGEN ny tekst bliver synlig (død tid)?
 *
 * Punkt 2 er det der afgør om det «skvulper». Punkt 3 er det der afgør om
 * det føles som om der sker noget.
 */
import { describe, expect, it } from 'vitest'
import { naesteRate, PACE_ANKOMST_VINDUE_S, PACE_GULV } from './paceRate'

const FPS = 60
const FRAME_S = 1 / FPS

/** Codex' målte konstanter (læst i deres bundle 30/10-2026). */
const FADE_SEGMENT_DELAY_MS = 24
const FADE_SEGMENT_MAX_DELAY_MS = 800
const FADE_DURATION_MS = 200

interface Resultat {
  sekunderTilAltSynligt: number
  stoersteSpring: number
  laengsteDoedeTidS: number
  frames: number
}

/** A: den ægte pacer, samme tick-loop som `useChatPacedBlocks`. */
function modelA(target: string, ankomstTegnPerS: number): Resultat {
  const targetPoints = Array.from(target)
  const total = targetPoints.length
  let shown = 0
  let rate = PACE_GULV
  let kredit = 0
  let sekunder = 0
  let stoersteSpring = 0
  let sidsteVaekst = 0
  let laengsteDoedeTid = 0
  let frames = 0

  // Ankomsten måles over et vindue, præcis som hooket gør.
  let maal = 0
  let vindueTid = 0

  while (shown < total && sekunder < 60) {
    frames += 1
    sekunder += FRAME_S

    // Hvor meget af target er ankommet på dette tidspunkt?
    const ankommet = Math.min(total, Math.floor(ankomstTegnPerS * sekunder))
    const vokset = ankommet - maal
    const dtAnkomst = vindueTid > 0 ? sekunder - vindueTid : 0
    const vindueUde = dtAnkomst >= PACE_ANKOMST_VINDUE_S
    const maaltAnkomst = vokset > 0 && vindueUde ? vokset / dtAnkomst : null
    if (vindueUde) {
      maal = ankommet
      vindueTid = sekunder
    }

    const pending = ankommet - shown
    if (pending <= 0) {
      if (sekunder - sidsteVaekst > laengsteDoedeTid) {
        laengsteDoedeTid = sekunder - sidsteVaekst
      }
      continue
    }

    rate = naesteRate({
      pending,
      forrigeRate: rate,
      ankomst: maaltAnkomst,
      dt: FRAME_S,
    })
    const maksPrFrame = Math.max(6, Math.ceil(rate * 0.1))
    kredit = Math.min(maksPrFrame, kredit + rate * FRAME_S)
    const step = Math.min(maksPrFrame, Math.floor(kredit))
    if (step <= 0) continue
    kredit -= step

    const foer = shown
    shown = Math.min(ankommet, shown + step)
    const vaekst = shown - foer
    if (vaekst > stoersteSpring) stoersteSpring = vaekst
    if (vaekst > 0) sidsteVaekst = sekunder
  }

  return {
    sekunderTilAltSynligt: sekunder,
    stoersteSpring,
    laengsteDoedeTidS: laengsteDoedeTid,
    frames,
  }
}

/** B: Codex-modellen. Alt er i DOM ved frame 0; segmenter toner ind. */
function modelB(target: string): Resultat {
  // Segmenter = afsnit/listepunkter, som deres markdown-renderer deler det.
  const segmenter = target.split(/\n\n+/).filter((s) => s.trim().length > 0)

  // Sidste segments forsinkelse + fade-varighed = hvornår alt er synligt.
  const sidsteForsinkelse = Math.min(
    Math.max(0, segmenter.length - 1) * FADE_SEGMENT_DELAY_MS,
    FADE_SEGMENT_MAX_DELAY_MS,
  )
  const sekunderTilAlt = (sidsteForsinkelse + FADE_DURATION_MS) / 1000

  // Springet: hvor mange tegn bliver synlige i den frame hvor det STØRSTE
  // segment toner ind? Teksten er allerede i DOM — men usynlig — så det
  // brugeren ser komme, er ét helt segment ad gangen.
  const stoersteSegment = segmenter.reduce(
    (maks, s) => Math.max(maks, Array.from(s).length),
    0,
  )

  return {
    sekunderTilAltSynligt: sekunderTilAlt,
    stoersteSpring: stoersteSegment,
    // Ingen død tid: der sker noget fra frame 0.
    laengsteDoedeTidS: 0,
    frames: Math.round(sekunderTilAlt * FPS),
  }
}

function tekst(antalTegn: number): string {
  const afsnit = [
    'Paceren måler ankomsten over et vindue i stedet for pr. frame. ',
    'Det betyder at en chunk på hundrede tegn ikke læses som seks tusind tegn i sekundet. ',
    'Raten glider tilbage mod grundtempoet med en halveringstid på ét sekund. ',
    'Uden tilbagefaldet satte én burst tempoet for resten af svaret. ',
    'Segmenterne toner ind med fireogtyve millisekunders forskydning. ',
    'Forsinkelsen har et loft på otte hundrede millisekunder. ',
    'Der findes også en tidslinje-variant der måler faktisk ankomst. ',
    'Ventilen kalder onComplete efter to og et halvt sekund. ',
  ]
  let ud = ''
  let i = 0
  while (Array.from(ud).length < antalTegn) {
    ud += afsnit[i % afsnit.length]
    i += 1
    if (i % 4 === 0) ud += '\n\n'
  }
  return ud
}

describe('PACE-MODELLER — tidslig pacer mod rumlig fade', () => {
  it('A: paceren — jævn udrulning, ingen spring', () => {
    for (const antal of [300, 1000, 2000]) {
      const a = modelA(tekst(antal), 100_000) // alt ankommer i ét hug
      // eslint-disable-next-line no-console
      console.log(
        `A ${antal} tegn: ${a.sekunderTilAltSynligt.toFixed(2)} s · ` +
          `største spring ${a.stoersteSpring} tegn · ` +
          `død tid ${a.laengsteDoedeTidS.toFixed(2)} s`,
      )
      expect(a.sekunderTilAltSynligt).toBeGreaterThan(0)
    }
  })

  it('B: faden — alt synligt med det samme, ét segment ad gangen', () => {
    for (const antal of [300, 1000, 2000]) {
      const b = modelB(tekst(antal))
      // eslint-disable-next-line no-console
      console.log(
        `B ${antal} tegn: ${b.sekunderTilAltSynligt.toFixed(2)} s · ` +
          `største spring ${b.stoersteSpring} tegn · ` +
          `død tid ${b.laengsteDoedeTidS.toFixed(2)} s`,
      )
      expect(b.sekunderTilAltSynligt).toBeLessThanOrEqual(1.0)
    }
  })

  it('sammenligning: forholdet mellem modellerne ved 2000 tegn', () => {
    const a = modelA(tekst(2000), 100_000)
    const b = modelB(tekst(2000))
    // eslint-disable-next-line no-console
    console.log(
      `\n2000 tegn — A: ${a.sekunderTilAltSynligt.toFixed(2)} s / ` +
        `spring ${a.stoersteSpring} · ` +
        `B: ${b.sekunderTilAltSynligt.toFixed(2)} s / spring ${b.stoersteSpring}`,
    )
    console.log(
      `A er ${(a.sekunderTilAltSynligt / b.sekunderTilAltSynligt).toFixed(1)}x ` +
        `langsommere, men springet er ${(b.stoersteSpring / Math.max(1, a.stoersteSpring)).toFixed(0)}x mindre`,
    )
    expect(a.sekunderTilAltSynligt).toBeGreaterThan(b.sekunderTilAltSynligt)
  })
})
