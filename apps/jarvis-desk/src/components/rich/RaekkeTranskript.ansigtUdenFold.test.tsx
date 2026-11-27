import { describe, it, expect, beforeEach } from 'vitest'
import { render } from '@testing-library/react'
import { RaekkeTranskript } from './RaekkeTranskript'
import { SettingsProvider } from '../../contexts/SettingsContext'
import { RAEKKE_KEY } from '../../lib/visningsPref'
import type { ContentBlock } from '../../lib/sseProtocol'

/**
 * Turens ansigt uden for folden — og hvilket sprog det taler.
 *
 * ## To kontrakter, to faser
 *
 * Filen hed før `RaekkeTranskript.ventelinje.test.tsx` og beviste en håndlavet
 * ventelinje: en `.rv-arbejdsrunde` med klassen `.rv-venter`, der stod uden for
 * folden fra første frame og viste den FØRSTE rundes tekst. Bjørn 27/11-2026
 * afviste den: «det der vises uden for foldet er det aller første
 * runde/tænke blokke og det burde slet ikk være».
 *
 * **Fase 1 — før svaret begynder:** der er ingen rundelinje uden for folden.
 * Uden for den er der kun hovedet (`.rv-tur`), som er turens eneste ansigt og
 * derfor også bærer turen fra første frame.
 *
 * **Fase 2 — efter svaret er begyndt:** runderne skal FORTSÆTTE uden for
 * folden. Bjørn: «runderne og den aktive runde linje skal forsætte udenfor
 * foldet». De skal tegnes af den SAMME komponent som runderne inde i folden —
 * `Arbejdsrunde`, altså `.rv-arbejdsrunde`.
 *
 * ## Hvorfor fase 2 har sin egen vagt
 *
 * Målt på Bjørns to skærmbilleder 27/11-2026: uden for folden faldt runden i
 * `svar`, som tegnes af `BlocksRenderer` — bobble-sproget. Det gav fast
 * `</>`-ikon (`.toolgroup`), et ur, og tænkningen som sin EGEN linje
 * (`.toolgroup.tanke-linje`). Inde i folden gav `Arbejdsrunde` én samlet linje
 * uden ikon på den færdige runde. To sprog for den samme ting.
 *
 * Vagtens ærinde er derfor ikke «ingen rundelinje uden for folden» længere,
 * men «uden for folden taler runderne rundelinjens sprog, ikke bobble-sproget».
 */

const kald = (navn: string, id: string, status: 'running' | 'done' = 'done'): ContentBlock => ({
  type: 'tool_use', id, name: navn,
  input: { command: navn === 'bash' ? 'git status' : undefined },
  status,
  // Resultatet bor PÅ kaldet — `tool_result` er ikke en egen blok i
  // `ContentBlock`; den foldes ind i `tool_use` før `opdel` ser listen.
  ...(status === 'done' ? { result: 'ok' } : {}),
})

const svarTekst = (t: string): ContentBlock => ({ type: 'text', text: t, phase: 'final_answer' })

beforeEach(() => { localStorage.setItem(RAEKKE_KEY, '1') })

function vis(props: {
  blocks?: ContentBlock[]
  streaming?: boolean
  finalAnswerStarted?: boolean
  arbejdeEfterSvar?: boolean
  workingStep?: string | null
}) {
  return render(
    <SettingsProvider>
      <RaekkeTranskript
        blocks={props.blocks ?? []}
        streaming={props.streaming ?? true}
        finalAnswerStarted={props.finalAnswerStarted}
        arbejdeEfterSvar={props.arbejdeEfterSvar}
        workingStep={props.workingStep}
      />
    </SettingsProvider>,
  )
}

/** Rundelinjer der IKKE ligger inde i foldens gruppe — altså dem EFTER foldet. */
const runderEfterFold = (c: HTMLElement) =>
  Array.from(c.querySelectorAll('.rv-arbejdsrunde')).filter(
    (el) => el.closest('.rv-gruppe') === null,
  )

describe('fase 1 — før svaret begynder', () => {
  it('viser Jarvis’ animerede ikon indtil første modelindhold', () => {
    const { container } = vis({ blocks: [], streaming: true })

    const waiting = container.querySelector('.rv-modelventer')!
    expect(waiting).toHaveAttribute('role', 'status')
    expect(waiting).toHaveAttribute('aria-label', 'Jarvis tænker')
    expect(waiting.querySelector('.jarvis-pulse.is-working')).not.toBeNull()
    expect(waiting.textContent).toBe('')
    expect(container.querySelector('.rv-tur')).toBeNull()
  })

  it('bevarer ikonet gennem tomme startblokke og overleverer ved første modelindhold', () => {
    const { container, rerender } = vis({ blocks: [{ type: 'text', text: '', code_answer_protocol: 1 }] })
    expect(container.querySelector('.rv-modelventer .jarvis-pulse.is-working')).not.toBeNull()
    rerender(<SettingsProvider><RaekkeTranskript streaming blocks={[
      { type: 'thinking', thinking: 'Undersøger opgaven' }, kald('bash', 'first', 'running'),
    ]} /></SettingsProvider>)
    expect(container.querySelector('.rv-modelventer')).toBeNull()
    expect(container.querySelector('.rv-arbejdsrunde[data-aktiv-runde] .jarvis-pulse.is-working')).not.toBeNull()
  })

  it('ignores an early legacy answer flag while protocol text is still commentary', () => {
    const { container } = vis({ streaming: true, finalAnswerStarted: true, blocks: [
      kald('bash', 'working', 'running'),
      { type: 'text', text: 'Nu undersøger jeg processen.', phase: 'final_answer', code_answer_protocol: 1 },
    ] })
    expect(container.querySelector('.rv-gruppe-ydre')).toHaveAttribute('data-aaben', 'true')
    expect(container.querySelector('.rv-tur')).toBeNull()
  })

  it('viser INGEN rundelinje uden for folden — heller ikke fra forste frame', () => {
    // Det var her den håndlavede ventelinje stod. Den er væk, og fraværet er
    // kontrakten: før svaret begynder findes rundelinjerne kun inde i folden.
    const { container } = vis({ blocks: [], streaming: true })

    expect(container.querySelector('.rv-venter')).toBeNull()
    expect(runderEfterFold(container)).toHaveLength(0)
  })

  it('lægger runderne INDE i folden naar arbejdet kommer', () => {
    const { container } = vis({ blocks: [kald('bash', 'b1')], streaming: true })

    const gruppe = container.querySelector('.rv-gruppe')
    expect(gruppe).not.toBeNull()
    expect(gruppe!.querySelector('.rv-arbejdsrunde')).not.toBeNull()
    // Og intet uden for den, saa længe svaret ikke er begyndt.
    expect(runderEfterFold(container)).toHaveLength(0)
  })

  it('serverens arbejdstrin bliver inde i den aktive runde, ikke uden for folden', () => {
    const { container } = vis({ blocks: [kald('bash', 'b1', 'running')], streaming: true, workingStep: 'Læser app.ts' })

    expect(container.textContent).toContain('Læser app.ts')
    expect(runderEfterFold(container)).toHaveLength(0)
  })
})

describe('fase 2 — runder efter foldet', () => {
  it('tegner runden som RUNDELINJE, ikke som bobble-kort', () => {
    // Bjørns to skærmbilleder, oversat til en maaling: inde i folden gav
    // `Arbejdsrunde` én linje; uden for den tog `BlocksRenderer` over og gav
    // `</>`-ikon, ur og en løs tænke-linje. Det er forskellen der skal væk.
    const { container } = vis({
      blocks: [kald('bash', 'b1'), svarTekst('Svaret.'), kald('remember_this', 'b2')],
      streaming: true,
      finalAnswerStarted: true,
    })

    // Runden efter svaret staar uden for folden — det er kontrakten.
    expect(runderEfterFold(container)).toHaveLength(1)
    // Og den taler rundelinjens sprog.
    expect(container.querySelector('.rv-arbejdsknap')).not.toBeNull()
    // Bobble-sproget maa IKKE have taget den.
    expect(container.querySelector('.toolgroup')).toBeNull()
    expect(container.querySelector('.tanke-linje')).toBeNull()
  })

  it('bevarer rækkefølgen: tekst, runde, tekst', () => {
    // Rækkefølgen var hele grunden til at `svarSektioner` findes: en flad
    // opdeling ville flytte runden eller teksten.
    const { container } = vis({
      blocks: [svarTekst('Første del.'), kald('remember_this', 'b1'), svarTekst('Anden del.')],
      streaming: false,
      finalAnswerStarted: true,
    })

    const svar = container.querySelector('.rv-svar')
    expect(svar).not.toBeNull()
    const boern = Array.from(svar!.children)
    // Barn 1: teksten. Barn 2: rundelinjen. Barn 3: teksten igen.
    expect(boern).toHaveLength(3)
    expect(boern[1]!.querySelector('.rv-arbejdsrunde')).not.toBeNull()
    expect(boern[1]!.className).toContain('rv-sen-runde')
    expect(container.textContent).toContain('Første del.')
    expect(container.textContent).toContain('Anden del.')
  })

  it('beholder et ansigt naar arbejde kommer EFTER svar-laasen', () => {
    const { container } = vis({
      blocks: [], streaming: true, finalAnswerStarted: true, arbejdeEfterSvar: true,
    })

    expect(container.querySelector('.rv-tur')).not.toBeNull()
    expect(container.querySelector('.rv-venter')).toBeNull()
  })
})

describe('den fulde sekvens — runde, syntese, fold, slutbesked, runde, syntese', () => {
  /**
   * Bjørns sekvens, ordret (27/11-2026). Den er ikke en abstraktion; hvert led
   * har sin egen ejer, og fejlen der blev målt den dag sad i overgangen mellem
   * led 2 og 3: syntesen der lå i folden blev teleporteret ud i det øjeblik
   * foldet skete, fordi `underArbejde` faldt til falsk.
   *
   * Model-testen (`raekkeModel.sekvens.test.ts`) beviser klassificeringen.
   * Denne beviser at komponenten TEGNER den samme fordeling — ellers kan de to
   * drive fra hinanden uden at nogen af testene ser det.
   */
  const syntese = (t: string): ContentBlock => ({ type: 'text', text: t })

  it('tegner syntesen FOER foldet inde i folden — den flytter sig ikke naar foldet sker', () => {
    const blokke = [
      kald('bash', 'b1'),
      syntese('Lad mig se på filen.'),
      svarTekst('Sådan ser det ud.'),
      kald('remember_this', 'b2'),
      syntese('Gemt.'),
    ]
    const { container } = vis({ blocks: blokke, streaming: false, finalAnswerStarted: true })

    // Folden er LUKKET her (turen er slut), så dens indhold er ikke monteret —
    // `.rv-gruppe` er med vilje tom. At kræve teksten dér ville måle foldens
    // animations-tilstand, ikke ejerskabet. Ejerskabet er allerede bevist i
    // `raekkeModel.sekvens.test.ts`; her bevises den anden halvdel: at den
    // ikke OGSÅ står i svaret.
    const svar = container.querySelector('.rv-svar')
    expect(svar).not.toBeNull()
    expect(svar!.textContent).not.toContain('Lad mig se på filen.')

    // Folden findes og er lukket — det er den beholder syntesen hører til.
    const ydre = container.querySelector('.rv-gruppe-ydre')
    expect(ydre).not.toBeNull()
    expect(ydre!.getAttribute('data-aaben')).toBe('false')
  })

  it('tegner runden EFTER foldet som rundelinje og syntesen bagefter den', () => {
    const blokke = [
      kald('bash', 'b1'),
      syntese('Lad mig se på filen.'),
      svarTekst('Sådan ser det ud.'),
      kald('remember_this', 'b2'),
      syntese('Gemt.'),
    ]
    const { container } = vis({ blocks: blokke, streaming: false, finalAnswerStarted: true })

    const svar = container.querySelector('.rv-svar')!
    const boern = Array.from(svar.children)

    // Slutbesked → rundelinje → syntese. Tre børn, i den rækkefølge.
    expect(boern).toHaveLength(3)
    expect(boern[1]!.querySelector('.rv-arbejdsrunde')).not.toBeNull()
    expect(boern[1]!.className).toContain('rv-sen-runde')
    expect(svar.textContent).toContain('Sådan ser det ud.')
    expect(svar.textContent).toContain('Gemt.')

    // Syntesen staar EFTER rundelinjen, ikke foer den.
    const rundeIdx = boern.findIndex((b) => b.className.includes('rv-arbejdsrunde'))
    const synteseIdx = boern.findIndex((b) => b.textContent?.includes('Gemt.'))
    expect(synteseIdx).toBeGreaterThan(rundeIdx)

    // Og bobble-sproget har ikke taget nogen af dem.
    expect(container.querySelector('.toolgroup')).toBeNull()
  })
})
