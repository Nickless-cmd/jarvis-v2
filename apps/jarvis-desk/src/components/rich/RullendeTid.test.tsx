import { render } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { RullendeTid } from './RullendeTid'

describe('RullendeTid — turens ur', () => {
  it('ruller kun ÆGTE cifre — mellemrummet i «1m 51s» er ikke et nul', () => {
    // Bjørn 17/10-2026: uret stod som «1m051s». `Number(' ')` er 0, og
    // `Number.isInteger(0)` er sand, så mellemrummet blev et rullende ciffer.
    // Testen er derfor på TEGNET, ikke på om det kan læses som et tal.
    const { container } = render(<RullendeTid tekst="1m 51s" />)
    expect(container.querySelectorAll('.rv-turTidCiffer')).toHaveLength(3)
    // Mellemrummet er det afgørende: det skal stå som FAST tekst, ikke som
    // et rullende nul. `textContent` kan ikke bruges til at bevise det —
    // hver ciffer-strimmel bærer hele 0-9 i DOM'en.
    const faste = [...container.querySelectorAll('.rv-turTidFast')].map((n) => n.textContent)
    expect(faste).toEqual(['m', ' ', 's'])
  })

  it('holder tidsleddene som fast tekst', () => {
    const { container } = render(<RullendeTid tekst="42s" />)
    expect(container.querySelectorAll('.rv-turTidCiffer')).toHaveLength(2)
    const faste = [...container.querySelectorAll('.rv-turTidFast')].map((n) => n.textContent)
    expect(faste).toEqual(['s'])
  })

  it('skærmlæsere får den flade streng, ikke ciffer-strimlerne', () => {
    const { container } = render(<RullendeTid tekst="1m 51s" />)
    const ur = container.querySelector('.rv-turTid') as HTMLElement
    expect(ur).toHaveAttribute('aria-label', '1m 51s')
    expect(ur).toHaveAttribute('role', 'timer')
  })
})
