import { render } from '@testing-library/react-native'
import { StreamIndicator } from './StreamIndicator'

describe('StreamIndicator', () => {
  it('rendrer når active', async () => {
    const { toJSON } = await render(<StreamIndicator active />)
    expect(toJSON()).toBeTruthy()
  })
  it('rendrer ingenting når inaktiv', async () => {
    const { toJSON } = await render(<StreamIndicator active={false} />)
    expect(toJSON()).toBeNull()
  })
})
