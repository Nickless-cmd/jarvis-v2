import { describe, expect, it, vi } from 'vitest'
import { render } from '@testing-library/react'
import { KarakterFigur } from './KarakterFigur'
import { karakterFigur } from '../../lib/karakterFigur'

/**
 * `MatrixKarakterer` henter selv via en pollende hook. Her mocks kilden og
 * hooken, så testen måler RENDERINGEN — ikke netværket.
 *
 * `vi.hoisted` fordi `vi.mock`-fabrikkerne løftes op over modulkroppen; uden
 * den ville `TESTDATA` være udefineret i det øjeblik fabrikken kører.
 */
const { TESTDATA } = vi.hoisted(() => ({
  TESTDATA: {
    active: true,
    tempo: 1,
    antal: 3,
    karakterer: [
      {
        name: 'red_dress', funktion: 'Rød kjole — fristelse', priority: 1,
        cooldown_minutes: 60, effektiv_cooldown_minutes: 60,
        last_run_at: '2026-11-18T20:00:00Z',
        udfald: { outcome: 'by_design', tekst: 'grænse i designet', tone: 'neutral' },
        udfald_at: '2026-11-18T20:00:00Z',
      },
      {
        name: 'oracle', funktion: 'Oraklet — forudsigelse', priority: 2,
        cooldown_minutes: 120, effektiv_cooldown_minutes: 120,
        last_run_at: null, udfald: null, udfald_at: null,
      },
      {
        name: 'trainman', funktion: 'Togmanden — kadence', priority: 3,
        cooldown_minutes: 30, effektiv_cooldown_minutes: 30,
        last_run_at: '2026-11-18T19:00:00Z',
        udfald: { outcome: 'ukendt_kode', tekst: 'ukendt_kode', tone: 'ukendt' },
        udfald_at: '2026-11-18T19:00:00Z',
      },
    ],
  },
}))

vi.mock('../../lib/api', () => ({ getMatrixKarakterer: vi.fn(async () => TESTDATA) }))
vi.mock('../../hooks/usePollWhenVisible', () => ({
  usePollWhenVisible: () => ({ data: TESTDATA, loading: false, error: null }),
}))

// Importeres EFTER mocks, ellers binder den den rigtige hook.
const { MatrixKarakterer } = await import('./MatrixKarakterer')

describe('KarakterFigur', () => {
  it('tegner en figur med mindst én form', () => {
    const { container } = render(<KarakterFigur navn="red_dress" />)
    const svg = container.querySelector('svg')
    expect(svg).not.toBeNull()
    // En tom <svg> ville bestå denne test hvis vi kun tjekkede eksistens —
    // derfor kræves mindst ét tegnet barn ud over øjnene (2 cirkler).
    const former = svg!.querySelectorAll('circle, rect, path, ellipse')
    expect(former.length).toBeGreaterThan(2)
  })

  it('tegner den samme figur for det samme navn', () => {
    const a = render(<KarakterFigur navn="morpheus" />).container.innerHTML
    const b = render(<KarakterFigur navn="morpheus" />).container.innerHTML
    expect(a).toBe(b)
  })

  it('tegner forskellige figurer for navne med forskellig form eller farve', () => {
    const a = karakterFigur('red_dress')
    const b = karakterFigur('oracle')
    // Kun meningsfuldt hvis de faktisk er forskellige — ellers måler vi ingenting.
    expect(`${a.shape}|${a.farve}`).not.toBe(`${b.shape}|${b.farve}`)
    const htmlA = render(<KarakterFigur navn="red_dress" />).container.innerHTML
    const htmlB = render(<KarakterFigur navn="oracle" />).container.innerHTML
    expect(htmlA).not.toBe(htmlB)
  })

  it('er skjult for skaermlaesere, saa navnet ikke laeses to gange', () => {
    const { container } = render(<KarakterFigur navn="ghost" />)
    expect(container.querySelector('svg')!.getAttribute('aria-hidden')).toBe('true')
  })
})

describe('MatrixKarakterer — figuren staar i hver raekke', () => {
  it('giver hver karakter en figur', () => {
    const { container } = render(<MatrixKarakterer config={undefined} />)
    const figurer = container.querySelectorAll('svg.mk-figur')
    expect(figurer.length).toBe(TESTDATA.karakterer.length)
  })

  it('bruger MASKINNAVNET, saa figuren ikke skifter naar beskrivelsen rettes', () => {
    const { container } = render(<MatrixKarakterer config={undefined} />)
    const raekker = container.querySelectorAll('.mk-raekke')
    expect(raekker.length).toBe(TESTDATA.karakterer.length)
    TESTDATA.karakterer.forEach((k, i) => {
      const svg = raekker[i]!.querySelector('svg.mk-figur')
      expect(svg).not.toBeNull()
      // Hovedgruppen bærer karakterens farve. Holder vi op med at bruge
      // `k.name` og i stedet falder tilbage på det viste navn, ændrer farven
      // sig for enhver karakter hvis `funktion` er redigeret.
      const farve = svg!.querySelector('g')!.getAttribute('fill')
      expect(farve).toBe(karakterFigur(k.name).farve)
    })
  })

  it('viser stadig navn, cooldown og udfald ved siden af figuren', () => {
    const { container } = render(<MatrixKarakterer config={undefined} />)
    const tekst = container.textContent ?? ''
    expect(tekst).toContain('Rød kjole')
    expect(tekst).toContain('grænse i designet')
    // En karakter uden udfald maa ikke se groen ud — den er ukendt.
    expect(tekst).toContain('ukendt')
  })
})
