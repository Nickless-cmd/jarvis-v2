import { act, fireEvent, render, waitFor } from '@testing-library/react-native'
import { MessageList } from './MessageList'
import { TilbagespolBanner } from './TilbagespolBanner'
import { Composer } from './Composer'
import type { ChatMessage } from '../lib/types'

/** Claude Desktop §8 på telefonen (19/9-2026). */
const m = (id: string, role: 'user' | 'assistant', content: string) =>
  ({ id, role, content, created_at: '2026-09-19T00:00:00Z' }) as ChatMessage

it('din besked har «Spol tilbage hertil», og den sender beskedens id', async () => {
  const onRewind = jest.fn()
  const s = await render(<MessageList messages={[m('m1', 'user', 'Hej'), m('m2', 'assistant', 'Svar')]} blocks={[]} onRewind={onRewind} />)
  await act(async () => { fireEvent.press(s.getByLabelText('Spol tilbage hertil')) })
  expect(onRewind).toHaveBeenCalledWith('m1')
})

it('en lokal (ikke-gemt) besked kan ikke spoles til', async () => {
  const s = await render(<MessageList messages={[m('local-123', 'user', 'Hej')]} blocks={[]} onRewind={() => {}} />)
  expect(s.queryByLabelText('Spol tilbage hertil')).toBeNull()
})

it('banneret lover det Claude Desktop lover — og Fortryd virker', async () => {
  const onFortryd = jest.fn()
  const s = await render(<TilbagespolBanner fjernet={3} fejl="" onFortryd={onFortryd} onLuk={() => {}} />)
  expect(s.getByText(/3 beskeder fjernet\. Dine filer er uændrede\./)).toBeTruthy()
  await act(async () => { fireEvent.press(s.getByLabelText('Fortryd')) })
  expect(onFortryd).toHaveBeenCalled()
})

it('skrivefeltet: «erstat» lægger beskeden ind i stedet for at tilføje, og kan tømme igen', async () => {
  const s = await render(<Composer onSend={jest.fn()} onStop={jest.fn()} indsaet={{ tekst: 'andet spørgsmål', n: 1, erstat: true }} />)
  await waitFor(() => expect(s.getByTestId('composer-input').props.value).toBe('andet spørgsmål'))
  await s.rerender(<Composer onSend={jest.fn()} onStop={jest.fn()} indsaet={{ tekst: '', n: 2, erstat: true }} />)
  await waitFor(() => expect(s.queryByTestId('composer-input')?.props.value ?? '').toBe(''))
})
