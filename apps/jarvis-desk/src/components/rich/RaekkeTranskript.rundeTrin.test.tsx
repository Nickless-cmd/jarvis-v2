import { beforeEach, describe, expect, it } from 'vitest'
import { fireEvent, render } from '@testing-library/react'
import { RaekkeTranskript } from './RaekkeTranskript'
import { RAEKKE_KEY } from '../../lib/visningsPref'
import type { ContentBlock } from '../../lib/sseProtocol'

/**
 * Runde-tidslinjen i code mode — de syv scenarier fra Bjørns krav (15/11-2026).
 *
 * Kontrakten er én sætning: den AKTIVE runde viser processen, den AFSLUTTEDE
 * viser resultatet. Derfor må trin-listen kun findes mens runden kører, og den
 * afsluttede runde skal bære en ærlig meta om hvad der ligger bag den.
 */

const kald = (
  id: string,
  input: Record<string, unknown>,
  status?: 'running' | 'done' | 'error',
  navn = 'bash',
): ContentBlock => ({
  type: 'tool_use', id, name: navn, input, ...(status ? { status } : {}),
})
const tekst = (t: string): ContentBlock => ({ type: 'text', text: t })

const overskrift = (c: HTMLElement) =>
  c.querySelector('.rv-arbejdsfortaelling')?.textContent ?? null
const trin = (c: HTMLElement) => Array.from(c.querySelectorAll('.rv-trinRaekke'))
const meta = (c: HTMLElement) => c.querySelector('.rv-arbejdsmeta')?.textContent ?? null
const detaljer = (c: HTMLElement) => c.querySelector('.rv-arbejdsdetaljer')

/** Uden streaming er TURENS fold lukket, og så rendres runderne slet ikke.
 *  Det er den eksisterende adfærd (hovedet er turens resultat) — ikke noget
 *  denne ændring indfører. Åbn den, så runderne kan måles. */
function aabnTur(c: HTMLElement) {
  const hoved = c.querySelector('.rv-tur')
  if (hoved?.getAttribute('aria-expanded') === 'false') fireEvent.click(hoved)
}

beforeEach(() => { localStorage.setItem(RAEKKE_KEY, '1') })

describe('Runde-tidslinjen — aktiv runde viser processen', () => {
  it('1. viser rundens trin løbende, med status pr. trin', () => {
    const { container } = render(
      <RaekkeTranskript
        blocks={[
          kald('t1', { command: 'git status' }, 'done'),
          kald('t2', { command: 'npx vitest run' }, 'running'),
        ]}
        streaming workingStep="Tester rendering i Chromium…" />)

    // Overskriften er HVAD der arbejdes på — serverens egen formulering.
    expect(overskrift(container)).toBe('Tester rendering i Chromium…')
    // Trinnene er HVORDAN: de faktiske kald, i rækkefølge.
    const r = trin(container)
    expect(r).toHaveLength(2)
    expect(r[0]!.getAttribute('data-status')).toBe('done')
    expect(r[1]!.getAttribute('data-status')).toBe('active')
    expect(r[0]!.textContent).toContain('git status')
    expect(r[1]!.textContent).toContain('npx vitest')
    // Den afsluttede metatekst hører til de afsluttede runder — ikke her.
    expect(meta(container)).toBeNull()
  })

  it('2. skifter fra arbejdsvisning til resultatvisning når runden forlades', () => {
    const blocks = [
      kald('t1', { command: 'git status' }, 'done'),
      kald('t2', { command: 'npx vitest run' }, 'done'),
    ]
    const { container, rerender } = render(
      <RaekkeTranskript blocks={blocks} streaming workingStep="Tester rendering i Chromium…" />)
    expect(trin(container)).toHaveLength(2)

    rerender(<RaekkeTranskript blocks={blocks} streaming={false} />)
    aabnTur(container)

    // Processen er væk, resultatet står tilbage — uden staffage.
    expect(trin(container)).toHaveLength(0)
    expect(meta(container)).toBeNull()
    expect(overskrift(container)).toBeTruthy()
  })

  it('3. kun den sidste runde er aktiv — de afsluttede bærer ingen staffage', () => {
    const { container } = render(
      <RaekkeTranskript
        blocks={[
          kald('t1', { command: 'git status' }, 'done'),
          tekst('Første del er på plads.'),
          kald('t2', { command: 'ls src' }, 'done'),
          tekst('Nu ser jeg på komponenterne.'),
          kald('t3', { command: 'rg CSS' }, 'done'),
          kald('t4', { command: 'npx vitest run' }, 'running'),
        ]}
        streaming workingStep="Tester rendering i Chromium…" />)

    // Præcis ÉN trin-liste: den der arbejder lige nu.
    expect(container.querySelectorAll('.rv-trin')).toHaveLength(1)
    expect(trin(container)).toHaveLength(2)
    // De to afsluttede runder bærer hverken trin-liste eller meta: de gik
    // som de skulle, og så er der intet at advare om (Bjørn 15/11-2026).
    expect(container.querySelectorAll('.rv-arbejdsmeta')).toHaveLength(0)
  })
})

describe('Runde-tidslinjen — ærlighed når noget ikke gik som det skulle', () => {
  it('4. en fejlet runde fremstår ikke som en succes', () => {
    const { container } = render(
      <RaekkeTranskript
        blocks={[kald('t1', { command: 'curl /health' }, 'error')]}
        streaming={false} />)
    aabnTur(container)
    expect(trin(container)).toHaveLength(0)
    expect(meta(container)).toContain('1 fejlede')
  })

  it('4b. et kald der aldrig svarede markeres som afbrudt, ikke som fuldført', () => {
    const { container } = render(
      <RaekkeTranskript
        blocks={[
          kald('t1', { command: 'git status' }, 'done'),
          kald('t2', { command: 'sleep 900' }, 'running'),
        ]}
        streaming={false} />)
    aabnTur(container)
    expect(meta(container)).toContain('1 uden resultat')
  })
})

describe('Runde-tidslinjen — genindlæsning og historik', () => {
  it('5. en genåbnet session viser resultatet, ikke en proces der ikke kører', () => {
    const { container } = render(
      <RaekkeTranskript
        blocks={[
          kald('t1', { command: 'git status' }, 'done'),
          kald('t2', { command: 'npx vitest run' }, 'done'),
        ]}
        streaming={false} />)
    aabnTur(container)
    // Ingen markering af aktivitet: der ER ingen aktivitet.
    expect(container.querySelector('[data-aktiv-runde]')).toBeNull()
    expect(trin(container)).toHaveLength(0)
    expect(meta(container)).toBeNull()
  })

  it('7. historikken kan foldes ud efter runden er afsluttet', () => {
    const { container } = render(
      <RaekkeTranskript
        blocks={[
          kald('t1', { command: 'git status' }, 'done'),
          kald('t2', { command: 'npx vitest run' }, 'done'),
        ]}
        streaming={false} />)

    aabnTur(container)
    expect(detaljer(container)!.hasAttribute('hidden')).toBe(true)
    fireEvent.click(container.querySelector('.rv-arbejdsknap')!)
    // Værktøjskaldene ligger stadig i den udfoldede historik (niveau 3).
    expect(detaljer(container)!.hasAttribute('hidden')).toBe(false)
    // Fold-tilstanden er pilens sag, ikke en tekst på linjen.
    expect(meta(container)).toBeNull()
  })
})

describe('Runde-tidslinjen — streaming uden at indholdet hopper', () => {
  it('6. hurtigt efterfølgende kald opdaterer listen frem for at genopbygge den', () => {
    const foerste = [kald('t1', { command: 'git status' }, 'done'), kald('t2', { command: 'ls src' }, 'running')]
    const { container, rerender } = render(
      <RaekkeTranskript blocks={foerste} streaming workingStep="Undersøger komponenterne…" />)
    const foersteRaekke = trin(container)[0]!
    expect(trin(container)).toHaveLength(2)

    // Kaldet svarer, og et nyt starter — samme runde, ny tilstand.
    rerender(
      <RaekkeTranskript
        blocks={[
          kald('t1', { command: 'git status' }, 'done'),
          kald('t2', { command: 'ls src' }, 'done'),
          kald('t3', { command: 'npx vitest run' }, 'running'),
        ]}
        streaming workingStep="Tester rendering i Chromium…" />)

    expect(trin(container)).toHaveLength(3)
    // SAMME DOM-node: rækken er opdateret, ikke genskabt.
    expect(trin(container)[0]).toBe(foersteRaekke)
    expect(trin(container)[1]!.getAttribute('data-status')).toBe('done')
    expect(trin(container)[2]!.getAttribute('data-status')).toBe('active')
  })

  it('6b. overskriften bærer det kørende trin når serveren ikke har en egen formulering', () => {
    const { container } = render(
      <RaekkeTranskript
        blocks={[kald('t1', { command: 'git status' }, 'done'), kald('t2', { command: 'npx vitest run' }, 'running')]}
        streaming />)
    // Uden `working_step` ER overskriften det kørende kald — så må det ikke
    // stå to gange: linjen bærer det, listen viser historikken op til det.
    expect(overskrift(container)).toContain('npx vitest')
    expect(trin(container)).toHaveLength(1)
    expect(trin(container)[0]!.textContent).toContain('git status')
  })
})

describe('Runde-tidslinjen — persisteret historik (målt 15/11-2026)', () => {
  it('8. et gemt kald med et resultat siger intet — udfaldet er ikke en påstand', () => {
    // Ved reload folder `foldToolResults` det persisterede `tool_result` ind på
    // sit `tool_use` og sætter `status`. Målt i den levende base: 1.211 kald,
    // 1.211 resultater — alle afsluttede. Der er derfor intet at advare om.
    const { container } = render(
      <RaekkeTranskript
        blocks={[
          kald('p1', { command: 'git status' }, 'done'),
          kald('p2', { command: 'npx vitest run' }, 'done'),
          tekst('Færdig.'),
        ]}
        streaming={false} />)
    aabnTur(container)
    expect(trin(container)).toHaveLength(0)
    expect(meta(container)).toBeNull()
  })

  it('9. et kald huset har stemplet «uden resultat» meldes stadig ærligt', () => {
    // `afslutForladteKald` sætter `anomali` på et kald der aldrig fik et svar.
    // Stemplet skal nå linjen, ikke blive liggende i detaljen.
    const forladt = {
      ...kald('p3', { command: 'git status' }, 'done'),
      anomali: 'uden-resultat' as const,
    }
    const { container } = render(
      <RaekkeTranskript blocks={[forladt, tekst('Færdig.')]} streaming={false} />)
    aabnTur(container)
    expect(meta(container)).toContain('uden resultat')
  })
})
