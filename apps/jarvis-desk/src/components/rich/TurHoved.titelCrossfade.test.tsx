import { act, render } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { TitelCrossfade } from './TurHoved'
import type { VisuelTransition } from '../../lib/visuelTransition'

describe('TitelCrossfade — serverstyret loft', () => {
  afterEach(() => vi.useRealTimers())

  it('skifter straks når serverens trin skifter', () => {
    vi.useFakeTimers()
    const view = render(
      <TitelCrossfade tekst="Læser konfigurationen" aktiv intervalMs={3500} />,
    )
    const foer = view.getByText('Læser konfigurationen')

    view.rerender(
      <TitelCrossfade tekst="Tester løsningen" aktiv intervalMs={3500} />,
    )

    const efter = view.getByText('Tester løsningen')
    expect(efter).not.toBe(foer)
    expect(efter).toHaveAttribute('data-crossfade')
    expect(view.queryByText('Læser konfigurationen')).toBeNull()
  })

  it('skifter uden fade når transitionens crossfade-flag er falsk', () => {
    const transition = {
      model: 'duration',
      durationMs: 180,
      curve: 'ease-out',
      crossfade: false,
    } satisfies VisuelTransition
    const view = render(<TitelCrossfade tekst="Læser" aktiv transition={transition} />)

    view.rerender(<TitelCrossfade tekst="Tester" aktiv transition={transition} />)

    expect(view.getByText('Tester')).not.toHaveAttribute('data-crossfade')
    expect(view.queryByText('Læser')).toBeNull()
  })

  // Regression vagtet mod den fejl der blev målt 18/11-2026: med
  // `vist.transition` i dependency-arrayet genarmede timeren sig selv og
  // genstartede fade'en på UÆNDRET tekst — 3 re-fades på 11 s. Det er en
  // puls, ikke en crossfade. Bjørn 18/11: «Kun ved ægte trin-skift —
  // loftet som rent værn, ingen puls.»
  it('genstarter ALDRIG fade på uændret tekst, selv når loftet er passeret mange gange', () => {
    vi.useFakeTimers()
    const view = render(
      <TitelCrossfade tekst="Læser konfigurationen" aktiv intervalMs={3500} />,
    )
    const foer = view.getByText('Læser konfigurationen')

    // Ti loft-perioder på samme tekst — mere end nok til at en selvgenarmende
    // timer ville have fyret ti gange.
    act(() => { vi.advanceTimersByTime(3500 * 10) })

    const efter = view.getByText('Læser konfigurationen')
    expect(efter).toBe(foer)
    expect(view.container).toHaveTextContent('Læser konfigurationen')
    expect(view.container.querySelectorAll('.rv-titelCrossfadeTekst')).toHaveLength(1)
  })

  it('skifter straks når trinnet skifter EFTER loftet er udløbet', () => {
    vi.useFakeTimers()
    const view = render(
      <TitelCrossfade tekst="Venter på agenter" aktiv intervalMs={1200} />,
    )
    act(() => { vi.advanceTimersByTime(5000) })
    const foer = view.getByText('Venter på agenter')

    view.rerender(
      <TitelCrossfade tekst="Skriver filen" aktiv intervalMs={1200} />,
    )

    const efter = view.getByText('Skriver filen')
    expect(efter).not.toBe(foer)
    expect(efter).toHaveAttribute('data-crossfade')
  })

  it('fader ikke når komponenten ikke er aktiv', () => {
    vi.useFakeTimers()
    const view = render(
      <TitelCrossfade tekst="Venter på agenter" aktiv={false} intervalMs={1200} />,
    )
    const foer = view.getByText('Venter på agenter')
    act(() => { vi.advanceTimersByTime(5000) })
    expect(view.getByText('Venter på agenter')).toBe(foer)
  })
})
