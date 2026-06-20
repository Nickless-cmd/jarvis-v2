import { parsePrecision, labelFromAddress } from './location'

describe('parsePrecision', () => {
  it('defaults to off for unknown/null', () => {
    expect(parsePrecision(null)).toBe('off')
    expect(parsePrecision('garbage')).toBe('off')
    expect(parsePrecision('')).toBe('off')
  })
  it('accepts valid values', () => {
    expect(parsePrecision('city')).toBe('city')
    expect(parsePrecision('precise')).toBe('precise')
    expect(parsePrecision('off')).toBe('off')
  })
})

describe('labelFromAddress', () => {
  it('precise → road + city', () => {
    expect(labelFromAddress({ road: 'Toftegårdsvej', city: 'Svendborg' }, true))
      .toBe('Toftegårdsvej, Svendborg')
  })
  it('city precision → city only', () => {
    expect(labelFromAddress({ road: 'Toftegårdsvej', city: 'Svendborg' }, false))
      .toBe('Svendborg')
  })
  it('falls back through town/village/municipality', () => {
    expect(labelFromAddress({ village: 'Vester Skerninge' }, false)).toBe('Vester Skerninge')
  })
  it('empty address → empty string', () => {
    expect(labelFromAddress({}, true)).toBe('')
  })
})
