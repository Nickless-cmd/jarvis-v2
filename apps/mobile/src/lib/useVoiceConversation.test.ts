import { act, renderHook, waitFor } from '@testing-library/react-native'
import * as audio from 'expo-audio'
import { useVoiceConversation } from './useVoiceConversation'
import type { ApiConfig } from './types'

jest.mock('./voiceApi', () => ({
  transcribeAudio: jest.fn(async () => ({ status: 'ok', text: 'hej Jarvis' })),
  synthesizeTtsToFile: jest.fn(async () => ({ uri: 'file:///tts.mp3', provider: 'elevenlabs' })),
}))

const config = { apiBaseUrl: 'https://api.example.test', authToken: 'tok' } as ApiConfig
const deps = { status: 'idle', blocks: [], sendMessage: jest.fn(), extractText: () => '' }

/** Optager der tager tid at komme op — som en rigtig mikrofon gør. */
function slowRecorder(prepareMs = 30) {
  const rec = {
    uri: 'file:///cache/utterance.m4a',
    prepareToRecordAsync: jest.fn(() => new Promise<void>((r) => setTimeout(r, prepareMs))),
    record: jest.fn(),
    stop: jest.fn(async () => undefined),
  }
  ;(audio.useAudioRecorder as jest.Mock).mockReturnValue(rec)
  return rec
}

beforeEach(() => jest.clearAllMocks())

describe('push-to-talk', () => {
  // Fejlen: knappen blev sluppet FØR optageren var oppe. stopListening spurgte
  // React' tilstand, som stadig stod på 'idle', og gjorde derfor ingenting —
  // mikrofonen kørte videre bag et overlay der sagde «Lytter…». Et hurtigt
  // tryk er den mest almindelige måde at trykke på en knap.
  it('stopper optagelsen selv når knappen slippes før mikrofonen er oppe', async () => {
    const rec = slowRecorder(40)
    const { result } = await renderHook(() => useVoiceConversation(config, deps))

    await act(async () => {
      const started = result.current.startListening()
      result.current.stopListening()   // sluppet med det samme
      await started
    })

    await waitFor(() => expect(rec.stop).toHaveBeenCalled())
    expect(result.current.state).not.toBe('listening')
  })

  it('et normalt hold optager og sender lyden videre', async () => {
    const rec = slowRecorder(0)
    const { result } = await renderHook(() => useVoiceConversation(config, deps))

    await act(async () => { await result.current.startListening() })
    expect(rec.record).toHaveBeenCalled()
    expect(result.current.state).toBe('listening')

    await act(async () => { await result.current.stopListening() })
    expect(rec.stop).toHaveBeenCalled()
    expect(deps.sendMessage).toHaveBeenCalledWith('hej Jarvis')
  })

  // Uden denne vagt ville et dobbelt-tryk starte optager nummer to oven i den
  // første, og den første ville aldrig blive stoppet.
  it('starter ikke en optagelse oven i en der kører', async () => {
    const rec = slowRecorder(0)
    const { result } = await renderHook(() => useVoiceConversation(config, deps))
    await act(async () => { await result.current.startListening() })
    await act(async () => { await result.current.startListening() })
    expect(rec.record).toHaveBeenCalledTimes(1)
  })

  // Stilhed og en tom optagelse er to forskellige ting. Serveren ved hvilken
  // af dem det var; uden denne skelnen ville begge hedde «Jeg hørte ikke noget»
  // og en ægte fejl ville se ud som om man bare havde tiet.
  it('skelner en ubrugelig optagelse fra at man tav', async () => {
    slowRecorder(0)
    const api = jest.requireMock('./voiceApi') as { transcribeAudio: jest.Mock }
    api.transcribeAudio.mockResolvedValueOnce({ status: 'error', text: '', error: 'empty audio' })
    const { result } = await renderHook(() => useVoiceConversation(config, deps))
    await act(async () => { await result.current.startListening() })
    await act(async () => { await result.current.stopListening() })
    expect(result.current.problem).toMatch(/empty audio/)

    api.transcribeAudio.mockResolvedValueOnce({ status: 'ok', text: '   ' })
    await act(async () => { await result.current.startListening() })
    await act(async () => { await result.current.stopListening() })
    expect(result.current.problem).toMatch(/hørte ikke noget/)
  })

  it('siger hvorfor når mikrofonen er nægtet — i stedet for bare at gå i stå', async () => {
    slowRecorder(0)
    ;(audio.requestRecordingPermissionsAsync as jest.Mock).mockResolvedValueOnce({ granted: false })
    const { result } = await renderHook(() => useVoiceConversation(config, deps))
    await act(async () => { await result.current.startListening() })
    expect(result.current.problem).toMatch(/mikrofonen/i)
    expect(result.current.state).toBe('idle')
  })
})
