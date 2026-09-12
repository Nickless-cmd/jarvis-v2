import * as SecureStore from 'expo-secure-store'
import { act, fireEvent, render, waitFor } from '@testing-library/react-native'
import { ThinkingSummary } from './ThinkingSummary'
import { getMessageReasoning } from '../lib/apiClient'

jest.mock('expo-secure-store', () => {
  let store: Record<string, string> = {}
  return {
    getItemAsync: jest.fn(async (k: string) => store[k] ?? null),
    setItemAsync: jest.fn(async (k: string, v: string) => { store[k] = v }),
    __reset: () => { store = {} }
  }
})

// Boblen kan rendere uden en provider; her giver vi den en config, så kaldet
// til serveren faktisk kan ske.
jest.mock('../state/AuthContext', () => ({
  useAuthOptional: () => ({ config: { apiBaseUrl: 'http://x', authToken: 't' } })
}))

jest.mock('../lib/apiClient', () => ({
  getMessageReasoning: jest.fn(async () => 'HELE STROEMMEN')
}))

const hentMock = getMessageReasoning as jest.MockedFunction<typeof getMessageReasoning>
const noegle = 'jarvis.mobile.fullThinking'
const nulstil = () => (SecureStore as unknown as { __reset: () => void }).__reset()

/** Åbn linjen. State-opdateringen skal pakkes i act — ellers ser vi den ikke. */
const aabn = async (s: { getByTestId: (id: string) => unknown }) => {
  await act(async () => { fireEvent.press(s.getByTestId('thinking-summary') as never) })
}

beforeEach(() => {
  nulstil()
  hentMock.mockClear()
  hentMock.mockResolvedValue('HELE STROEMMEN')
})

describe('ThinkingSummary — hele strømmen er et tilvalg', () => {
  it('henter IKKE fra serveren når tilvalget er slået fra', async () => {
    const s = await render(<ThinkingSummary seconds={14} text="halen" messageId="m1" />)
    await aabn(s)
    // Standarden er ChatGPT-agtig: halen er nok, og der hentes intet.
    expect(s.getByText('halen')).toBeTruthy()
    expect(hentMock).not.toHaveBeenCalled()
  })

  it('henter og viser HELE strømmen når tilvalget er slået til', async () => {
    await SecureStore.setItemAsync(noegle, '1')
    const s = await render(<ThinkingSummary seconds={14} text="halen" messageId="m1" />)
    await aabn(s)
    await waitFor(() => expect(s.getByText('HELE STROEMMEN')).toBeTruthy())
    expect(hentMock).toHaveBeenCalledWith(
      expect.objectContaining({ apiBaseUrl: 'http://x' }),
      'm1'
    )
  })

  it('beholder halen hvis hentningen fejler', async () => {
    await SecureStore.setItemAsync(noegle, '1')
    hentMock.mockRejectedValueOnce(new Error('netvaerk nede'))
    const s = await render(<ThinkingSummary seconds={14} text="halen" messageId="m1" />)
    await aabn(s)
    await waitFor(() => expect(hentMock).toHaveBeenCalled())
    // En fejl må aldrig fjerne noget brugeren allerede kunne se.
    expect(s.getByText('halen')).toBeTruthy()
  })

  it('henter ikke uden messageId — der er intet at slå op', async () => {
    await SecureStore.setItemAsync(noegle, '1')
    const s = await render(<ThinkingSummary seconds={14} text="halen" />)
    await aabn(s)
    expect(hentMock).not.toHaveBeenCalled()
    expect(s.getByText('halen')).toBeTruthy()
  })
})
