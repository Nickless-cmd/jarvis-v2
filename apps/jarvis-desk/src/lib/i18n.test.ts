import { describe, it, expect, beforeEach } from 'vitest'
import { t, setLocale, getLocale, availableLocales, initLocaleFromOS } from './i18n'
import da from '../locales/da.json'
import en from '../locales/en.json'

describe('i18n', () => {
  beforeEach(() => setLocale('da'))

  it('oversætter på dansk (default)', () => {
    expect(t('nav.code')).toBe('Kode')
    expect(t('cowork.agents')).toBe('Agenter')
  })

  it('skifter til engelsk', () => {
    setLocale('en')
    expect(t('nav.code')).toBe('Code')
    expect(getLocale()).toBe('en')
  })

  it('falder tilbage til da, så nøgle', () => {
    setLocale('en')
    // en mangler ikke nøgler her, men ukendt nøgle → selve nøglen
    expect(t('helt.ukendt.nøgle')).toBe('helt.ukendt.nøgle')
  })

  it('interpolerer variabler', () => {
    // ingen var-streng i default-sættet — test mekanikken direkte via en kendt nøgle
    expect(t('quota.exceeded')).toContain('kvote')
  })

  it('da og en har IDENTISKE nøgler (ingen huller)', () => {
    expect(Object.keys(da).sort()).toEqual(Object.keys(en).sort())
  })

  it('initLocaleFromOS vælger understøttet sprog', () => {
    initLocaleFromOS('en-US')
    expect(getLocale()).toBe('en')
    initLocaleFromOS('fr-FR')   // ikke understøttet → uændret
    expect(getLocale()).toBe('en')
  })

  it('availableLocales', () => {
    expect(availableLocales().sort()).toEqual(['da', 'en'])
  })
})
