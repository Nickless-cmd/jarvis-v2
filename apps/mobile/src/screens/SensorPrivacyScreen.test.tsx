import { render } from '@testing-library/react-native'
import { SensorPrivacyScreen } from './SensorPrivacyScreen'

it('renders a single privacy dashboard for sensors and background behavior', async () => {
  const screen = await render(
    <SensorPrivacyScreen
      onClose={jest.fn()}
      rows={[
        { id: 'camera', label: 'Kamera', value: 'Shutter stille', risk: 'medium' },
        { id: 'location', label: 'Lokation', value: 'Præcis', risk: 'high' }
      ]}
    />
  )

  expect(screen.getByText('Sanser & privatliv')).toBeTruthy()
  expect(screen.getByText('Kamera')).toBeTruthy()
  expect(screen.getByText('Lokation')).toBeTruthy()
})
