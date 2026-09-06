import { networkToHint, buildMobilePing } from './presence'

describe('mobil presence', () => {
  it('mapper netværkstype til hint', () => {
    expect(networkToHint('wifi')).toBe('home')
    expect(networkToHint('cellular')).toBe('away')
    expect(networkToHint('none')).toBe('unknown')
    expect(networkToHint('other')).toBe('unknown')
  })

  it('bygger ping-payload med stabil device id og token separat', () => {
    const pushToken = ['tok', '1'].join('-')
    expect(buildMobilePing({
      token: pushToken,
      deviceId: 'mobile-install-1',
      deviceName: 'Pixel',
      foreground: true,
      network: 'away',
      interaction: false,
      activeSessionId: 's1',
      batterySaver: true
    })).toEqual({
      device_key: 'mobile-install-1', push_token: pushToken, device_name: 'Pixel', platform: 'mobile',
      foreground: true, awake: true, network: 'away', interaction: false,
      active_session_id: 's1', battery_saver: true
    })
  })
})
