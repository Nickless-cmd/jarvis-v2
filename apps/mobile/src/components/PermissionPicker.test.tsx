import { fireEvent, render } from '@testing-library/react-native'
import { PermissionPicker } from './PermissionPicker'

it('viser de to ærlige permission-niveauer og vælger fuld adgang', async () => {
  const onSelect = jest.fn()
  const onClose = jest.fn()
  const screen = await render(
    <PermissionPicker
      open
      selected="ask"
      onSelect={onSelect}
      onClose={onClose}
    />
  )

  expect(screen.getByText('Spørg først')).toBeTruthy()
  expect(screen.getByText('Fuld adgang')).toBeTruthy()
  fireEvent.press(screen.getByText('Fuld adgang'))

  expect(onSelect).toHaveBeenCalledWith('trust')
  expect(onClose).toHaveBeenCalledTimes(1)
})
