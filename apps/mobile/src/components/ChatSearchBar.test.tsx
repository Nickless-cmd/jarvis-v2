import { act, fireEvent, render } from '@testing-library/react-native'
import { ChatSearchBar } from './ChatSearchBar'
import type { ChatMessage } from '../lib/types'

const m = (id: string, content: string): ChatMessage =>
  ({ id, role: 'assistant', content, created_at: '' }) as ChatMessage

const BESKEDER = [m('1', 'noget om broen'), m('2', 'USB-kortet faldt af'), m('3', 'broen igen')]

const vis = async () => {
  const onJump = jest.fn()
  const onClose = jest.fn()
  const screen = await render(
    <ChatSearchBar visible messages={BESKEDER} onJump={onJump} onClose={onClose} />
  )
  return { screen, onJump, onClose }
}

it('viser intet før man har skrevet noget brugbart', async () => {
  const { screen } = await vis()
  expect(screen.queryByTestId('chat-search-count')).toBeNull()
})

it('tæller træf — «1 af 2», ikke bare «fundet»', async () => {
  const { screen } = await vis()
  await act(async () => { fireEvent.changeText(screen.getByTestId('chat-search-input'), 'broen') })
  expect(screen.getByText('1 af 2')).toBeTruthy()
})

it('siger ærligt at der ingen er', async () => {
  const { screen } = await vis()
  await act(async () => { fireEvent.changeText(screen.getByTestId('chat-search-input'), 'findesikke') })
  expect(screen.getByText('ingen')).toBeTruthy()
})

it('springer til beskeden — man vil se svaret DÉR hvor det står', async () => {
  const { screen, onJump } = await vis()
  await act(async () => { fireEvent.changeText(screen.getByTestId('chat-search-input'), 'broen') })
  await act(async () => { fireEvent.press(screen.getByTestId('chat-search-next')) })
  expect(onJump).toHaveBeenCalledWith('3')
})

it('ombryder ved sidste træf i stedet for at gå i stå', async () => {
  const { screen, onJump } = await vis()
  await act(async () => { fireEvent.changeText(screen.getByTestId('chat-search-input'), 'broen') })
  await act(async () => { fireEvent.press(screen.getByTestId('chat-search-next')) })
  await act(async () => { fireEvent.press(screen.getByTestId('chat-search-next')) })
  expect(onJump).toHaveBeenLastCalledWith('1')
})

it('viser uddraget, så man kan genkende træffet uden at springe', async () => {
  const { screen } = await vis()
  await act(async () => { fireEvent.changeText(screen.getByTestId('chat-search-input'), 'USB') })
  expect(screen.getByTestId('chat-search-snippet')).toBeTruthy()
})

it('nulstiller feltet når man lukker', async () => {
  const { screen, onClose } = await vis()
  await act(async () => { fireEvent.changeText(screen.getByTestId('chat-search-input'), 'broen') })
  await act(async () => { fireEvent.press(screen.getByTestId('chat-search-close')) })
  expect(onClose).toHaveBeenCalled()
})

it('er helt væk når den ikke er åben', async () => {
  const screen = await render(
    <ChatSearchBar visible={false} messages={BESKEDER} onJump={jest.fn()} onClose={jest.fn()} />
  )
  expect(screen.queryByTestId('chat-search')).toBeNull()
})
