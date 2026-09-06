import { formatérTid } from './TaskThreadScreen'

describe('opgave-tråden (R6)', () => {
  it('viser klokkeslæt, ikke dato — tidspunktet bærer tidslinjen', () => {
    expect(formatérTid('2026-09-06T14:32:00+00:00')).toMatch(/^\d{2}[.:]\d{2}$/)
  })

  it('en ugyldig tid vælter ikke tråden', () => {
    expect(formatérTid('volapyk')).toBe('')
    expect(formatérTid('')).toBe('')
  })
})
