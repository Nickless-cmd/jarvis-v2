import { describeLayer, describeResult } from './accountData'

const layer = (over: Partial<Parameters<typeof describeLayer>[0]> = {}) =>
  ({ key: 'sessions', label: 'Samtaler', count: 3, unit: 'samtaler', detail: '', ...over }) as never

describe('describeLayer', () => {
  it('boejer entallet', () => {
    expect(describeLayer(layer({ count: 1 }))).toBe('1 samtale')
    expect(describeLayer(layer({ count: 2 }))).toBe('2 samtaler')
  })

  it('siger nul rent ud', () => {
    expect(describeLayer(layer({ count: 0 }))).toBe('0 samtaler')
  })

  // «1.204 hvem du er» giver ikke mening — identitet maales i tegn.
  it('identitet maales i tegn og har sin egen form', () => {
    expect(describeLayer(layer({ key: 'identity', count: 1204, unit: 'tegn' }))).toBe('1.204 tegn')
    expect(describeLayer(layer({ key: 'identity', count: 0 }))).toBe('tom')
  })

  it('taaler skrald i taellingen', () => {
    expect(describeLayer(layer({ count: -5 }))).toBe('0 samtaler')
    expect(describeLayer(layer({ count: NaN as never }))).toBe('0 samtaler')
  })
})

describe('describeResult', () => {
  it('kvitterer for et enkelt lag', () => {
    expect(describeResult({ deleted: 4 })).toBe('Slettede 4.')
  })

  // «Intet skete» skal siges, ikke udelades — ellers tror man knappen var doed.
  it('siger det naar der intet var at slette', () => {
    expect(describeResult({ deleted: 0 })).toBe('Der var ingenting at slette.')
  })

  it('skjuler ikke at noget fejlede', () => {
    expect(describeResult({ deleted: 2, failed: 1 })).toContain('men noget fejlede')
    expect(describeResult({ results: [{ deleted: 3 }, { deleted: 0, failed: 1 }] }))
      .toContain('1 lag fejlede')
  })

  it('lægger sammen paa tvaers af lag', () => {
    expect(describeResult({ results: [{ deleted: 3 }, { deleted: 4 }] })).toBe('Slettede 7 ting.')
  })

  it('er aerlig naar kaldet slet ikke gik igennem', () => {
    expect(describeResult(null)).toContain('kunne ikke')
  })
})
