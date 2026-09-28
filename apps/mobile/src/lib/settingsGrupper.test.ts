import { SETTINGS_GRUPPER, SETTINGS_PUNKTER, matcherSoegning } from './settingsGrupper'

// Bjørn 28/9-2026: «det skal være nemt og overskueligt og noget der fanger nye
// brugere og lad folk uden for stor teknisk viden kunne finde ud af menu».
// Rækkefølgen ER svaret på det, så den skal være låst — ikke overladt til
// tilfældig omrokering næste gang nogen rører skærmen.

describe('indstillingernes grupper', () => {
  it('har fem grupper i den rækkefølge brugeren møder dem', () => {
    expect(SETTINGS_GRUPPER.map((g) => g.navn)).toEqual([
      'Jarvis',
      'Sanser & privatliv',
      'Forbindelser',
      'Data & konto',
      'Avanceret'
    ])
  })

  it('lægger det basale før det tekniske', () => {
    // Det var hele problemet: Udseende lå som niende sektion, efter teknikken.
    const i = SETTINGS_PUNKTER
    expect(i.indexOf('udseende')).toBeLessThan(i.indexOf('diagnostik'))
    expect(i.indexOf('hukommelse')).toBeLessThan(i.indexOf('status'))
    expect(i.indexOf('lokation')).toBeLessThan(i.indexOf('chat'))
  })

  it('Avanceret ligger sidst — teknikken samlet ét sted', () => {
    expect(SETTINGS_GRUPPER[SETTINGS_GRUPPER.length - 1]!.navn).toBe('Avanceret')
  })

  it('hvert punkt vises præcis én gang', () => {
    expect(new Set(SETTINGS_PUNKTER).size).toBe(SETTINGS_PUNKTER.length)
  })

  it('tom søgning viser alt', () => {
    expect(matcherSoegning('udseende lys mørk', '')).toBe(true)
    expect(matcherSoegning('udseende lys mørk', '   ')).toBe(true)
  })

  it('søger på brugerens ord, ikke på kode-navne', () => {
    expect(matcherSoegning('hukommelse husker memory glem', 'husker')).toBe(true)
    expect(matcherSoegning('udseende lys mørk tema farve', 'mørk')).toBe(true)
    expect(matcherSoegning('udseende lys mørk tema farve', 'MØRK')).toBe(true)
    expect(matcherSoegning('udseende lys mørk tema farve', 'diagnostik')).toBe(false)
  })
})
