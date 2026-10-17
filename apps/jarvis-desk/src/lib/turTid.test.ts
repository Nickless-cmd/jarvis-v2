import { describe, expect, it } from 'vitest'
import { formaterTurTid, varighedFraTider } from './turTid'

describe('varighedFraTider', () => {
  it('regner turen ud af spændet mellem brugertrækken og assistentrækken', () => {
    // De tre ture er målt mod databasen 17/10-2026 — ikke opdigtede tal.
    expect(varighedFraTider('2026-10-17T15:22:04.542723+00:00', '2026-10-17T15:25:30.810715+00:00')).toBe(206)
    expect(varighedFraTider('2026-10-17T16:12:29.266881+00:00', '2026-10-17T16:12:55.669065+00:00')).toBe(26)
    expect(varighedFraTider('2026-10-17T16:34:02.361124+00:00', '2026-10-17T16:34:09.440723+00:00')).toBe(7)
  })

  it('giver intet tal når tiderne mangler eller står i den forkerte rækkefølge', () => {
    expect(varighedFraTider(null, '2026-10-17T16:34:09.440723+00:00')).toBeNull()
    expect(varighedFraTider('2026-10-17T16:34:09.440723+00:00', null)).toBeNull()
    expect(varighedFraTider('2026-10-17T16:34:09.440723+00:00', '2026-10-17T16:34:02.361124+00:00')).toBeNull()
  })

  it('afviser et spænd over to timer — det er et genoptaget run, ikke en tur', () => {
    expect(varighedFraTider('2026-10-17T10:00:00.000000+00:00', '2026-10-17T13:00:00.000000+00:00')).toBeNull()
  })
})

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
