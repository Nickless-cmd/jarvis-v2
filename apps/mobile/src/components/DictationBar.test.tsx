import { act, fireEvent, render, waitFor } from '@testing-library/react-native'
import { DictationBar } from './DictationBar'

it('viser optagetid og kan stoppe eller annullere', async () => {
  const onStop = jest.fn()
  const onCancel = jest.fn()
  const screen = await render(
    <DictationBar state="recording" elapsedMs={4200} onStop={onStop} onCancel={onCancel} />
  )
  expect(screen.getByText('0:04')).toBeTruthy()
  expect(screen.getByTestId('dictation-level')).toBeTruthy()
  await act(async () => {
    fireEvent.press(screen.getByLabelText('Stop diktering'))
    fireEvent.press(screen.getByLabelText('Annuller diktering'))
  })
  expect(onStop).toHaveBeenCalledTimes(1)
  expect(onCancel).toHaveBeenCalledTimes(1)
})

it('viser transskriptionsstatus uden en ekstra modal', async () => {
  const screen = await render(
    <DictationBar state="transcribing" elapsedMs={0} onStop={jest.fn()} onCancel={jest.fn()} />
  )
  await waitFor(() => expect(screen.getByText('Transskriberer...')).toBeTruthy())
})
