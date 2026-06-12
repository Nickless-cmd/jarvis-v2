import { describe, it, expect } from 'vitest'
import { render } from '@testing-library/react'
import { MarkdownRenderer } from './MarkdownRenderer'

describe('MarkdownRenderer', () => {
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
  // Root-cause regression: Jarvis emitter ofte afsnit adskilt af ÉT newline.
  // Uden hard-break-håndtering kollapser CommonMark dem til ét løbende afsnit
  // ("kastet ind"). remark-breaks → enkelt-\n bliver <br>, så linjerne adskilles.
  it('enkelt-newline bliver hårdt linjeskift (ikke kollapset prosa)', () => {
    const { container } = render(<MarkdownRenderer text={'Første linje.\nAnden linje.'} streaming={false} />)
    expect(container.querySelector('br')).not.toBeNull()
  })
  // Lister må IKKE få indsat spuriøse <br> — de er block-konstruktioner.
  it('liste-punkter forbliver separate <li>', () => {
    const { container } = render(<MarkdownRenderer text={'- et\n- to\n- tre'} streaming={false} />)
    expect(container.querySelectorAll('li').length).toBe(3)
  })
})
