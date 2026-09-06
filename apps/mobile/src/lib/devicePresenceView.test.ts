import { summarizeDevices } from './devicePresenceView'

it('names the current device and the route target from presence debug data', () => {
  const summary = summarizeDevices({
    summary: 'mobile active',
    devices: [
      { device_key: 'mobile-1', platform: 'mobile', foreground: true, awake: true, network: 'home', device_name: 'Pixel' },
      { device_key: 'desk-1', platform: 'desktop', foreground: true, awake: true, network: 'home', device_name: 'Jarvis Desk' }
    ],
    ranked: [{ device_key: 'mobile-1', platform: 'mobile', score: 8, via: 'fcm' }]
  }, 'mobile-1')

  expect(summary.current?.label).toBe('Pixel')
  expect(summary.routeTarget?.label).toBe('Pixel')
  expect(summary.rows).toHaveLength(2)
})
