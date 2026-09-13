import { availableLocales, normalizeLocale, translate } from './i18n'

describe('mobile i18n', () => {
  it('normaliserer sprogkoder til understøttede locale-basics', () => {
    expect(normalizeLocale('en-US')).toBe('en')
    expect(normalizeLocale('da-DK')).toBe('da')
    expect(normalizeLocale('fr-FR')).toBe('da')
    expect(normalizeLocale('auto')).toBe('auto')
  })

  it('oversætter med dansk fallback og interpolation', () => {
    expect(translate('en', 'settings.title')).toBe('Settings')
    expect(translate('da', 'settings.title')).toBe('Indstillinger')
    expect(translate('en', 'devices.current', { name: 'CheifOne' })).toBe('This device: CheifOne')
    expect(translate('en', 'missing.key')).toBe('missing.key')
  })

  it('har samme nøgler på dansk og engelsk', () => {
    expect(availableLocales().sort()).toEqual(['da', 'en'])
  })
})
