import { describe, it, expect, beforeEach } from 'vitest'
import { render } from '@testing-library/react'
import { RaekkeTranskript } from './RaekkeTranskript'
import { SettingsProvider } from '../../contexts/SettingsContext'
import { RAEKKE_KEY } from '../../lib/visningsPref'
import type { ContentBlock } from '../../lib/sseProtocol'

/**
 * Rundelinjen bærer livet — også før det første værktøjskald.
 *
 * Bjørn 16/11-2026: «den aktive rundelinje skal være synlig fra starten for
 * det er den der bærer livet... sådan er det os i chat mode».
 *
 * Målt før rettelsen: `senesteRunde` kræver mindst ét `tool_use`-element, og
 * `visTurhoved` kræver `arbejde.length > 0`. Fra turen startede til det første
 * kald landede, var code mode derfor HELT tom — hverken ring eller ord i
 * præcis det vindue hvor brugeren venter på et livstegn. Chat mode har haft en
 * placeholder hele tiden; den manglede her.
 *
 * Testene måler tilstanden, ikke implementeringen: at der står en ring med en
 * tekst fra FØRSTE frame, at den giver plads til den rigtige runde uden at
 * blive stående ved siden af den, og at den ikke overlever ind i svaret.
 */

const kald = (navn: string): ContentBlock => ({
  type: 'tool_use', id: `${navn}-1`, name: navn, input: {}, status: 'running',
})

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

const ventende = (c: HTMLElement) => c.querySelector('.rv-venter')
const aktiveRunder = (c: HTMLElement) => c.querySelectorAll('.rv-arbejdsrunde[data-aktiv-runde]')

describe('den ventende rundelinje', () => {
  it('staar der fra forste frame — tur startet, intet arbejde endnu', () => {
    const { container } = vis({ blocks: [], streaming: true })

    expect(ventende(container)).not.toBeNull()
    // Teksten er den aelige tilstand: turen koerer, der er intet at fortælle.
    expect(container.textContent).toContain('Tænker')
    // Ringen er tilstedeværelsen — ikke et ikon for et vaerktoej der ikke er kaldt.
    expect(container.querySelector('.rv-arbejdsikon svg')).not.toBeNull()
  })

  it('giver pladsen til den rigtige runde — aldrig to linjer ved siden af hinanden', () => {
    const { container } = vis({ blocks: [kald('bash')], streaming: true })

    expect(ventende(container)).toBeNull()
    expect(aktiveRunder(container)).toHaveLength(1)
  })

  it('forsvinder naar svaret begynder', () => {
    const { container } = vis({ blocks: [], streaming: true, finalAnswerStarted: true })

    expect(ventende(container)).toBeNull()
  })

  it('forsvinder naar turen er slut — den er en status, ikke et resultat', () => {
    const { container } = vis({ blocks: [], streaming: false })

    expect(ventende(container)).toBeNull()
  })

  it('viser serverens arbejde naar det findes, ellers Tænker', () => {
    // Raat vaerktoejsnavn maa ikke slippe igennem (samme vagt som rundelinjen).
    const raat = vis({ blocks: [], streaming: true, workingStep: 'bash' })
    expect(raat.container.textContent).toContain('Tænker')
    raat.unmount()

    const aegte = vis({ blocks: [], streaming: true, workingStep: 'Læser app.ts' })
    expect(aegte.container.textContent).toContain('Læser app.ts')
    expect(aegte.container.textContent).not.toContain('Tænker')
  })

  it('bliver staaende naar arbejde kommer EFTER svar-laasen', () => {
    // Svar-laasen beskytter svaret, ikke turen. Kommer der arbejde bagefter,
    // koerer turen stadig — og saa skal der stadig vaere et livstegn.
    const { container } = vis({ blocks: [], streaming: true, finalAnswerStarted: true, arbejdeEfterSvar: true })

    expect(ventende(container)).not.toBeNull()
  })
})
