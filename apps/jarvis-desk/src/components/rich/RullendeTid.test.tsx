import { readFileSync } from 'node:fs'
import { join } from 'node:path'
import { render } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { RullendeTid } from './RullendeTid'

describe('RullendeTid — turens ur', () => {
  it('ruller kun ÆGTE cifre — mellemrummet i «1m 51s» er ikke et nul', () => {
    // Bjørn 17/10-2026: uret stod som «1m051s». `Number(' ')` er 0, og
    // `Number.isInteger(0)` er sand, så mellemrummet blev et rullende ciffer.
    // Testen er derfor på TEGNET, ikke på om det kan læses som et tal.
    const { container } = render(<RullendeTid tekst="1m 51s" />)
    expect(container.querySelectorAll('.hjul')).toHaveLength(3)
    // Mellemrummet er det afgørende: det skal stå som FAST tekst, ikke som
    // et rullende nul. `textContent` kan ikke bruges til at bevise det —
    // et hjul kan under rulningen bære både forrige og aktuelt ciffer.
    const faste = [...container.querySelectorAll('.tegn')].map((n) => n.textContent)
    expect(faste).toEqual(['m', ' ', 's'])
  })

  it('holder tidsleddene som fast tekst', () => {
    const { container } = render(<RullendeTid tekst="42s" />)
    expect(container.querySelectorAll('.hjul')).toHaveLength(2)
    const faste = [...container.querySelectorAll('.tegn')].map((n) => n.textContent)
    expect(faste).toEqual(['s'])
  })

  it('mellemrummet har BREDDE — det er CSS, ikke DOM', () => {
    // Bjørn 17/10-2026: «der mangler mellemrum mellem Xm og Xs». Elementet
    // findes og bærer ' ' (testen ovenfor), men `.rv-turTidFast` er et
    // inline-block hvis ENESTE indhold er luft — og browseren kollapser
    // whitespace i en blok-container. Uden `white-space: pre` er bredden 0,
    // og uret står som «1m51s» uanset hvad DOM'en indeholder.
    const css = readFileSync(join(__dirname, '../../styles/liveness.css'), 'utf8')
    const blok = /\.rullende \.tegn\s*\{([^}]*)\}/.exec(css)
    expect(blok).not.toBeNull()
    expect(blok![1]).toMatch(/white-space:\s*pre/)
  })

  it('tæller op ved at føre nyt ciffer ind nedefra og det gamle ud opad', () => {
    const { container, rerender } = render(<RullendeTid tekst="9s" />)
    rerender(<RullendeTid tekst="10s" />)
    expect(container.querySelectorAll('.hjul-ciffer--ind-op')).toHaveLength(1)
    expect(container.querySelector('.hjul-ciffer--ud-op')).toHaveTextContent('9')
    expect(container.querySelector('.hjul-ciffer--ind-op')).toHaveTextContent('0')

    const css = readFileSync(join(__dirname, '../../styles/liveness.css'), 'utf8')
    expect(css).toMatch(/@keyframes hjul-ind-op\s*\{\s*from\s*\{\s*transform:\s*translateY\(100%\)/)
    expect(css).toMatch(/@keyframes hjul-ud-op\s*\{\s*from[^}]*translateY\(0\)[^}]*\}\s*to[^}]*translateY\(-100%\)/)
  })

  it('skærmlæsere får den flade streng, ikke ciffer-strimlerne', () => {
    const { container } = render(<RullendeTid tekst="1m 51s" />)
    const ur = container.querySelector('.rv-turTid') as HTMLElement
    expect(ur).toHaveAttribute('aria-label', '1m 51s')
    expect(ur).toHaveAttribute('role', 'timer')
  })
})
