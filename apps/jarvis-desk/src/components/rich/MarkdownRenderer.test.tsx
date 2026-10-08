import { describe, it, expect, vi } from 'vitest'
import { render, fireEvent } from '@testing-library/react'
import { MarkdownRenderer } from './MarkdownRenderer'

describe('MarkdownRenderer', () => {
  it('opens a safe link from the browser UI', () => {
    vi.stubGlobal('jarvisDesk', undefined)
    const open = vi.fn(() => ({}))
    vi.stubGlobal('open', open)
    const { container } = render(<MarkdownRenderer text="[docs](https://example.com/docs)" streaming={false} />)
    fireEvent.click(container.querySelector('a')!)
    expect(open).toHaveBeenCalledWith('https://example.com/docs', '_blank', 'noopener,noreferrer')
    vi.unstubAllGlobals()
  })
  it('renders bold markdown as <strong>', () => {
    const { container } = render(<MarkdownRenderer text="**fed**" streaming={false} />)
    expect(container.querySelector('strong')?.textContent).toBe('fed')
  })
  it('does NOT render raw HTML (XSS guard)', () => {
    const { container } = render(<MarkdownRenderer text={'<img src=x onerror=alert(1)>'} streaming={false} />)
    expect(container.querySelector('img')).toBeNull()
  })
  it('blocks javascript: links (renders without href)', () => {
    const { container } = render(<MarkdownRenderer text={'[klik](javascript:alert(1))'} streaming={false} />)
    const a = container.querySelector('a')
    expect(a?.getAttribute('href') ?? null).toBeNull()
  })
  // 2026-06-13: remarkBreaks FJERNET (forstærkede malformede tabeller til
  // <br>-mure = "kastet ind"). Enkelt-\n giver nu IKKE <br> — vi stoler på
  // korrekte blanklinjer + backend-normalizer i stedet. Denne test vogter at
  // remarkBreaks ikke smutter tilbage.
  it('enkelt-newline giver IKKE <br> (remarkBreaks fjernet)', () => {
    const { container } = render(<MarkdownRenderer text={'Første linje.\nAnden linje.'} streaming={false} />)
    expect(container.querySelector('br')).toBeNull()
  })
  // Blanklinje-adskilte afsnit bliver separate <p>.
  it('blanklinje-adskilte afsnit bliver separate <p>', () => {
    const { container } = render(<MarkdownRenderer text={'Første.\n\nAnden.'} streaming={false} />)
    expect(container.querySelectorAll('p').length).toBe(2)
  })
  // Lister må IKKE få indsat spuriøse <br> — de er block-konstruktioner.
  it('liste-punkter forbliver separate <li>', () => {
    const { container } = render(<MarkdownRenderer text={'- et\n- to\n- tre'} streaming={false} />)
    expect(container.querySelectorAll('li').length).toBe(3)
  })
  it.each([false, true])('viser 1 · punkterne som én liste under streaming=%s', (streaming) => {
    const text = '**1 · Skill-testen.**\nDen er stadig rød.\n\n**2 · Doc-drift.** To kommentarer er forældede.'
    const { container } = render(<MarkdownRenderer text={text} streaming={streaming} />)
    expect(container.querySelectorAll('ol')).toHaveLength(1)
    expect(container.querySelectorAll('li')).toHaveLength(2)
    expect(container.querySelector('li')?.textContent).toContain('Den er stadig rød.')
  })
})
