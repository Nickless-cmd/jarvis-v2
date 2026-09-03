import { ACCENTS, accentByName, onAccent, paletteFor } from './palettes'
import { buildTheme } from './ThemeContext'

describe('paletter', () => {
  it('alle accenter har begge boble-varianter og en rgb-trippel', () => {
    for (const a of ACCENTS) {
      expect(a.color).toMatch(/^#[0-9A-Fa-f]{6}$/)
      expect(a.bubbleDark).toMatch(/^#[0-9A-Fa-f]{6}$/)
      expect(a.bubbleLight).toMatch(/^#[0-9A-Fa-f]{6}$/)
      expect(a.rgb.split(',')).toHaveLength(3)
    }
  })

  it('ukendt accent falder tilbage paa den foerste', () => {
    expect(accentByName('findes-ikke').name).toBe(ACCENTS[0]!.name)
    expect(accentByName(null).name).toBe(ACCENTS[0]!.name)
  })

  it('lys og moerk deler ROLLE-navne, ikke vaerdier', () => {
    const dark = paletteFor('dark', ACCENTS[0]!)
    const light = paletteFor('light', ACCENTS[0]!)
    expect(Object.keys(dark).sort()).toEqual(Object.keys(light).sort())
    expect(dark.bg0).not.toBe(light.bg0)
    expect(dark.fg1).not.toBe(light.fg1)
  })

  it('brugerboblen foelger baade accent og tema', () => {
    const a = ACCENTS[2]!  // lilla
    expect(paletteFor('dark', a).userBubble).toBe(a.bubbleDark)
    expect(paletteFor('light', a).userBubble).toBe(a.bubbleLight)
  })

  // Send-knappen har accent-baggrund og et ikon ovenpaa. Uden dette ville
  // ikonet forsvinde paa halvdelen af paletterne.
  it('tekst OVEN PAA accenten vender efter accentens lyshed', () => {
    expect(onAccent(accentByName('gron'))).toBe('#111111')   // lys accent
    expect(onAccent(accentByName('bla'))).toBe('#FFFFFF')    // moerk accent
  })
})

describe('buildTheme', () => {
  it('auto foelger systemets valg', () => {
    expect(buildTheme('auto', 'gron', 'light').scheme).toBe('light')
    expect(buildTheme('auto', 'gron', 'dark').scheme).toBe('dark')
  })

  it('et eksplicit valg ignorerer systemet', () => {
    expect(buildTheme('dark', 'gron', 'light').scheme).toBe('dark')
    expect(buildTheme('light', 'gron', 'dark').scheme).toBe('light')
  })

  it('accent og tema er uafhaengige valg', () => {
    const a = buildTheme('light', 'rav', 'dark')
    expect(a.scheme).toBe('light')
    expect(a.accent.name).toBe('rav')
  })

  it('temaet baerer stadig afstande og radier', () => {
    const t = buildTheme('dark', 'gron', 'dark')
    expect(t.spacing.md).toBeGreaterThan(0)
    expect(t.radius.lg).toBeGreaterThan(0)
  })
})

describe('accentText', () => {
  // «Forbundet til Jarvis ✓» i lys groen paa hvidt var naesten ulaeselig.
  it('moerknes i lyst tema, men kun som TEKST', () => {
    const a = accentByName('gron')
    const light = paletteFor('light', a)
    const dark = paletteFor('dark', a)
    expect(light.accentText).not.toBe(a.color)
    expect(light.accent).toBe(a.color)      // fladen beholder brugerens valg
    expect(dark.accentText).toBe(a.color)   // paa sort er den fin som den er
  })

  it('den moerknede er faktisk moerkere', () => {
    const light = paletteFor('light', accentByName('gron'))
    const lum = (hex: string) => parseInt(hex.slice(1, 3), 16) + parseInt(hex.slice(3, 5), 16)
    expect(lum(light.accentText)).toBeLessThan(lum(light.accent))
  })
})
