import { fireEvent, render } from '@testing-library/react-native'
import { ModelPicker } from './ModelPicker'

const choices = [{ model: '', providerChoice: 'deepseek', label: 'Deepseek' }]

it('viser thinking og approval controls', async () => {
  const onThinkingModeChange = jest.fn()
  const onApprovalModeChange = jest.fn()
  const screen = await render(
    <ModelPicker
      open
      choices={choices}
      selectedLabel="Deepseek"
      thinkingMode="think"
      approvalMode="ask"
      onThinkingModeChange={onThinkingModeChange}
      onApprovalModeChange={onApprovalModeChange}
      onSelect={jest.fn()}
      onClose={jest.fn()}
    />
  )

  fireEvent.press(screen.getByText('Fast'))
  fireEvent.press(screen.getByText('Trust'))

  expect(onThinkingModeChange).toHaveBeenCalledWith('fast')
  expect(onApprovalModeChange).toHaveBeenCalledWith('trust')
})
