// Desktop device-presence: bygger ping-payload til POST /presence/ping.
// Desktop antages altid på 'home'-netværk (stationær).

export interface DesktopPingState {
  deviceKey: string
  foreground: boolean
  awake: boolean
  interaction: boolean
}

export interface PresencePingBody {
  device_key: string
  platform: 'desktop'
  foreground: boolean
  awake: boolean
  network: 'home'
  interaction: boolean
}

export function buildPingBody(s: DesktopPingState): PresencePingBody {
  return {
    device_key: s.deviceKey,
    platform: 'desktop',
    foreground: s.foreground,
    awake: s.awake,
    network: 'home',
    interaction: s.interaction,
  }
}
