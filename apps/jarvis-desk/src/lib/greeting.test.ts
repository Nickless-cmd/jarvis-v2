import { describe, it, expect } from 'vitest'
import { greetingFor } from './greeting'

describe('greetingFor', () => {
  it('aften → Godaften', () => {
    expect(greetingFor(new Date('2026-06-16T20:00:00'), 0).hello).toBe('Godaften')
  })

  it('morgen → Godmorgen', () => {
    expect(greetingFor(new Date('2026-06-16T07:00:00'), 0).hello).toBe('Godmorgen')
  })

  it('middag → God dag', () => {
    expect(greetingFor(new Date('2026-06-16T12:00:00'), 0).hello).toBe('God dag')
  })

  it('nat → Godnat', () => {
    expect(greetingFor(new Date('2026-06-16T02:00:00'), 0).hello).toBe('Godnat')
  })

  it('seed vælger deterministisk linje fra puljen', () => {
    const a = greetingFor(new Date('2026-06-16T20:00:00'), 0)
    const b = greetingFor(new Date('2026-06-16T20:00:00'), 0)
    expect(a.line).toBe(b.line)
    expect(a.line.length).toBeGreaterThan(0)
  })

  // 13/10-2026: glyphen — og tint'en der tonede ringen om den — er fjernet.
  // Bjørn: «det icon med sol og måne passer ikk rigtigt ind». Testen holder
  // beslutningen fast: dukker et emoji-felt op igen, fanges det her.
  it('bærer hverken glyph eller tint — hilsenen er ord', () => {
    const g = greetingFor(new Date('2026-06-16T20:00:00'), 0) as unknown as Record<string, unknown>
    expect(g.glyph).toBeUndefined()
    expect(g.tint).toBeUndefined()
  })
})
