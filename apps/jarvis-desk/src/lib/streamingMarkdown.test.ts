import { describe, it, expect } from 'vitest'
import { stabilizeStreamingMarkdown } from './streamingMarkdown'

describe('stabilizeStreamingMarkdown', () => {
  it('holds back an unclosed code fence', () => {
    const out = stabilizeStreamingMarkdown('tekst\n```js\nconst x')
    expect(out).toBe('tekst')
  })
  it('renders a closed code fence fully', () => {
    const md = 'tekst\n```js\nconst x = 1\n```'
    expect(stabilizeStreamingMarkdown(md)).toBe(md)
  })
  it('passes through plain text unchanged', () => {
    expect(stabilizeStreamingMarkdown('bare tekst')).toBe('bare tekst')
  })
  it('klipper ikke prosa med inline backticks', () => {
    const md = 'Her er et eksempel. Brug ``` for kode. Det er smart.'
    expect(stabilizeStreamingMarkdown(md)).toBe(md)
  })
  it('tre backticks inde i en fire-backtick fence lukker den ikke', () => {
    const md = '````md\nHer viser jeg ```\nkode\n````'
    expect(stabilizeStreamingMarkdown(md)).toBe(md)
  })
  it('genkender både åbne og lukkede tilde-fences', () => {
    expect(stabilizeStreamingMarkdown('Før\n~~~js\nconst x = 1')).toBe('Før')
    const lukket = 'Før\n~~~js\nconst x = 1\n~~~'
    expect(stabilizeStreamingMarkdown(lukket)).toBe(lukket)
  })
  it('kortere eller forkert tegn kan ikke lukke en fence', () => {
    expect(stabilizeStreamingMarkdown('Før\n````js\n```\n~~~')).toBe('Før\n````js\n```\n````')
  })
  it('viser afsluttede linjer i en åben fence uden den halve linje', () => {
    expect(stabilizeStreamingMarkdown('Før\n```ts\nconst a = 1\nconst b')).toBe('Før\n```ts\nconst a = 1\n```')
    expect(stabilizeStreamingMarkdown('Før\n```ts\nconst a = 1\nconst b = 2\n')).toBe('Før\n```ts\nconst a = 1\nconst b = 2\n```')
    expect(stabilizeStreamingMarkdown('Før\n~~~~js\nconst x = 1\nrest')).toBe('Før\n~~~~js\nconst x = 1\n~~~~')
  })
})

/* ── Verifikation af spec punkt 9's kendte begrænsning (30/9-2026) ──────────
 *
 * «En patologisk enkelt lang linje falder tilbage til den almindelige
 * hale-vej.» Speccen siger selv: verificér at fallback'en faktisk udløses —
 * en dokumenteret begrænsning der ikke virker er værre end en udokumenteret,
 * fordi ingen leder efter den.
 */
describe('den kendte begrænsning: en fence uden en eneste afsluttet linje', () => {
  const T = '```'

  it('falder tilbage til hale-vejen — fencen holdes HELT tilbage', () => {
    // Åbneren er kommet, men første linje er ikke afsluttet endnu. Der er
    // intet at vise inde i blokken, så hele fencen holdes tilbage.
    const md = `prosa før\n${T}js\nconst x = "en meget lang linje der endnu ikke er afsluttet`
    const ud = stabilizeStreamingMarkdown(md)
    expect(ud).toBe('prosa før')
    expect(ud).not.toContain(T)
  })

  it('og så snart ÉN linje er afsluttet, skifter den til den frosne vej', () => {
    // Kontrollen: uden den ville testen ovenfor også bestå hvis fallback'en
    // var den eneste vej der fandtes.
    const md = `prosa før\n${T}js\nconst x = 1\nconst y = `
    const ud = stabilizeStreamingMarkdown(md)
    expect(ud).toContain('const x = 1')
    expect(ud).not.toContain('const y =')     // den halve linje vises ikke
    expect(ud.endsWith(T)).toBe(true)          // midlertidig lukkemarkør
  })
})
