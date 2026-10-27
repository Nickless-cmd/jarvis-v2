import { describe, expect, it } from 'vitest'
import { unified } from 'unified'
import remarkParse from 'remark-parse'
import remarkGfm from 'remark-gfm'
import {
  KODE_REPO, commitUrl, isCommitHref, isSideOpgaveHref, linkifyRefs, referenceUrl,
  sideOpgaveHref, sideOpgaveIdFromHref,
} from './linkifyRefs'

/** Kør den ægte kæde (parse + gfm + vores plugin) og returnér alle links.
 *  `parse()` kører KUN parseren — transformere skal køres med `runSync`,
 *  ellers tester man parseren og ikke pluginnet. */
function trae(md: string) {
  const processor = unified().use(remarkParse).use(remarkGfm).use(linkifyRefs)
  return processor.runSync(processor.parse(md))
}

function links(md: string): string[] {
  const fundet: string[] = []
  const gaa = (n: { type?: string; url?: string; children?: unknown[] }): void => {
    if (n.type === 'link' && n.url) fundet.push(n.url)
    ;(n.children ?? []).forEach((b) => gaa(b as never))
  }
  gaa(trae(md) as never)
  return fundet
}

describe('linkifyRefs — referencer bliver klikbare', () => {
  it('gør en commit-hash i backticks til et GitHub-commit-link', () => {
    expect(links('Commit `442b3bc85` er inde.')).toEqual([
      `https://github.com/${KODE_REPO}/commit/442b3bc85`,
    ])
  })

  it('gør en URL i backticks til et link — remark-gfm autolinker kun prosa', () => {
    // Målt 25/10-2026: `https://srvlab.dk` blev inlineCode UDEN link, mens
    // den samme URL i prosa blev autolinked. Det var hele forskellen.
    expect(links('Se `https://srvlab.dk` her.')).toEqual(['https://srvlab.dk'])
  })

  it('gør en fritstående commit-hash klikbar i chattekst', () => {
    expect(links('Deployet som 442b3bc85 og klar.')).toEqual([
      `https://github.com/${KODE_REPO}/commit/442b3bc85`,
    ])
  })

  it('forveksler ikke farver, UUID-led eller rene hex-ord med commits', () => {
    expect(links('Farve #a371f7, id 442b3bc8-1234 og ordet deadbeef.')).toEqual([])
  })

  it('genkender GitHub commit-links på tværs af repositories til ikonvalg', () => {
    expect(isCommitHref('https://github.com/openai/codex/commit/442b3bc85')).toBe(true)
    expect(isCommitHref('https://github.com/openai/codex/issues/442b3bc85')).toBe(false)
  })

  it('bevarer badge-formen: linket bærer stadig inlineCode indeni', () => {
    const tree = trae('`442b3bc85`') as unknown as { children: unknown[] }
    const p = tree.children[0] as {
      children: Array<{ type: string; children?: Array<{ type: string }> }>
    }
    const a = p.children[0]
    expect(a?.type).toBe('link')
    expect(a?.children?.[0]?.type).toBe('inlineCode')
  })

  it('rører ikke en hash der ikke er en hash', () => {
    expect(links('Brug `deadbeefzz` og `min-variabel` som navne.')).toEqual([])
  })

  it('rører ikke kodeblokke, hvor en hash kan være en del af en kommando', () => {
    const md = '```bash\ngit show 442b3bc85\n```'
    expect(links(md)).toEqual([])
  })

  it('rører ikke prosa-links den allerede har fanget', () => {
    // Ingen dubletter: gfm laver linket, vores plugin skal ikke lave et mere.
    expect(links('Se https://srvlab.dk nu.')).toEqual(['https://srvlab.dk'])
  })

  it('referenceUrl afviser tomt og mellemrum', () => {
    expect(referenceUrl('')).toBeNull()
    expect(referenceUrl('  ')).toBeNull()
    expect(referenceUrl('to ord')).toBeNull()
  })

  it('commitUrl peger på det repo git selv peger på', () => {
    expect(commitUrl('abc1234')).toBe(`https://github.com/${KODE_REPO}/commit/abc1234`)
  })
})

describe('linkifyRefs — side-opgave-referencer', () => {
  // 27/10-2026: agenten skrev `return \`#side-opgave=\`` og smed argumentet
  // væk. Et link blev dannet, men id'et manglede, så isSideOpgaveHref afviste
  // det og klikket gjorde ingenting. En test der kun tjekkede «der kom et
  // link» var grøn hele tiden. Derfor tjekker disse id'et, ikke linket.
  it('sideOpgaveHref bærer id\'et — det var den faktiske fejl', () => {
    expect(sideOpgaveHref('side-4978e79e57')).toBe('#side-opgave=side-4978e79e57')
  })

  it('en side-opgave-reference bliver et link med id\'et intakt', () => {
    expect(referenceUrl('side-4978e79e57')).toBe('#side-opgave=side-4978e79e57')
    expect(links('Se `side-4978e79e57` her.')).toEqual(['#side-opgave=side-4978e79e57'])
  })

  it('isSideOpgaveHref og sideOpgaveIdFromHref læser samme form', () => {
    const href = sideOpgaveHref('side-4978e79e57')
    expect(isSideOpgaveHref(href)).toBe(true)
    expect(sideOpgaveIdFromHref(href)).toBe('side-4978e79e57')
  })

  it('afviser id-format der ikke er en side-opgave', () => {
    expect(isSideOpgaveHref('#side-opgave=')).toBe(false)
    expect(sideOpgaveIdFromHref('#side-opgave=')).toBeNull()
    expect(isSideOpgaveHref('#side-opgave=side-XYZ')).toBe(false)
    expect(referenceUrl('side-')).toBeNull()
  })
})
