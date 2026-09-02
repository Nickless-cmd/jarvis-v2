import { livesInHousehold } from './household'

describe('livesInHousehold', () => {
  it('Bjoern (owner) og Michelle (partner) bor i huset', () => {
    expect(livesInHousehold({ role: 'owner' })).toBe(true)
    expect(livesInHousehold({ role: 'partner' })).toBe(true)
  })

  it('familie bor ikke i huset', () => {
    expect(livesInHousehold({ role: 'member' })).toBe(false)
    expect(livesInHousehold({ role: 'guest' })).toBe(false)
  })

  // At gaette forkert her betyder en knap der giver 403 — ikke en laekage.
  it('ukendt rolle skjuler indgangen', () => {
    expect(livesInHousehold(null)).toBe(false)
    expect(livesInHousehold(undefined)).toBe(false)
    expect(livesInHousehold({ role: 'noget' } as never)).toBe(false)
  })
})
