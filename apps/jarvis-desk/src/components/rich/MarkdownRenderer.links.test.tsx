import { describe, expect, it } from 'vitest'
import { render } from '@testing-library/react'
import { MarkdownRenderer } from './MarkdownRenderer'
import { KODE_REPO } from '../../lib/linkifyRefs'

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
    expect(html('Se https://srvlab.dk nu.')).toContain('link-globe')
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
