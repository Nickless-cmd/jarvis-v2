import { describe, expect, it } from 'vitest'
import { fireEvent, render } from '@testing-library/react'
import { MarkdownRenderer } from './MarkdownRenderer'
import { KODE_REPO } from '../../lib/linkifyRefs'
import { REF_AABN_EVENT } from '../../lib/refAabn'

/** Ægte render — ikke bare mdast. Et link der findes i træet men ikke i
 *  DOM'en er ikke et link Bjørn kan klikke på. */
function html(md: string): string {
  return render(<MarkdownRenderer text={md} streaming={false} />).container.innerHTML
}

describe('MarkdownRenderer — referencer er klikbare', () => {
  it('en commit-hash i backticks bliver et rigtigt <a> til GitHub', () => {
    const ud = html('Commit `442b3bc85` er inde.')
    expect(ud).toContain(`href="https://github.com/${KODE_REPO}/commit/442b3bc85"`)
  })

  it('en URL i backticks bliver et rigtigt <a>', () => {
    const ud = html('Se `https://srvlab.dk` her.')
    expect(ud).toContain('href="https://srvlab.dk"')
  })

  it('en URL i prosa er stadig et link', () => {
    expect(html('Se https://srvlab.dk nu.')).toContain('href="https://srvlab.dk"')
  })

  it('eksterne links får globus-ikonet foran', () => {
    const ud = html('Se https://srvlab.dk nu.')
    expect(ud).toContain('link-globe')
    expect(ud).not.toContain('link-github')
  })

  it('commit-hashes får GitHub-ikon i stedet for globus', () => {
    const ud = html('Commit 442b3bc85 er inde.')
    expect(ud).toContain('link-github')
    expect(ud).not.toContain('link-globe')
    expect(ud).toContain(`href="https://github.com/${KODE_REPO}/commit/442b3bc85"`)
  })

  it('hash-badgen beholder sin kode-form indeni linket', () => {
    const ud = html('Commit `442b3bc85` er inde.')
    expect(ud).toMatch(/<a[^>]*>.*<code[^>]*>442b3bc85<\/code>/)
  })

  it('kodeblokke forbliver kode — ingen link inde i en kommando', () => {
    const ud = html('```bash\ngit show 442b3bc85\n```')
    expect(ud).not.toContain('/commit/442b3bc85')
  })
})

describe('MarkdownRenderer — side-opgave-referencer', () => {
  it('en side-opgave-reference får ListTodo-ikonet, ikke globus eller GitHub', () => {
    const ud = html('Se `side-4978e79e57` her.')
    expect(ud).toContain('link-todo')
    expect(ud).toContain('ref-link--sideopgave')
    expect(ud).not.toContain('link-globe')
    expect(ud).not.toContain('link-github')
  })

  it('href bærer id\'et — ellers kan klikket ikke finde opgaven', () => {
    expect(html('Se `side-4978e79e57` her.'))
      .toContain('href="#side-opgave=side-4978e79e57"')
  })

  it('klik sender en reference-event i stedet for ekstern navigation', () => {
    // 27/10-2026: kontrakten er ændret. MarkdownRenderer kender ikke fladerne —
    // den sender ÉN event med (kind, vaerdi), og `RefAabnHost` i App oversætter
    // den til det rette panel. Testen her vogter den kontrakt; flade-valget
    // testes i RefAabnHost.test.tsx.
    const modtaget: { kind: string; vaerdi: string }[] = []
    const lyt = (e: Event) => {
      modtaget.push((e as CustomEvent<{ kind: string; vaerdi: string }>).detail)
    }
    window.addEventListener(REF_AABN_EVENT, lyt)
    try {
      const { container } = render(
        <MarkdownRenderer text="Se `side-4978e79e57` her." streaming={false} />,
      )
      const a = container.querySelector('a')
      expect(a).not.toBeNull()
      fireEvent.click(a!)
      expect(modtaget).toEqual([{ kind: 'sideopgave', vaerdi: 'side-4978e79e57' }])
    } finally {
      window.removeEventListener(REF_AABN_EVENT, lyt)
    }
  })
})

describe('MarkdownRenderer — de øvrige referencetyper (27/10-2026)', () => {
  // Bjørn: «asg-…, wt-…, wake-…, agent/asg-…, run-… og filnavne bør osse have
  // ikon og være klikbare». Hver type får sit eget ikon — ellers kan man ikke
  // se på badgen hvad man klikker på.
  const tilfaelde: [string, string, string][] = [
    ['asg-d82c9e2189ec4b8e', 'agent', 'link-agent'],
    ['agent/asg-deb93ebf820f412d', 'agent', 'link-agent'],
    ['wt-2fc178d6675d4c51', 'worktree', 'link-worktree'],
    ['wake-5bd95f0d9b', 'wake', 'link-wake'],
    ['run-870a741adb4e4283', 'run', 'link-run'],
    ['sideOpgaveHighlight.ts', 'fil', 'link-fil'],
  ]

  for (const [id, kind, ikon] of tilfaelde) {
    it(`${id} bliver et link med ${ikon}-ikon`, () => {
      const ud = html('Se `' + id + '` her.')
      expect(ud).toContain(`href="#${kind === 'sideopgave' ? 'side-opgave' : kind}=`)
      expect(ud).toContain(ikon)
      expect(ud).not.toContain('link-globe')
    })

    it(`${id} sender kind=${kind} ved klik`, () => {
      const modtaget: { kind: string; vaerdi: string }[] = []
      const lyt = (e: Event) => modtaget.push((e as CustomEvent<{ kind: string; vaerdi: string }>).detail)
      window.addEventListener(REF_AABN_EVENT, lyt)
      try {
        const { container } = render(<MarkdownRenderer text={'Se `' + id + '` her.'} streaming={false} />)
        fireEvent.click(container.querySelector('a')!)
        expect(modtaget[0]?.kind).toBe(kind)
      } finally {
        window.removeEventListener(REF_AABN_EVENT, lyt)
      }
    })
  }

  it('agent/asg-… bevarer kun asg-id\'et som værdi', () => {
    const modtaget: { kind: string; vaerdi: string }[] = []
    const lyt = (e: Event) => modtaget.push((e as CustomEvent<{ kind: string; vaerdi: string }>).detail)
    window.addEventListener(REF_AABN_EVENT, lyt)
    try {
      const { container } = render(
        <MarkdownRenderer text={'Se `agent/asg-deb93ebf820f412d` her.'} streaming={false} />,
      )
      fireEvent.click(container.querySelector('a')!)
      expect(modtaget[0]?.vaerdi).toBe('asg-deb93ebf820f412d')
    } finally {
      window.removeEventListener(REF_AABN_EVENT, lyt)
    }
  })

  it('en commit-hash bliver IKKE forvekslet med et asg-id', () => {
    expect(html('Commit `442b3bc85` er inde.')).toContain('/commit/442b3bc85')
  })

  it('en version som 0.6.270 bliver ikke et fil-link', () => {
    expect(html('Version `0.6.270` er ude.')).not.toContain('href="#fil=')
  })
})
