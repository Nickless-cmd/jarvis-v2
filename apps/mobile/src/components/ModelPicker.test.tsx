import { fireEvent, render } from '@testing-library/react-native'
import { ModelPicker } from './ModelPicker'

const choices = [{ model: '', providerChoice: 'deepseek', label: 'Deepseek' }]

it('viser thinking men ikke permissions', async () => {
  const onThinkingModeChange = jest.fn()
  const screen = await render(
    <ModelPicker
      open
      choices={choices}
      selectedLabel="Deepseek"
      thinkingMode="think"
      onThinkingModeChange={onThinkingModeChange}
      onSelect={jest.fn()}
      onClose={jest.fn()}
    />
  )

  fireEvent.press(screen.getByText('Fast'))

  expect(onThinkingModeChange).toHaveBeenCalledWith('fast')
  expect(screen.queryByText('Godkendelser')).toBeNull()
  expect(screen.queryByText('Trust')).toBeNull()
})
