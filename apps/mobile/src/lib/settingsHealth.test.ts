import { buildSettingsHealthTiles } from './settingsHealth'

it('builds a compact control-center summary for settings', () => {
  const tiles = buildSettingsHealthTiles({
    connectivity: 'connected',
    pushEnabled: true,
    microphoneAvailable: true,
    cameraAvailable: true,
    locationPrecision: 'precise',
    currentDeviceName: 'Pixel',
    routeTargetName: 'Jarvis Desk',
    outboxCount: 2
  })

  expect(tiles.map((t) => t.label)).toEqual(['API', 'Push', 'Mikrofon', 'Kamera', 'Lokation', 'Enhed', 'Router', 'Outbox'])
  expect(tiles.find((t) => t.label === 'Outbox')?.value).toBe('2 i kø')
  expect(tiles.find((t) => t.label === 'Lokation')?.value).toBe('Præcis')
})

it('can render health tiles in English through the app translator', () => {
  const dict: Record<string, string> = {
    'health.api': 'API',
    'health.push': 'Push',
    'health.microphone': 'Microphone',
    'health.camera': 'Camera',
    'health.location': 'Location',
    'health.device': 'Device',
    'health.router': 'Router',
    'health.outbox': 'Outbox',
    'health.online': 'Online',
    'health.offline': 'Offline',
    'health.reconnecting': 'Reconnecting',
    'health.active': 'Active',
    'health.notTested': 'Not tested',
    'health.ready': 'Ready',
    'health.off': 'Off',
    'health.precise': 'Precise',
    'health.background': 'Background',
    'health.unknown': 'Unknown',
    'health.empty': 'Empty',
    'health.queued': '{count} queued',
  }
  const t = (key: string, vars?: Record<string, string | number>) => {
    let value = dict[key] ?? key
    for (const [k, v] of Object.entries(vars ?? {})) value = value.replace(`{${k}}`, String(v))
    return value
  }

  const tiles = buildSettingsHealthTiles({
    connectivity: 'offline',
    pushEnabled: false,
    microphoneAvailable: false,
    cameraAvailable: true,
    locationPrecision: 'background',
    outboxCount: 3,
  }, t)

  expect(tiles.map((tile) => `${tile.label}:${tile.value}`)).toContain('Microphone:Off')
  expect(tiles.map((tile) => `${tile.label}:${tile.value}`)).toContain('Outbox:3 queued')
  expect(tiles.map((tile) => `${tile.label}:${tile.value}`)).toContain('Location:Background')
})
