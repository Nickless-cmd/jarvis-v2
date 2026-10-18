import { parsePrecision, labelFromAddress, precisionLabel, shouldUseGps } from './location'

describe('parsePrecision', () => {
  it('defaults to off for unknown/null', () => {
    expect(parsePrecision(null)).toBe('off')
    expect(parsePrecision('garbage')).toBe('off')
    expect(parsePrecision('')).toBe('off')
  })
  it('accepts valid values', () => {
    expect(parsePrecision('city')).toBe('city')
    expect(parsePrecision('area')).toBe('area')
    expect(parsePrecision('now')).toBe('now')
    expect(parsePrecision('precise')).toBe('precise')
    expect(parsePrecision('background')).toBe('background')
    expect(parsePrecision('off')).toBe('off')
  })
})

describe('location precision policy', () => {
  it('bruger GPS på ALLE delende niveauer — IP er kun reserve', () => {
    // Målt tre gange som forkert by (Taastrup 24/9, København 7/10, Ålborg
    // 18/10) mens Bjørn var i Svendborg: bag CGNAT kan et IP-opslag ikke
    // finde byen. Derfor må 'city'/'area' ikke længere springe GPS over.
    expect(shouldUseGps('city')).toBe(true)
    expect(shouldUseGps('area')).toBe(true)
    expect(shouldUseGps('precise')).toBe(true)
    expect(shouldUseGps('now')).toBe(true)
    expect(shouldUseGps('background')).toBe(true)
    expect(shouldUseGps('off')).toBe(false)
  })

  it('has user-facing labels for all precision levels', () => {
    expect(precisionLabel('off')).toBe('Fra')
    expect(precisionLabel('city')).toBe('By')
    expect(precisionLabel('area')).toBe('Område')
    expect(precisionLabel('now')).toBe('Præcis nu')
    expect(precisionLabel('precise')).toBe('Mens appen er åben')
    expect(precisionLabel('background')).toBe('I baggrund')
  })
})

describe('labelFromAddress', () => {
  it('precise → road + city', () => {
    expect(labelFromAddress({ road: 'Toftegårdsvej', city: 'Svendborg' }, true))
      .toBe('Toftegårdsvej, Svendborg')
  })
  it('precise → bruger pedestrian/neighbourhood når road mangler', () => {
    expect(labelFromAddress({ pedestrian: 'Gågaden', city: 'Svendborg' }, true))
      .toBe('Gågaden, Svendborg')
    expect(labelFromAddress({ neighbourhood: 'Centrum', town: 'Svendborg' }, true))
      .toBe('Centrum, Svendborg')
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
