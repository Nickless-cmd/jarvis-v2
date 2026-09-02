import { tokens } from './tokens'

describe('design-sprog tokens (ChatGPT-paritet, målt 2026-09-02)', () => {
  it('siden er ægte sort', () => {
    expect(tokens.color.bg0).toBe('#000000')
    expect(tokens.color.depth0).toBe('#000000')
  })

  it('det AKTIVE segment er mørkere end beholderen', () => {
    // Speccen sagde det modsatte. Målingen på R2 vandt: beholder #414141,
    // aktiv pille #222222. Testen findes for at fange en tilbagerulning.
    expect(tokens.color.segmentTrack).toBe('#414141')
    expect(tokens.color.segmentActive).toBe('#212121')
    const lum = (hex: string) => parseInt(hex.slice(1, 3), 16)
    expect(lum(tokens.color.segmentActive)).toBeLessThan(lum(tokens.color.segmentTrack))
  })

  it('accenten er lilla — ikke V1s grønne', () => {
    // Accenten er den ENE bevidste afvigelse fra de målte ChatGPT-værdier.
    // Se kommentaren i tokens.ts: form følger referencen, farven er Jarvis' egen.
    expect(tokens.color.accent).toBe('#3FC7B4')
    expect(tokens.color.accent).not.toBe('#6ee7a8')
    expect(tokens.color.accentDim).toContain('63, 199, 180')
  })

  it('status-grøn lever videre som sin egen farve', () => {
    // Online-prikken er stadig grøn i ChatGPT — den må ikke følge accenten.
    expect(tokens.color.ok).toBe('#4CAF50')
  })

  it('har glas + timing', () => {
    expect(tokens.color.glassFill).toMatch(/rgba\(255, ?255, ?255, ?0\.07\)/)
    expect(tokens.motion.breath).toBe(3000)
    expect(tokens.motion.durBase).toBe(250)
    expect(tokens.motion.heartbeat).toBe(1400)
  })
})
