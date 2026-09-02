import { nextUserRow } from './messageNav'

describe('nextUserRow', () => {
  // flags[i] = er række i en bruger-besked
  const flags = [false, true, false, false, true, false] // bruger ved 1 og 4
  it('finder næste bruger-række i +retning', () => {
    expect(nextUserRow(flags, 1, 1)).toBe(4)
    expect(nextUserRow(flags, 0, 1)).toBe(1)
  })
  it('finder næste bruger-række i -retning', () => {
    expect(nextUserRow(flags, 4, -1)).toBe(1)
  })
  it('null når ingen i retningen', () => {
    expect(nextUserRow(flags, 4, 1)).toBeNull()
    expect(nextUserRow(flags, 1, -1)).toBeNull()
  })
  it('håndterer current uden for grænser', () => {
    expect(nextUserRow(flags, -1, 1)).toBe(1)
    expect(nextUserRow(flags, 99, -1)).toBe(4)
  })
})
