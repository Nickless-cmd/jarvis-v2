import type { PresenceDebugSnapshot } from './apiClient'

export interface DevicePresenceRow {
  key: string
  label: string
  detail: string
  current: boolean
  routeTarget: boolean
}

export function summarizeDevices(snapshot: PresenceDebugSnapshot, currentDeviceKey?: string) {
  const rankedKey = snapshot.ranked?.[0]?.device_key
  const rows: DevicePresenceRow[] = (snapshot.devices ?? []).map((device) => ({
    key: device.device_key,
    label: device.device_name || device.platform || device.device_key,
    detail: [
      device.platform,
      device.foreground ? 'aktiv' : 'baggrund',
      device.network,
      device.battery_saver ? 'batterioptimeret' : ''
    ].filter(Boolean).join(' · '),
    current: Boolean(currentDeviceKey && device.device_key === currentDeviceKey),
    routeTarget: Boolean(rankedKey && device.device_key === rankedKey)
  }))
  return {
    summary: snapshot.summary,
    rows,
    current: rows.find((row) => row.current) ?? null,
    routeTarget: rows.find((row) => row.routeTarget) ?? null
  }
}
