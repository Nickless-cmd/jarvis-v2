import { tokens } from './tokens'

describe('design-sprog tokens', () => {
  it('har depth-lag', () => {
    expect(tokens.color.depth0).toBe('#0D0D12')
    expect(tokens.color.depth1).toBe('#10151d')
    expect(tokens.color.depth2).toBe('#131922')
  })
  it('har glas + accent-varianter', () => {
    expect(tokens.color.glassFill).toMatch(/rgba\(255, ?255, ?255, ?0\.07\)/)
    expect(tokens.color.accentDim).toContain('110, 231, 168')
  })
  it('har timing', () => {
    expect(tokens.motion.breath).toBe(3000)
    expect(tokens.motion.durBase).toBe(250)
    expect(tokens.motion.heartbeat).toBe(1400)
  })
})
