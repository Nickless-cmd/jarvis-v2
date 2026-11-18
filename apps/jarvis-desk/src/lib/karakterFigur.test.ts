import { describe, expect, it } from 'vitest'
import {
  KARAKTER_ACCESSORIES,
  KARAKTER_FARVER,
  KARAKTER_SHAPES,
  karakterFigur,
} from './karakterFigur'

/**
 * De 28 navne cadence-registret faktisk registrerer — målt 18/11-2026 ved at
 * køre `matrix_navne()` mod registret. De er skrevet ind her fordi testen
 * kører i jsdom uden adgang til Python; ændrer registret sig, er det her
 * facit skal opdateres, ikke modellen.
 */
const REGISTRET = [
  'construct', 'oracle', 'architect', 'echo_breaker', 'continuity_healer',
  'red_dress', 'analyst', 'redpill', 'dissent', 'white_rabbit', 'belief_gap',
  'machines', 'morpheus', 'trinity', 'dejavu', 'sentinel', 'ghost', 'mourning',
  'merovingian', 'dream_action', 'rca', 'relational', 'glitch', 'trainman',
  'seraph', 'persephone', 'twins', 'exile',
] as const

describe('karakterFigur', () => {
  it('giver samme figur for samme navn, hver gang', () => {
    // Deterministisk på tværs af kald er hele pointen: ellers skifter en
    // karakters udseende ved hver genindlæsning af fladen.
    for (const navn of REGISTRET) {
      expect(karakterFigur(navn)).toEqual(karakterFigur(navn))
    }
  })

  it('giver en gyldig figur til alle 28 registrerede karakterer', () => {
    for (const navn of REGISTRET) {
      const f = karakterFigur(navn)
      expect(KARAKTER_SHAPES).toContain(f.shape)
      expect(KARAKTER_FARVER).toContain(f.farve)
      expect(f.accessory === null || KARAKTER_ACCESSORIES.includes(f.accessory)).toBe(true)
      expect(f.oejeAfstand).toBeGreaterThanOrEqual(2.6)
      expect(f.oejeAfstand).toBeLessThanOrEqual(3.5)
      expect(f.oejeHoejde).toBeGreaterThanOrEqual(19.5)
      expect(f.oejeHoejde).toBeLessThanOrEqual(22.5)
    }
  })

  it('bruger alle ti former blandt de 28 — ingen form er død kode', () => {
    // En form der aldrig vælges er en tegning ingen ser. Måler vi ikke dette,
    // kan et dårligt salt gøre halvdelen af paletten ubrugt uden at nogen ved det.
    const brugte = new Set(REGISTRET.map((n) => karakterFigur(n).shape))
    expect([...brugte].sort()).toEqual([...KARAKTER_SHAPES].sort())
  })

  it('bruger mindst otte af de ti farver', () => {
    const brugte = new Set(REGISTRET.map((n) => karakterFigur(n).farve))
    expect(brugte.size).toBeGreaterThanOrEqual(8)
  })

  it('giver ikke alle samme accessory, og ikke alle en', () => {
    const med = REGISTRET.filter((n) => karakterFigur(n).accessory !== null)
    expect(med.length).toBeGreaterThan(0)
    expect(med.length).toBeLessThan(REGISTRET.length)
    // Både beanie og headphones skal forekomme, ellers er ACCESSORY_VALG for
    // skæv til at de otte reelt er i brug.
    const slags = new Set(med.map((n) => karakterFigur(n).accessory))
    expect(slags.size).toBeGreaterThanOrEqual(4)
  })

  it('giver mindst 20 forskellige form+farve-par blandt de 28', () => {
    // To karakterer der deler både form og farve er til at forveksle i listen.
    // Med 100 mulige par og 28 navne er nogle sammenfald uundgåelige; under 20
    // ville betyde at fordelingen er klumpet, og så skal saltet justeres.
    const par = new Set(REGISTRET.map((n) => {
      const f = karakterFigur(n)
      return `${f.shape}|${f.farve}`
    }))
    expect(par.size).toBeGreaterThanOrEqual(20)
  })

  it('skelner navne der ligner hinanden', () => {
    // `red_dress` og `redpill` deler syv tegn. Havde hash-funktionen været
    // svag på præfikser, ville de få næsten samme figur.
    expect(karakterFigur('red_dress')).not.toEqual(karakterFigur('redpill'))
  })

  it('giver en figur ogsaa for et tomt eller ukendt navn', () => {
    // Fladen må ikke vælte fordi en producent registrerer sig underligt.
    expect(() => karakterFigur('')).not.toThrow()
    expect(KARAKTER_SHAPES).toContain(karakterFigur('').shape)
  })
})
