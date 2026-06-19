import { describe, it, expect } from 'vitest'
import { buildPingBody } from './presence'

describe('buildPingBody', () => {
  it('mapper desktop-state til ping-payload', () => {
    const b = buildPingBody({ deviceKey: 'dev-1', foreground: true, awake: false, interaction: true })
    expect(b).toEqual({
      device_key: 'dev-1', platform: 'desktop',
      foreground: true, awake: false, network: 'home', interaction: true,
    })
  })
})
