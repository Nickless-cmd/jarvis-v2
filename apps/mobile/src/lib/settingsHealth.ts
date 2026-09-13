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

type Translator = (key: string, vars?: Record<string, string | number>) => string

const DA: Record<string, string> = {
  'health.api': 'API',
  'health.push': 'Push',
  'health.microphone': 'Mikrofon',
  'health.camera': 'Kamera',
  'health.location': 'Lokation',
  'health.device': 'Enhed',
  'health.router': 'Router',
  'health.outbox': 'Outbox',
  'health.online': 'Online',
  'health.offline': 'Offline',
  'health.reconnecting': 'Genopretter',
  'health.active': 'Aktiv',
  'health.notTested': 'Ikke testet',
  'health.ready': 'Klar',
  'health.off': 'Fra',
  'health.precise': 'Præcis',
  'health.background': 'Baggrund',
  'health.unknown': 'Ukendt',
  'health.empty': 'Tom',
  'health.queued': '{count} i kø',
}

function fallbackT(key: string, vars?: Record<string, string | number>): string {
  let value = DA[key] ?? key
  for (const [k, v] of Object.entries(vars ?? {})) value = value.replace(`{${k}}`, String(v))
  return value
}

export function buildSettingsHealthTiles(input: SettingsHealthInput, t: Translator = fallbackT): SettingsHealthTile[] {
  const locationValue = input.locationPrecision === 'precise'
    ? t('health.precise')
    : input.locationPrecision === 'background'
      ? t('health.background')
      : precisionLabel(input.locationPrecision)
  return [
    {
      label: t('health.api'),
      value: input.connectivity === 'connected' ? t('health.online') : input.connectivity === 'offline' ? t('health.offline') : t('health.reconnecting'),
      state: input.connectivity === 'connected' ? 'ok' : input.connectivity === 'offline' ? 'off' : 'warn'
    },
    { label: t('health.push'), value: input.pushEnabled ? t('health.active') : t('health.notTested'), state: input.pushEnabled ? 'ok' : 'warn' },
    { label: t('health.microphone'), value: input.microphoneAvailable ? t('health.ready') : t('health.off'), state: input.microphoneAvailable ? 'ok' : 'off' },
    { label: t('health.camera'), value: input.cameraAvailable ? t('health.ready') : t('health.off'), state: input.cameraAvailable ? 'ok' : 'off' },
    {
      label: t('health.location'),
      value: locationValue,
      state: input.locationPrecision === 'off' ? 'off' : input.locationPrecision === 'background' ? 'warn' : 'ok'
    },
    { label: t('health.device'), value: input.currentDeviceName || t('health.unknown'), state: input.currentDeviceName ? 'ok' : 'warn' },
    { label: t('health.router'), value: input.routeTargetName || t('health.unknown'), state: input.routeTargetName ? 'ok' : 'warn' },
    { label: t('health.outbox'), value: input.outboxCount ? t('health.queued', { count: input.outboxCount }) : t('health.empty'), state: input.outboxCount ? 'warn' : 'ok' }
  ]
}
