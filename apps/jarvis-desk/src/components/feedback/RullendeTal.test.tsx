import { describe, it, expect } from 'vitest'
import { render } from '@testing-library/react'
import { RullendeTokens, RullendeUr } from './RullendeTal'

/**
 * Hjulenes aktuelle cifre i træets rækkefølge (venstre → højre).
 *
 * Hvert hjul har ét aktuelt ciffer og, mens det ruller, ét udgående ciffer.
 * Det aktuelle står sidst i gridcellen.
 */
const aktuelle = (c: HTMLElement): string[] =>
  Array.from(c.querySelectorAll('.hjul')).map((e) => e.lastElementChild?.textContent ?? '')

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
    expect(aktuelle(container)).toEqual(['9'])

    rerender(<RullendeUr sek={10} />)
    expect(aktuelle(container)).toEqual(['1', '0'])
    expect(container.querySelectorAll('.hjul-ciffer--ind-op')).toHaveLength(1)
  })

  /** Uret skriver «5s»/«45s»/«1m 12s» — ikke «00:05». */
  it('uret skriver varigheden som «1m 12s»', () => {
    const { container } = render(<RullendeUr sek={72} />)
    expect(container.querySelector('[role="timer"]')?.getAttribute('aria-label')).toBe('1m 12s')
  })

  it('tegner token-cifrene som synlig tekst sammen med k-suffikset', () => {
    const { container } = render(<RullendeTokens tokens={1_234} />)
    expect(container.querySelector('.rullende')).toHaveAttribute('aria-label', '1.2k')
    expect(aktuelle(container)).toEqual(['1', '2'])
    expect([...container.querySelectorAll('.tegn')].map((e) => e.textContent)).toEqual(['.', 'k'])
  })

  it('holder det aktuelle ciffer i normal layout, så turens shimmer kan male det', () => {
    const { container, rerender } = render(<RullendeUr sek={59} />)
    rerender(<RullendeUr sek={60} />)
    expect(container.querySelectorAll('.hjul-spor')).toHaveLength(0)
    // Ener-hjulet genbruges og ruller 9 → 0; det nye minut-hjul monteres
    // direkte på 1, så format-skiftet ikke starter en falsk ekstra animation.
    expect(container.querySelectorAll('.hjul-ciffer--ind-op')).toHaveLength(1)
    expect(aktuelle(container)).toEqual(['1', '0'])
  })
})
