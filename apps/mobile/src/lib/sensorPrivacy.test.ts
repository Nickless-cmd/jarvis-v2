import { sensorRowsFromState } from './sensorPrivacy'

it('summarizes sensor permissions and switches in one privacy model', () => {
  const rows = sensorRowsFromState({
    cameraShutterSound: false,
    locationPrecision: 'background',
    batterySaver: true,
    bubbleEnabled: false,
    microphoneAvailable: true
  })

  expect(rows.map((r) => r.id)).toEqual(['camera', 'microphone', 'location', 'background', 'bubble', 'battery'])
  expect(rows.find((r) => r.id === 'camera')?.value).toContain('stille')
  expect(rows.find((r) => r.id === 'background')?.risk).toBe('high')
})
