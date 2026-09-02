import { act, fireEvent, render, waitFor } from '@testing-library/react-native'
import { Composer } from './Composer'

describe('Composer', () => {
  it('trims input, sends it, and clears the field', async () => {
    const onSend = jest.fn()
    const screen = await render(<Composer onSend={onSend} onStop={jest.fn()} />)

    await waitFor(() => expect(screen.getByTestId('composer-input')).toBeTruthy())

    await act(async () => {
      screen.getByTestId('composer-input').props.onChangeText('  Hej Jarvis  ')
    })
    await waitFor(() => expect(screen.getByTestId('composer-input').props.value).toBe('  Hej Jarvis  '))
    await act(async () => {
      fireEvent.press(screen.getByTestId('composer-button'))
    })

    expect(onSend).toHaveBeenCalledWith('Hej Jarvis')
    await waitFor(() => expect(screen.getByTestId('composer-input').props.value).toBe(''))
  })

  it('keeps the draft when async send fails', async () => {
    const onSend = jest.fn().mockRejectedValue(new Error('session create failed'))
    const screen = await render(<Composer onSend={onSend} onStop={jest.fn()} />)

    await waitFor(() => expect(screen.getByTestId('composer-input')).toBeTruthy())

    await act(async () => {
      screen.getByTestId('composer-input').props.onChangeText('Hej Jarvis')
    })
    await act(async () => {
      fireEvent.press(screen.getByTestId('composer-button'))
    })

    expect(onSend).toHaveBeenCalledWith('Hej Jarvis')
    expect(screen.getByTestId('composer-input').props.value).toBe('Hej Jarvis')
  })

  it('shows stop while working and calls onStop instead of sending', async () => {
    const onSend = jest.fn()
    const onStop = jest.fn()
    const screen = await render(<Composer working onSend={onSend} onStop={onStop} />)

    await waitFor(() => expect(screen.getByTestId('composer-input')).toBeTruthy())

    await act(async () => {
      screen.getByTestId('composer-input').props.onChangeText('Hej')
    })
    await waitFor(() => expect(screen.getByTestId('composer-input').props.value).toBe('Hej'))
    await act(async () => {
      fireEvent.press(screen.getByTestId('composer-button'))
    })

    expect(onSend).not.toHaveBeenCalled()
    expect(onStop).toHaveBeenCalledTimes(1)
  })

  it('does not send blank or disabled input', async () => {
    const onSend = jest.fn()
    const screen = await render(<Composer disabled onSend={onSend} onStop={jest.fn()} />)

    await waitFor(() => expect(screen.getByTestId('composer-input')).toBeTruthy())

    await act(async () => {
      screen.getByTestId('composer-input').props.onChangeText('   ')
    })
    await waitFor(() => expect(screen.getByTestId('composer-input').props.value).toBe('   '))
    await act(async () => {
      fireEvent.press(screen.getByTestId('composer-button'))
    })
    await act(async () => {
      screen.getByTestId('composer-input').props.onChangeText('Hej')
    })
    await waitFor(() => expect(screen.getByTestId('composer-input').props.value).toBe('Hej'))
    await act(async () => {
      fireEvent.press(screen.getByTestId('composer-button'))
    })

    expect(onSend).not.toHaveBeenCalled()
  })
})
