import { describe, it, expect } from 'vitest'
import { lukAabneMarkeringer, stabilizeStreamingMarkdown } from './streamingMarkdown'

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

describe('lukAabneMarkeringer — den halve markering (14/11-2026)', () => {
  it('lukker en fed-markering der er ved at blive skrevet', () => {
    // Målt: uden lukningen stod der rå `**` i fladen mens svaret løb.
    expect(lukAabneMarkeringer('Her er en **vigtig pointe')).toBe('Her er en **vigtig pointe**')
  })

  it('rører IKKE en komplet markering', () => {
    const md = 'Her er en **vigtig pointe** der er lukket'
    expect(lukAabneMarkeringer(md)).toBe(md)
  })

  it('lukker inline-kode', () => {
    expect(lukAabneMarkeringer('kør `npm test')).toBe('kør `npm test`')
  })

  it('tæller ikke markeringer inde i en kode-fence', () => {
    // Kode skal vises som den er skrevet. Uden fence-værnet ville de to
    // stjerner i eksemplet blive talt med og give en falsk lukning.
    const md = '```\nconst a = "**"\n```'
    expect(lukAabneMarkeringer(md)).toBe(md)
  })

  it('rører ikke en enkelt stjerne eller underscore', () => {
    // Dansk prosa bruger `*` og `_` uden at mene markdown. En gættet lukning
    // ville gøre skade i stedet for at undgå den.
    const md = 'en note om 2 * 3 og snake_case_navn'
    expect(lukAabneMarkeringer(md)).toBe(md)
  })

  it('en tekst uden markeringer er uændret', () => {
    const md = 'helt almindelig prosa uden formatering'
    expect(lukAabneMarkeringer(md)).toBe(md)
  })

  it('stabilizeStreamingMarkdown lukker markeringen — og kun dér', () => {
    // Kontrakten: reparationen hører til streaming-vejen. En FÆRDIG tekst med
    // en halv markering skal se rå ud, for der er det en rigtig fejl.
    const halv = 'Her er en **pointe der ikke blev lukket'
    expect(stabilizeStreamingMarkdown(halv)).toBe(`${halv}**`)
  })
})
