import { describe, expect, it } from 'vitest'
import { render } from '@testing-library/react'
import { MarkdownRenderer } from './MarkdownRenderer'

/**
 * Matematik i chatviewet.
 *
 * MÅLT 20/10-2026: nul forekomster af katex, mathjax eller remark-math i
 * apps/jarvis-desk. En formel som `$e^{i\pi}+1=0$` kom ud som rå tekst, mens
 * ChatGPT, Claude og Gemini alle renderer LaTeX. Det var det eneste reelle hul
 * i dækningen — de øvrige 37 renderere findes i forvejen.
 */

describe('formel-rendering', () => {
  it('renderer inline-matematik', () => {
    const { container } = render(
      <MarkdownRenderer text={'Eulers identitet er $e^{i\\pi}+1=0$ og den er smuk.'} streaming={false} />)
    expect(container.querySelector('.katex')).not.toBeNull()
    // Den rå LaTeX må ikke stå tilbage som tekst.
    expect(container.textContent).not.toContain('e^{i\\pi}')
    // ...men den omgivende tekst skal være intakt.
    expect(container.textContent).toContain('Eulers identitet er')
    expect(container.textContent).toContain('og den er smuk')
  })

  it('renderer blok-matematik', () => {
    const { container } = render(
      <MarkdownRenderer text={'$$\n\\int_0^1 x^2\\,dx = \\frac{1}{3}\n$$'} streaming={false} />)
    expect(container.querySelector('.katex-display')).not.toBeNull()
  })

  it('en ødelagt formel vælter IKKE beskeden', () => {
    // `\frac{1` er uafsluttet. Uden throwOnError:false ville KaTeX kaste, og
    // hele svaret ville forsvinde — dét er værre end en grim formel.
    const { container } = render(
      <MarkdownRenderer text={'Før $\frac{1$ midt og teksten efter står stadig.'} streaming={false} />)
    expect(container.textContent).toContain('Før')
    expect(container.textContent).toContain('midt og teksten efter står stadig')
  })

  it('halvfærdig formel under streaming giver ikke en kastet fejl', () => {
    // Mens svaret streames er `$e^{i\pi` en lovlig mellemtilstand.
    const { container } = render(
      <MarkdownRenderer text={'Her kommer den: $e^{i\\pi'} streaming />)
    expect(container.textContent).toContain('Her kommer den')
  })

  it('dollar-tegn der IKKE er matematik forbliver tekst', () => {
    // "koster $5 og $10" må ikke blive en formel. remark-math kræver at
    // dollartegnet ikke følges af mellemrum, og det holder her.
    const { container } = render(
      <MarkdownRenderer text={'Det koster $5 og $10 i alt.'} streaming={false} />)
    expect(container.textContent).toContain('Det koster')
    expect(container.textContent).toContain('i alt')
  })
})
