import { describe, expect, it } from 'vitest'
import { fireEvent, render } from '@testing-library/react'
import { MarkdownRenderer } from './MarkdownRenderer'
import { KODE_REPO } from '../../lib/linkifyRefs'
import { SIDE_OPGAVE_AABN_EVENT } from '../../lib/sideOpgaveHighlight'

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

  it('klik åbner panelet via event i stedet for ekstern navigation', () => {
    const modtaget: string[] = []
    const lyt = (e: Event) => {
      modtaget.push((e as CustomEvent<{ id: string }>).detail.id)
    }
    window.addEventListener(SIDE_OPGAVE_AABN_EVENT, lyt)
    try {
      const { container } = render(
        <MarkdownRenderer text="Se `side-4978e79e57` her." streaming={false} />,
      )
      const a = container.querySelector('a')
      expect(a).not.toBeNull()
      fireEvent.click(a!)
      expect(modtaget).toEqual(['side-4978e79e57'])
    } finally {
      window.removeEventListener(SIDE_OPGAVE_AABN_EVENT, lyt)
    }
  })
})
