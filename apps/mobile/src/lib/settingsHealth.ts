import { precisionLabel, type LocationPrecision } from './location'
import type { Connectivity } from './useConnectivity'

export interface SettingsHealthInput {
  connectivity: Connectivity
  pushEnabled: boolean
  microphoneAvailable: boolean
  cameraAvailable: boolean
  locationPrecision: LocationPrecision
  currentDeviceName?: string
  routeTargetName?: string
  outboxCount: number
}

export interface SettingsHealthTile {
  label: string
  value: string
  state: 'ok' | 'warn' | 'off'
}

export function buildSettingsHealthTiles(input: SettingsHealthInput): SettingsHealthTile[] {
  const locationValue = input.locationPrecision === 'precise'
    ? 'Præcis'
    : input.locationPrecision === 'background'
      ? 'Baggrund'
      : precisionLabel(input.locationPrecision)
  return [
    {
      label: 'API',
      value: input.connectivity === 'connected' ? 'Online' : input.connectivity === 'offline' ? 'Offline' : 'Genopretter',
      state: input.connectivity === 'connected' ? 'ok' : input.connectivity === 'offline' ? 'off' : 'warn'
    },
    { label: 'Push', value: input.pushEnabled ? 'Aktiv' : 'Ikke testet', state: input.pushEnabled ? 'ok' : 'warn' },
    { label: 'Mikrofon', value: input.microphoneAvailable ? 'Klar' : 'Fra', state: input.microphoneAvailable ? 'ok' : 'off' },
    { label: 'Kamera', value: input.cameraAvailable ? 'Klar' : 'Fra', state: input.cameraAvailable ? 'ok' : 'off' },
    {
      label: 'Lokation',
      value: locationValue,
      state: input.locationPrecision === 'off' ? 'off' : input.locationPrecision === 'background' ? 'warn' : 'ok'
    },
    { label: 'Enhed', value: input.currentDeviceName || 'Ukendt', state: input.currentDeviceName ? 'ok' : 'warn' },
    { label: 'Router', value: input.routeTargetName || 'Ukendt', state: input.routeTargetName ? 'ok' : 'warn' },
    { label: 'Outbox', value: input.outboxCount ? `${input.outboxCount} i kø` : 'Tom', state: input.outboxCount ? 'warn' : 'ok' }
  ]
}
