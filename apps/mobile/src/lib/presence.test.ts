import { networkToHint, buildMobilePing } from './presence'

describe('mobil presence', () => {
  it('mapper netværkstype til hint', () => {
    expect(networkToHint('wifi')).toBe('home')
    expect(networkToHint('cellular')).toBe('away')
    expect(networkToHint('none')).toBe('unknown')
    expect(networkToHint('other')).toBe('unknown')
  })

  it('bygger ping-payload (token som device_key)', () => {
    expect(buildMobilePing({ token: 'tok-1', foreground: true, network: 'away', interaction: false })).toEqual({
      device_key: 'tok-1', platform: 'mobile',
      foreground: true, awake: true, network: 'away', interaction: false,
    })
  })
})
