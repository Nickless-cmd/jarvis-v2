import { describe, it, expect } from 'vitest'
import { greetingFor } from './greeting'

describe('greetingFor', () => {
  it('aften → måne + Godaften', () => {
    const g = greetingFor(new Date('2026-06-16T20:00:00'), 0)
    expect(g.glyph).toBe('🌙')
    expect(g.hello).toBe('Godaften')
  })

  it('morgen → soldopgang + Godmorgen', () => {
    const g = greetingFor(new Date('2026-06-16T07:00:00'), 0)
    expect(g.glyph).toBe('🌅')
    expect(g.hello).toBe('Godmorgen')
  })

  it('middag → sol', () => {
    expect(greetingFor(new Date('2026-06-16T12:00:00'), 0).glyph).toBe('☀️')
  })

  it('nat → måne', () => {
    expect(greetingFor(new Date('2026-06-16T02:00:00'), 0).glyph).toBe('🌙')
  })

  it('seed vælger deterministisk linje fra puljen', () => {
    const a = greetingFor(new Date('2026-06-16T20:00:00'), 0)
    const b = greetingFor(new Date('2026-06-16T20:00:00'), 0)
    expect(a.line).toBe(b.line)
    expect(a.line.length).toBeGreaterThan(0)
  })

  it('giver en tint (hex) pr. bucket', () => {
    expect(greetingFor(new Date('2026-06-16T20:00:00'), 0).tint).toMatch(/^#/)
  })
})
