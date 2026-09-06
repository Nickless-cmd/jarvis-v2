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
