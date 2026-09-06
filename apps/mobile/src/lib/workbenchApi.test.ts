import { timerTilbage } from './workbenchApi'

describe('timerTilbage', () => {
  it('runder til hele timer — minuttet betyder intet her', () => {
    expect(timerTilbage({ open: true, udloeber_om_s: 7200 })).toBe(2)
    expect(timerTilbage({ open: true, udloeber_om_s: 12600 })).toBe(4)
  })

  it('viser mindst 1 t så længe der ER tid tilbage', () => {
    expect(timerTilbage({ open: true, udloeber_om_s: 120 })).toBe(1)
  })

  it('giver 0 når kanalen er lukket eller ukendt', () => {
    expect(timerTilbage({ open: false })).toBe(0)
    expect(timerTilbage(null)).toBe(0)
  })
})
