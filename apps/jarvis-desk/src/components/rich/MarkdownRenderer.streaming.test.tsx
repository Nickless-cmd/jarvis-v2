import { describe, it, expect, vi } from 'vitest'
import { render } from '@testing-library/react'

// Tæl hvor mange gange hver blok faktisk parses (= react-markdown kaldes med den).
const parset = vi.hoisted(() => new Map<string, number>())
vi.mock('react-markdown', async (orig) => {
  const ægte = (await orig<typeof import('react-markdown')>()).default
  return {
    default: (props: { children: string }) => {
      parset.set(props.children, (parset.get(props.children) ?? 0) + 1)
      return ægte(props as never)
    },
  }
})

import { MarkdownRenderer } from './MarkdownRenderer'

const afsnit = (i: number) => `## Afsnit ${i}\n\nTekst ${i} med **fed**, \`kode\` og [et link](https://x.dk).\n\n- et ${i}\n\n- to med \`sti.ts:${i}\`\n\n| k | v |\n|---|---|\n| load | ${i} |\n\n\`\`\`ts\nconst a${i} = 1\n\nconst b${i} = 2\n\`\`\`\n\n`
const doc = Array.from({ length: 12 }, (_, i) => afsnit(i)).join('') + 'Slutafsnit.'

describe('MarkdownRenderer under streaming', () => {
  it('giver PRÆCIS samme HTML som ét samlet parse', () => {
    // Et samlet parse lægger linjeskift-tekstnoder MELLEM blokelementerne;
    // de delte blokke gør ikke. Det er mellemrum mellem blokke — usynligt —
    // så det fjernes før sammenligningen. Alt andet skal være identisk.
    const norm = (h: string) => h.replace(/>\s+</g, '><')
    const del = render(<MarkdownRenderer text={doc} streaming />).container.innerHTML
    const hel = render(<MarkdownRenderer text={doc} streaming={false} />).container.innerHTML
    expect(norm(del)).toBe(norm(hel))
  })

  it('en færdig blok parses ÉN gang — kun den levende hale parses igen', () => {
    parset.clear()
    const { rerender } = render(<MarkdownRenderer text="" streaming />)
    for (let n = 30; n <= doc.length; n += 30) rerender(<MarkdownRenderer text={doc.slice(0, n)} streaming />)
    const foersteBlok = '## Afsnit 0\n'
    expect(parset.get(foersteBlok)).toBe(1)
    // En færdig blok parses højst TO gange, uanset antallet af deltaer (her
    // ~250). Den ekstra gang er afgrænset: mens en kodeblok står åben, holder
    // stabilizeStreamingMarkdown den tilbage og trimmer tomme linjer, så blokken
    // foran et øjeblik er den levende hale. Før 19/9 blev hver blok parset ved
    // HVER delta.
    const flest = Math.max(...[...parset.entries()].filter(([md]) => md.endsWith('\n')).map(([, n]) => n))
    expect(flest).toBeLessThanOrEqual(2)
  })

  it('tiden pr. render vokser IKKE med teksten (regressionsvagt)', () => {
    // Før 19/9-2026: 2,9 ms → 27,5 ms pr. render hen over et svar (×9,4).
    // Forholdet er maskine-uafhængigt; grænsen ×3 fanger den kvadratiske vækst.
    const lang = Array.from({ length: 30 }, (_, i) => afsnit(i)).join('')
    const { rerender } = render(<MarkdownRenderer text="" streaming />)
    const tider: number[] = []
    for (let n = 24; n < lang.length; n += 24) {
      const a = performance.now()
      rerender(<MarkdownRenderer text={lang.slice(0, n)} streaming />)
      tider.push(performance.now() - a)
    }
    const snit = (xs: number[]) => xs.reduce((s, x) => s + x, 0) / xs.length
    const tiendedel = Math.floor(tider.length / 10)
    const start = snit(tider.slice(tiendedel, 2 * tiendedel))
    const slut = snit(tider.slice(-tiendedel))
    expect(slut / start).toBeLessThan(3)
  }, 120000)
})
