import { describe, expect, it } from 'vitest'
import { skalGenhente } from './komprimeringsVagt'

// Bjørn 18/9-2026: markøren stod først på skærmen efter en manuel opdatering.
describe('skalGenhente', () => {
  it('første aflæsning er bare nulpunktet — beskederne blev netop hentet', () => {
    expect(skalGenhente(null, '2026-09-18T20:20:44Z')).toBe(false)
  })

  it('en NY markør betyder: hent beskederne igen', () => {
    expect(skalGenhente('2026-09-18T19:00:00Z', '2026-09-18T20:20:44Z')).toBe(true)
  })

  it('den første markør nogensinde i en session tæller også', () => {
    expect(skalGenhente('', '2026-09-18T20:20:44Z')).toBe(true)
  })

  it('samme markør som sidst: intet at hente', () => {
    expect(skalGenhente('2026-09-18T20:20:44Z', '2026-09-18T20:20:44Z')).toBe(false)
  })

  // En server der endnu ikke sender feltet må ikke udløse en genhentning pr. poll.
  it('manglende felt fra en ældre server udløser intet', () => {
    expect(skalGenhente('', undefined)).toBe(false)
    expect(skalGenhente('2026-09-18T20:20:44Z', undefined)).toBe(false)
  })
})
