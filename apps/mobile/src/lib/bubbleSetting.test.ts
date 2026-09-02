import { parseBubblePersist } from './bubbleSetting'

describe('parseBubblePersist', () => {
  it('"1" → true', () => expect(parseBubblePersist('1')).toBe(true))
  it('"0" → false', () => expect(parseBubblePersist('0')).toBe(false))
  it('null → false', () => expect(parseBubblePersist(null)).toBe(false))
})
