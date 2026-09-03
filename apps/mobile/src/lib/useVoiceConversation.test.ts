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

describe('svaret bliver talt', () => {
  const text = (blocks: { type?: string; text?: string }[]) =>
    blocks.filter((b) => b.type === 'text').map((b) => b.text || '').join(' ').trim()

  /** Klienten rydder blokkene i SAMME opdatering som status bliver 'done' —
   *  svaret flyttes over i den persisterede historik. Læser man først dér, er
   *  der intet tilbage, og stemmen tier mens svaret står i chatten. */
  function play(statuses: { status: string; blocks: { type: string; text: string }[] }[]) {
    const api = jest.requireMock('./voiceApi') as { synthesizeTtsToFile: jest.Mock }
    return { api, statuses }
  }

  it('taler svaret selv om blokkene ryddes i samme øjeblik som status bliver done', async () => {
    slowRecorder(0)
    const { api } = play([])
    let live: { status: string; blocks: { type: string; text: string }[] } =
      { status: 'idle', blocks: [] }
    const d = {
      get status() { return live.status },
      get blocks() { return live.blocks as never },
      sendMessage: jest.fn(),
      extractText: text as never,
    }
    const { result, rerender } = await renderHook(() => useVoiceConversation(config, d))

    await act(async () => { await result.current.startListening() })
    await act(async () => { await result.current.stopListening() })
    expect(d.sendMessage).toHaveBeenCalledWith('hej Jarvis')

    live = { status: 'working', blocks: [{ type: 'text', text: 'Ja, det kan jeg godt.' }] }
    await act(async () => { rerender({}) })
    // Præcis som klienten gør det: status og tømning i ÉN opdatering.
    live = { status: 'done', blocks: [] }
    await act(async () => { rerender({}) })

    await waitFor(() => expect(api.synthesizeTtsToFile).toHaveBeenCalled())
    expect(api.synthesizeTtsToFile.mock.calls[0][1]).toContain('Ja, det kan jeg godt.')
  })

  // Et afbrudt run efterlod før stemmen ventende for evigt — og NÆSTE svar
  // ville så blive talt i stedet for dette.
  it('bliver ikke hængende når et run afbrydes', async () => {
    slowRecorder(0)
    const api = jest.requireMock('./voiceApi') as { synthesizeTtsToFile: jest.Mock }
    let live: { status: string; blocks: { type: string; text: string }[] } =
      { status: 'idle', blocks: [] }
    const d = {
      get status() { return live.status },
      get blocks() { return live.blocks as never },
      sendMessage: jest.fn(),
      extractText: text as never,
    }
    const { result, rerender } = await renderHook(() => useVoiceConversation(config, d))
    await act(async () => { await result.current.startListening() })
    await act(async () => { await result.current.stopListening() })

    live = { status: 'working', blocks: [{ type: 'text', text: 'Halvt svar' }] }
    await act(async () => { rerender({}) })
    live = { status: 'interrupted', blocks: [] }
    await act(async () => { rerender({}) })

    await waitFor(() => expect(api.synthesizeTtsToFile).toHaveBeenCalled())
    expect(api.synthesizeTtsToFile.mock.calls[0][1]).toContain('Halvt svar')
  })
})
