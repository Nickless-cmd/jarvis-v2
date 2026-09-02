import { render } from '@testing-library/react-native'
import { HeartbeatDot } from './HeartbeatDot'

describe('HeartbeatDot', () => {
  it('rendrer uden crash', async () => {
    const { toJSON } = await render(<HeartbeatDot />)
    expect(toJSON()).toBeTruthy()
  })
})
