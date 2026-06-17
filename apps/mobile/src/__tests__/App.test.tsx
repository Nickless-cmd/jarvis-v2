import { render } from '@testing-library/react-native'
import App from '../App'

it('renders the Jarvis mobile shell', async () => {
  const { getByText } = await render(<App />)
  expect(getByText('Jarvis')).toBeTruthy()
  expect(getByText('Mobile companion')).toBeTruthy()
})
