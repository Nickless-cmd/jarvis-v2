import { describe, it, expect } from 'vitest'
import { railAnchors, railLabel } from './MessageRail'

/**
 * Bjørn 8/9-2026: skinnen er «rimelig useriøs og ufunktionel».
 *
 * Den markerede ALTID den sidste besked som aktiv — `is-active` var hardkodet
 * til `anchors[length-1]`. Den fortalte altså ikke hvor man var, men hvor
 * samtalen sluttede, hvilket man i forvejen ved.
 */
const bruger = (id: string, tekst: string) => ({ id, role: 'user', content: [{ type: 'text', text: tekst }] })
const svar = (id: string, blokke: unknown[]) => ({ id, role: 'assistant', content: blokke })

describe('railLabel', () => {
  it('tager FØRSTE LINJE, ikke de første 80 tegn', () => {
    // En besked med to linjers indledning gav før et fragment der stoppede midt
    // i et ord.
    expect(railLabel([{ type: 'text', text: 'Kan du kigge på gaten?\nDen fejler i produktion.' }]))
      .toBe('Kan du kigge på gaten?')
  })

  it('stripper markdown-indledning', () => {
    expect(railLabel([{ type: 'text', text: '## Overskrift\nnoget' }])).toBe('Overskrift')
    expect(railLabel([{ type: 'text', text: '> citat' }])).toBe('citat')
  })

  it('springer tomme linjer over', () => {
    expect(railLabel([{ type: 'text', text: '\n\n  \nrigtig tekst' }])).toBe('rigtig tekst')
  })

  it('klipper en meget lang linje med ellipse', () => {
    const l = railLabel([{ type: 'text', text: 'x'.repeat(200) }])
    expect(l.length).toBe(72)
    expect(l.endsWith('…')).toBe(true)
  })

  it('falder tilbage på «Besked» frem for at vise ingenting', () => {
    expect(railLabel([])).toBe('Besked')
    expect(railLabel(null)).toBe('Besked')
  })
})

describe('railAnchors', () => {
  it('ét anker pr. bruger-besked', () => {
    const a = railAnchors([bruger('u1', 'et'), svar('a1', []), bruger('u2', 'to')])
    expect(a.map((x) => x.id)).toEqual(['u1', 'u2'])
  })

  it('markerer turen når SVARET indeholdt en fejl', () => {
    // Bruger-beskeden bærer ingen fejl — den ligger i svaret bagefter. Derfor
    // ses der frem til næste bruger-besked.
    const a = railAnchors([
      bruger('u1', 'gør noget'),
      svar('a1', [{ type: 'tool_use', status: 'error' }]),
      bruger('u2', 'og så'),
      svar('a2', [{ type: 'tool_use', status: 'done' }]),
    ])
    expect(a[0]!.fejl).toBe(true)
    expect(a[1]!.fejl).toBe(false)
  })

  it('en fejl smitter ikke bagud på den forrige tur', () => {
    const a = railAnchors([
      bruger('u1', 'fin tur'),
      svar('a1', [{ type: 'tool_use', status: 'done' }]),
      bruger('u2', 'skidt tur'),
      svar('a2', [{ type: 'tool_result', is_error: true }]),
    ])
    expect(a[0]!.fejl).toBe(false)
    expect(a[1]!.fejl).toBe(true)
  })

  it('tom samtale giver ingen ankre — skinnen skjuler sig selv', () => {
    expect(railAnchors([])).toEqual([])
  })
})

describe('robusthed', () => {
  it('uden en container vælter skinnen ikke', async () => {
    // Ref'en er null i den ene render før transcript-div'en findes.
    const { render, screen } = await import('@testing-library/react')
    const { MessageRail } = await import('./MessageRail')
    const { createRef } = await import('react')
    const ref = createRef<HTMLElement>()
    expect(() => render(
      <MessageRail containerRef={ref} anchors={[{ id: 'a', label: 'en' }, { id: 'b', label: 'to' }]} />,
    )).not.toThrow()
    expect(screen.getByText('en')).toBeTruthy()
  })
})
