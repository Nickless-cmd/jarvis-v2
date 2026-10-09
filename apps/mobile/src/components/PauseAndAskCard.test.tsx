import { fireEvent, render } from '@testing-library/react-native'
import { PauseAndAskCard } from './PauseAndAskCard'

const ask = {
  question: 'Hvilke flader?', options: ['Desk', 'Mobil', 'Web UI'],
  allowMultiple: false, context: '', urgency: 'normal' as const,
}

test('enkeltvalg vises uden cirkler og sendes først ved Send svar', async () => {
  const send = jest.fn()
  const view = await render(<PauseAndAskCard ask={ask} onAnswer={send} />)
  expect(view.queryByTestId('pauseask-circle')).toBeNull()
  await fireEvent.press(view.getByText('Desk'))
  expect(send).not.toHaveBeenCalled()
  await fireEvent.press(view.getByText('Send svar'))
  expect(send).toHaveBeenCalledWith('Desk')
})

test('flere valg får cirkler og sendes som ét svar', async () => {
  const send = jest.fn()
  const view = await render(<PauseAndAskCard ask={{ ...ask, allowMultiple: true }} onAnswer={send} />)
  expect(view.getAllByTestId('pauseask-circle')).toHaveLength(3)
  await fireEvent.press(view.getByText('Desk'))
  await fireEvent.press(view.getByText('Mobil'))
  await fireEvent.press(view.getByText('Send svar'))
  expect(send).toHaveBeenCalledWith('Jeg vælger:\n- Desk\n- Mobil')
})
