import { fireEvent, render } from '@testing-library/react-native'
import { KoeChip } from './KoeChip'

const items = [
  { id: 1, sessionId: 'a', text: 'første besked' },
  { id: 2, sessionId: 'a', text: 'anden besked' },
]

it('viser alle ventende beskeder og giver hver sin rediger, flyt, send og fjern handling', async () => {
  const onEdit = jest.fn()
  const onMove = jest.fn()
  const onRemove = jest.fn()
  const onSendNow = jest.fn()
  const s = await render(<KoeChip items={items} busy canSteer error=""
    onEdit={onEdit} onMove={onMove} onRemove={onRemove} onSendNow={onSendNow} />)
  expect(s.getByText('I kø · 2')).toBeTruthy()
  expect(s.getByText('første besked')).toBeTruthy()
  expect(s.getByText('anden besked')).toBeTruthy()
  await fireEvent.press(s.getAllByLabelText('Flyt op')[1]!)
  expect(onMove).toHaveBeenCalledWith(2, -1)
  await fireEvent.press(s.getAllByLabelText('Send nu til aktivt run')[0]!)
  expect(onSendNow).toHaveBeenCalledWith(1)
  await fireEvent.press(s.getAllByLabelText('Rediger follow-up')[1]!)
  await fireEvent.changeText(s.getByLabelText('Rediger follow-up-tekst'), 'rettet besked')
  await fireEvent.press(s.getByLabelText('Gem ændring'))
  expect(onEdit).toHaveBeenCalledWith(2, 'rettet besked')
  await fireEvent.press(s.getAllByLabelText('Fjern fra kø')[0]!)
  expect(onRemove).toHaveBeenCalledWith(1)
})
