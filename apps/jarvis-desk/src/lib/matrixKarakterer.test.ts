import { describe, expect, it } from 'vitest'
import {
  formatCooldown, formatMinutter, formatSidste, karakterListe, splitFunktion, udfaldVisning,
} from './matrixKarakterer'

describe('splitFunktion', () => {
  it('deler «Navn — funktion» ved tankestregen', () => {
    expect(splitFunktion('Déjà Vu — ufrivillig erindring', 'dejavu'))
      .toEqual({ navn: 'Déjà Vu', beskrivelse: 'ufrivillig erindring' })
  })
  it('uden tankestreg er teksten beskrivelsen og navnet falder tilbage', () => {
    expect(splitFunktion('Noget uden streg', 'white_rabbit'))
      .toEqual({ navn: 'white rabbit', beskrivelse: 'Noget uden streg' })
  })
  it('tom funktion giver tom beskrivelse, ikke en fejl', () => {
    expect(splitFunktion('', 'ghost')).toEqual({ navn: 'ghost', beskrivelse: '' })
  })
})

describe('cooldown', () => {
  it('formaterer minutter, timer og dage', () => {
    expect(formatMinutter(45)).toBe('45 min')
    expect(formatMinutter(360)).toBe('6 t')
    expect(formatMinutter(1440)).toBe('24 t')
    expect(formatMinutter(30 * 24 * 60)).toBe('30 d')
    expect(formatMinutter(0)).toBe('—')
  })
  it('viser kun den effektive ved tempo 1', () => {
    expect(formatCooldown({ cooldown_minutes: 60, effektiv_cooldown_minutes: 60 }, 1)).toBe('60 min')
  })
  it('viser den effektive FØRST og rå × tempo som forklaring ved modulation', () => {
    expect(formatCooldown({ cooldown_minutes: 60, effektiv_cooldown_minutes: 30 }, 0.5))
      .toBe('30 min (60 min × 0.50)')
  })
})

describe('formatSidste', () => {
  const nu = new Date('2026-11-13T12:00:00Z')
  it('manglende eller ugyldig tid er «aldrig set», ikke et gæt', () => {
    expect(formatSidste(null, nu)).toBe('aldrig set')
    expect(formatSidste('ikke-en-dato', nu)).toBe('aldrig set')
  })
  it('regner relativt', () => {
    expect(formatSidste('2026-11-13T11:30:00Z', nu)).toBe('30 min siden')
    expect(formatSidste('2026-11-13T06:00:00Z', nu)).toBe('6 t siden')
  })
})

describe('udfaldVisning', () => {
  it('uden udfald er «ukendt» — aldrig grøn', () => {
    const v = udfaldVisning({ udfald: null, udfald_at: null })
    expect(v.tekst).toBe('ukendt')
    expect(v.tone).toBe('ukendt')
  })
  it('videregiver serverens tekst og tone, og rå-værdien som title', () => {
    const v = udfaldVisning({
      udfald: { outcome: 'skift_registreret', tekst: 'skift registreret', tone: 'warn' },
      udfald_at: '2026-11-13T10:00:00Z',
    })
    expect(v).toEqual({ tekst: 'skift registreret', tone: 'warn', title: 'skift_registreret' })
  })
})

describe('karakterListe', () => {
  it('tåler manglende eller forkert payload', () => {
    expect(karakterListe(null)).toEqual([])
    expect(karakterListe({})).toEqual([])
    expect(karakterListe({ karakterer: 'nej' })).toEqual([])
  })
})
