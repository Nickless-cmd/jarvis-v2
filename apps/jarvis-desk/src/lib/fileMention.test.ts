import { describe, expect, it } from 'vitest'
import { findAktivMention, rangerFiler, indsætMention } from './fileMention'
import type { ProjectFil } from './projectApi'

const f = (rel: string): ProjectFil => ({ path: `/repo/${rel}`, rel, size_bytes: 1 })
const FILER = [
  f('core/tools/simple_tools.py'),
  f('core/tools/simple_tools_web.py'),
  f('core/services/visible_model.py'),
  f('tests/test_simple_tools.py'),
  f('tests/test_visible_model.py'),
  f('README.md'),
]

describe('findAktivMention', () => {
  it('finder mentionen cursoren står i', () => {
    expect(findAktivMention('se @core/too', 12)).toEqual({ start: 3, query: 'core/too' })
  })

  it('åbner ikke på en e-mail', () => {
    // '@' efter et bogstav er ikke en mention — ellers popper listen op
    // midt i «bjorn@srvlab.dk».
    expect(findAktivMention('bjorn@srvlab', 12)).toBeNull()
  })

  it('lukker igen når der kommer mellemrum', () => {
    expect(findAktivMention('@core/x og så', 13)).toBeNull()
  })

  it('virker i starten af feltet og med tom query', () => {
    expect(findAktivMention('@', 1)).toEqual({ start: 0, query: '' })
  })

  it('bruger cursorpositionen, ikke slutningen af teksten', () => {
    // Bjørn retter midt i en linje: kun mentionen ved cursoren tæller.
    expect(findAktivMention('@ab og @cd', 3)).toEqual({ start: 0, query: 'ab' })
  })
})

describe('rangerFiler', () => {
  it('sætter filnavns-træf over sti-træf', () => {
    const r = rangerFiler(FILER, 'simple_tools')
    expect(r[0]?.rel).toBe('core/tools/simple_tools.py')
  })

  it('matcher forkortelser som subsekvens', () => {
    expect(rangerFiler(FILER, 'visiblemodel')[0]?.rel).toBe('core/services/visible_model.py')
  })

  it('sætter kilden over testen ved subsekvens-træf', () => {
    // Mod det ægte indeks gav 'visiblemodel' tests/test_visible_model.py
    // øverst, alene fordi stien var kortere. Et træf der starter tidligt i
    // FILNAVNET skal veje tungere end en kort sti.
    const r = rangerFiler(FILER, 'visiblemodel', 2)
    expect(r[0]?.rel).toBe('core/services/visible_model.py')
  })

  it('giver hele listen ved tom query', () => {
    expect(rangerFiler(FILER, '', 3)).toHaveLength(3)
  })

  it('returnerer intet når tegnene ikke findes i rækkefølge', () => {
    expect(rangerFiler(FILER, 'zzqq')).toEqual([])
  })
})

describe('indsætMention', () => {
  it('erstatter mentionen og sætter cursoren efter mellemrummet', () => {
    const m = findAktivMention('se @core/too', 12)!
    const r = indsætMention('se @core/too', m, 'core/tools/simple_tools.py')
    expect(r.tekst).toBe('se @core/tools/simple_tools.py ')
    expect(r.caret).toBe(r.tekst.length)
  })

  it('bevarer tekst efter mentionen uden at fordoble mellemrummet', () => {
    const m = findAktivMention('@co og resten', 3)!
    const r = indsætMention('@co og resten', m, 'README.md')
    expect(r.tekst).toBe('@README.md og resten')
    expect(r.tekst.slice(r.caret)).toBe(' og resten')
  })
})
