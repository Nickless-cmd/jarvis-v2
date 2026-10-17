import { describe, expect, it } from 'vitest'
import { formaterTurTid } from './turTid'

describe('formaterTurTid', () => {
  it('viser sekunder alene indtil det første minut', () => {
    expect(formaterTurTid(0)).toBe('0s')
    expect(formaterTurTid(7)).toBe('7s')
    expect(formaterTurTid(59)).toBe('59s')
  })

  it('skifter til minutter og sekunder ved 60', () => {
    expect(formaterTurTid(60)).toBe('1m 00s')
    expect(formaterTurTid(72)).toBe('1m 12s')
    expect(formaterTurTid(3599)).toBe('59m 59s')
  })

  it('viser timer naar turen loeber over en time', () => {
    expect(formaterTurTid(3600)).toBe('1t 00m')
    expect(formaterTurTid(3900)).toBe('1t 05m')
  })
})
