import { describe, it, expect } from 'vitest'
import { render } from '@testing-library/react'
import { RullendeUr } from './RullendeTal'

/**
 * Hjulenes `translateY`, i træets rækkefølge (venstre → højre).
 *
 * Et hjul viser cifferet ved `-position em`, så positionen er det eneste
 * sted i DOM'en hvor man kan se HVILKET ciffer der faktisk står — og dermed
 * om et hjul blev GENBRUGT (står på det gamle ciffer) eller nymonteret (står
 * på sit eget).
 */
const spor = (c: HTMLElement): string[] =>
  Array.from(c.querySelectorAll('.hjul-spor')).map((e) => (e as HTMLElement).style.transform)

describe('RullendeTal', () => {
  /**
   * MÅLT 4/10-2026 i mobilen (samme kode): med `key={i}` genbrugte React det
   * forreste hjul da strengen voksede, så «9s» → «10s» lod hjul 0 gå 9 → 1.
   * Da 1 < 9 ramte det viklings-grenen og viste «0» — uret stod på «90s».
   *
   * MUT: sæt nøglen tilbage til `i` → det forreste spor står på -10em
   * (viklingen) i stedet for -1em → fanger.
   */
  it('«9s» → «10s»: det nye ciffer foran monteres på sit eget tal', () => {
    const { container, rerender } = render(<RullendeUr sek={9} />)
    expect(spor(container)).toEqual(['translateY(-9em)'])

    rerender(<RullendeUr sek={10} />)
    expect(spor(container)[0]).toBe('translateY(-1em)')
  })

  /** Uret skriver «5s»/«45s»/«1m 12s» — ikke «00:05». */
  it('uret skriver varigheden som «1m 12s»', () => {
    const { container } = render(<RullendeUr sek={72} />)
    expect(container.querySelector('[role="timer"]')?.getAttribute('aria-label')).toBe('1m 12s')
  })
})
