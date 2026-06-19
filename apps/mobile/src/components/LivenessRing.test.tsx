import { render } from '@testing-library/react-native'
import { LivenessRing } from './LivenessRing'

describe('LivenessRing', () => {
  it('rendrer i alle tre tilstande uden crash', async () => {
    for (const status of ['idle', 'working', 'error'] as const) {
      const { toJSON } = await render(<LivenessRing status={status} />)
      expect(toJSON()).toBeTruthy()
    }
  })
})
