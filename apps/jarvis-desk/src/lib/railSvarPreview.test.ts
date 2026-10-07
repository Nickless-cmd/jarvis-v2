import { describe, it, expect } from 'vitest'
import { svarPreview, svarTilAnker, klipTegn, MAX_TEGN } from './railSvarPreview'

/**
 * Skinnens etiket svarer i dag paa «hvad spurgte jeg om», ikke paa «fik jeg
 * det jeg skulle bruge» — og det sidste er som regel dét man leder efter naar
 * man scroller tilbage (spec punkt 3.2).
 */

const tekst = (s: string) => [{ type: 'text', text: s }]

describe('svar-preview', () => {
  it('tager op til tre linjer og samler dem', () => {
    expect(svarPreview(tekst('en\nto\ntre\nfire'))).toBe('en to tre')
  })

  it('springer et KODEHEGN og dets indhold over', () => {
    // Et svar der aabner med ```bash gav ellers uddraget «bash» — vaerre end
    // ingenting.
    expect(svarPreview(tekst('```bash\nls -la\ncd /tmp\n```\nDet ligger i /tmp nu.')))
      .toBe('Det ligger i /tmp nu.')
  })

  it('et UAFSLUTTET hegn sluger ikke resten', () => {
    // En stream der er klippet over midt i et hegn er almindelig. Havde vi
    // ikke linjen foer hegnet, ville preview'et blive tomt.
    expect(svarPreview(tekst('Her er den:\n```py\nprint(1)'))).toBe('Her er den:')
  })

  it('tabel-linjer og streger er struktur, ikke indhold', () => {
    expect(svarPreview(tekst('| a | b |\n|---|---|\n---\nSvaret er 42.'))).toBe('Svaret er 42.')
  })

  it('markdown-markoerer ryddes af linjens begyndelse', () => {
    expect(svarPreview(tekst('## Overskrift\n- punkt et\n> citat'))).toBe('Overskrift punkt et citat')
  })

  it('et tomt eller rent kode-svar giver tom streng — ikke et fragment', () => {
    expect(svarPreview(tekst(''))).toBe('')
    expect(svarPreview(tekst('   \n\n '))).toBe('')
    expect(svarPreview(tekst('```\nkun kode\n```'))).toBe('')
  })

  it('en ren streng virker som blokke', () => {
    expect(svarPreview('bare tekst')).toBe('bare tekst')
    expect(svarPreview(null)).toBe('')
    expect(svarPreview(undefined)).toBe('')
  })

  it('klipper paa TEGN, saa et emoji aldrig braekkes over', () => {
    // Emojien skal ligge PRAECIS paa klippet, ellers maaler testen ingenting:
    // med maks 10 klippes der efter 9 tegn, saa emojien staar paa plads 9
    // (0-indekseret 8). I UTF-16 fylder den to enheder — et `slice(0, 9)`
    // ville tage den foerste og efterlade en ensom hoej surrogat.
    // Mutationskoersel: `Array.from` -> `split('')` bestod med emojien ét tegn
    // laengere fremme. Den er flyttet hertil.
    const s = 'a'.repeat(8) + '👍' + 'b'.repeat(20)
    expect(s.slice(0, 9)).toMatch(/[\uD800-\uDBFF]$/)   // saadan ser fejlen ud

    const ud = klipTegn(s, 10)
    // En ENSOM surrogat — ikke bare «en surrogat»: 👍 ER et surrogat-par, saa
    // et forbud mod tegnet selv ville ogsaa afvise det rigtige svar.
    const ensom = /[\uD800-\uDBFF](?![\uDC00-\uDFFF])|(?<![\uD800-\uDBFF])[\uDC00-\uDFFF]/
    expect(ud).not.toMatch(ensom)
    expect(ud).toBe('a'.repeat(8) + '👍' + '…')
    expect(Array.from(ud)).toHaveLength(10)
  })

  it('klipper ikke noget der er kort nok', () => {
    expect(klipTegn('kort', 10)).toBe('kort')
    expect(klipTegn('', 10)).toBe('')
  })

  it('samlet loft paa 120 tegn', () => {
    const lang = Array.from({ length: 5 }, (_, i) => `linje ${i} ${'x'.repeat(40)}`).join('\n')
    expect(Array.from(svarPreview(lang)).length).toBeLessThanOrEqual(MAX_TEGN)
  })
})

describe('svaret der hører til et anker', () => {
  const B = [
    { id: 'u1', role: 'user', content: tekst('spørgsmål et') },
    { id: 'a1', role: 'assistant', content: tekst('svar et') },
    { id: 'u2', role: 'user', content: tekst('spørgsmål to') },
    { id: 'a2', role: 'assistant', content: tekst('svar to') },
  ]

  it('tager svaret EFTER ankeret, ikke før', () => {
    expect(svarTilAnker(B, 'u1')).toBe('svar et')
    expect(svarTilAnker(B, 'u2')).toBe('svar to')
  })

  it('stopper ved næste bruger-besked', () => {
    // Uden stoppet ville preview'et for tur 1 indeholde tur 2's svar, og
    // skinnen ville sige det samme hele vejen ned.
    expect(svarTilAnker(B, 'u1')).not.toContain('svar to')
  })

  it('samler flere assistent-beskeder i samme tur', () => {
    const delt = [
      { id: 'u1', role: 'user', content: tekst('spørg') },
      { id: 'a1', role: 'assistant', content: tekst('første del') },
      { id: 'a2', role: 'assistant', content: tekst('anden del') },
      { id: 'u2', role: 'user', content: tekst('næste') },
    ]
    expect(svarTilAnker(delt, 'u1')).toBe('første del anden del')
  })

  it('en tur uden svar giver tom streng', () => {
    expect(svarTilAnker([{ id: 'u1', role: 'user', content: tekst('spørg') }], 'u1')).toBe('')
  })

  it('et ukendt anker giver tom streng og ikke et crash', () => {
    expect(svarTilAnker(B, 'findes-ikke')).toBe('')
  })

  it('et anker der PEGER PÅ et svar tager det svar med', () => {
    // Komprimerings- og fastgjorte ankre kan pege på en assistent-besked.
    expect(svarTilAnker(B, 'a1')).toBe('svar et')
  })
})
