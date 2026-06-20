// Desktop device-presence: bygger ping-payload til POST /presence/ping.
// Desktop antages altid på 'home'-netværk (stationær).
import type { DeskLocationPayload } from './deskLocation'

export interface DesktopPingState {
  deviceKey: string
  foreground: boolean
  awake: boolean
  interaction: boolean
  // undefined = udelad (ingen ændring); {} = ryd (toggle off); payload = ny lokation.
  location?: DeskLocationPayload | Record<string, never>
}

export interface PresencePingBody {
  device_key: string
  platform: 'desktop'
  foreground: boolean
  awake: boolean
  network: 'home'
  interaction: boolean
  location?: DeskLocationPayload | Record<string, never>
}

export function buildPingBody(s: DesktopPingState): PresencePingBody {
  const body: PresencePingBody = {
    device_key: s.deviceKey,
    platform: 'desktop',
    foreground: s.foreground,
    awake: s.awake,
    network: 'home',
    interaction: s.interaction,
  }
  if (s.location !== undefined) body.location = s.location
  return body
}
