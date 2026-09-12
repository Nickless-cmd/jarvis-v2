import { act, renderHook } from '@testing-library/react-native'
import * as audio from 'expo-audio'
import { useComposerDictation } from './useComposerDictation'

jest.mock('./voiceApi', () => ({
  transcribeAudio: jest.fn(async () => ({ status: 'ok', text: 'dikteret tekst' })),
}))

const config = { apiBaseUrl: 'https://api.example.test', authToken: 'tok' }

beforeEach(() => jest.clearAllMocks())

it('optager én ytring og returnerer redigerbar tekst uden at sende', async () => {
  const recorder = {
    uri: 'file:///cache/dictation.m4a',
    prepareToRecordAsync: jest.fn(async () => undefined),
    record: jest.fn(),
    stop: jest.fn(async () => undefined),
    getStatus: jest.fn(() => ({ metering: -25 })),
  }
  ;(audio.useAudioRecorder as jest.Mock).mockReturnValue(recorder)
  const { result } = await renderHook(() => useComposerDictation(config))

  await act(async () => { await result.current.start() })
  expect(result.current.state).toBe('recording')
  await act(async () => { await result.current.stop() })

  expect(result.current.state).toBe('idle')
  expect(result.current.text).toBe('dikteret tekst')
})

it('annullerer en aktiv optagelse uden transskription', async () => {
  const recorder = {
    uri: 'file:///cache/dictation.m4a',
    prepareToRecordAsync: jest.fn(async () => undefined),
    record: jest.fn(), stop: jest.fn(async () => undefined),
    getStatus: jest.fn(() => ({ metering: -160 })),
  }
  ;(audio.useAudioRecorder as jest.Mock).mockReturnValue(recorder)
  const api = jest.requireMock('./voiceApi') as { transcribeAudio: jest.Mock }
  const { result } = await renderHook(() => useComposerDictation(config))
  await act(async () => { await result.current.start() })
  await act(async () => { await result.current.cancel() })
  expect(recorder.stop).toHaveBeenCalled()
  expect(api.transcribeAudio).not.toHaveBeenCalled()
  expect(result.current.state).toBe('idle')
})

it('ignorerer et sent STT-resultat efter annullering', async () => {
  let finish: ((value: { status: string; text: string }) => void) | undefined
  const api = jest.requireMock('./voiceApi') as { transcribeAudio: jest.Mock }
  api.transcribeAudio.mockImplementationOnce(() => new Promise((resolve) => { finish = resolve }))
  const recorder = {
    uri: 'file:///cache/dictation.m4a',
    prepareToRecordAsync: jest.fn(async () => undefined), record: jest.fn(),
    stop: jest.fn(async () => undefined), getStatus: jest.fn(() => ({ metering: -20 })),
  }
  ;(audio.useAudioRecorder as jest.Mock).mockReturnValue(recorder)
  const { result } = await renderHook(() => useComposerDictation(config))
  await act(async () => { await result.current.start() })
  let stopping: Promise<void>
  await act(async () => { stopping = result.current.stop() })
  await act(async () => { await result.current.cancel() })
  await act(async () => { finish?.({ status: 'ok', text: 'for sent' }); await stopping! })
  expect(result.current.text).toBe('')
  expect(result.current.state).toBe('idle')
})
