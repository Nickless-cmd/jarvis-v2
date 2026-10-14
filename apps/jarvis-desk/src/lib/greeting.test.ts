import { describe, it, expect } from 'vitest'
import { greetingFor } from './greeting'

describe('greetingFor', () => {
  it('aften → Godaften uden et gentaget tidsikon', () => {
    const g = greetingFor(new Date('2026-06-16T20:00:00'), 0)
    expect(g.hello).toBe('Godaften')
    expect(g).not.toHaveProperty('glyph')
  })

  it('morgen → Godmorgen uden et gentaget tidsikon', () => {
    const g = greetingFor(new Date('2026-06-16T07:00:00'), 0)
    expect(g.hello).toBe('Godmorgen')
    expect(g).not.toHaveProperty('glyph')
  })

  it('seed vælger deterministisk linje fra puljen', () => {
    const a = greetingFor(new Date('2026-06-16T20:00:00'), 0)
    const b = greetingFor(new Date('2026-06-16T20:00:00'), 0)
    expect(a.line).toBe(b.line)
    expect(a.line.length).toBeGreaterThan(0)
  })

  it('tilføjer ikke en særskilt tint til den almindelige hilsen', () => {
    expect(greetingFor(new Date('2026-06-16T20:00:00'), 0)).not.toHaveProperty('tint')
  })
})
