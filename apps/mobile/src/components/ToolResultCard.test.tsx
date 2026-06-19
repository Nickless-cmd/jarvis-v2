import { render } from '@testing-library/react-native'
import { ToolResultCard } from './ToolResultCard'

describe('ToolResultCard', () => {
  it('rendrer fra content + fra live-props uden crash', async () => {
    expect((await render(<ToolResultCard content="[tool_result] read_file: ok" />)).toJSON()).toBeTruthy()
    expect((await render(<ToolResultCard toolName="bash" body="hej" running />)).toJSON()).toBeTruthy()
  })
})
