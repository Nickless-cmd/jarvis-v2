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
    // Standarden er hænderfri; dét her handler om push-to-talk, hvor et slip
    // SKAL stoppe optagelsen — også hvis det kom før mikrofonen var oppe.
    await act(async () => { result.current.setMode('push') })

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

describe('oplæsning mens svaret skrives', () => {
  const text = (blocks: { type?: string; text?: string }[]) =>
    blocks.filter((b) => b.type === 'text').map((b) => b.text || '').join(' ').trim()

  function live() {
    let cur: { status: string; blocks: { type: string; text: string }[] } =
      { status: 'idle', blocks: [] }
    const d = {
      get status() { return cur.status },
      get blocks() { return cur.blocks as never },
      sendMessage: jest.fn(),
      extractText: text as never,
    }
    return { d, set: (status: string, t: string) => { cur = { status, blocks: t ? [{ type: 'text', text: t }] : [] } } }
  }

  // Kernen i ønsket: han skal begynde at læse op MENS han skriver, ikke først
  // når hele svaret står færdigt.
  it('siger første sætning før svaret er færdigt', async () => {
    slowRecorder(0)
    const api = jest.requireMock('./voiceApi') as { synthesizeTtsToFile: jest.Mock }
    const { d, set } = live()
    const { result, rerender } = await renderHook(() => useVoiceConversation(config, d))
    await act(async () => { await result.current.startListening() })
    await act(async () => { await result.current.stopListening() })

    set('working', 'Jeg har kigget på containeren i nat. Og der er')
    await act(async () => { rerender({}) })

    await waitFor(() => expect(api.synthesizeTtsToFile).toHaveBeenCalled())
    expect(api.synthesizeTtsToFile.mock.calls[0][1]).toBe('Jeg har kigget på containeren i nat.')
  })

  it('siger ikke den samme sætning igen når resten kommer', async () => {
    slowRecorder(0)
    const api = jest.requireMock('./voiceApi') as { synthesizeTtsToFile: jest.Mock }
    const { d, set } = live()
    const { result, rerender } = await renderHook(() => useVoiceConversation(config, d))
    await act(async () => { await result.current.startListening() })
    await act(async () => { await result.current.stopListening() })

    set('working', 'Første hele sætning står her nu. Anden')
    await act(async () => { rerender({}) })
    set('working', 'Første hele sætning står her nu. Anden hele sætning er også klar nu.')
    await act(async () => { rerender({}) })
    set('done', '')
    await act(async () => { rerender({}) })

    await waitFor(() => expect(api.synthesizeTtsToFile.mock.calls.length).toBeGreaterThanOrEqual(2))
    const spoken = api.synthesizeTtsToFile.mock.calls.map((c: unknown[]) => c[1] as string)
    expect(spoken[0]).toBe('Første hele sætning står her nu.')
    expect(spoken[1]).toBe('Anden hele sætning er også klar nu.')
    expect(spoken.join(' ')).not.toMatch(/Første hele sætning står her nu\..*Første hele/)
  })
})

describe('hænderfri holder samtalen i gang', () => {
  // En pause hvor man tænker må ikke afslutte samtalen. Men mikrofonen må
  // heller ikke stå åben i stuen resten af dagen, så der er en grænse.
  it('lytter igen efter én tom runde — og holder så inde', async () => {
    const rec = slowRecorder(0)
    const api = jest.requireMock('./voiceApi') as { transcribeAudio: jest.Mock }
    const { result } = await renderHook(() => useVoiceConversation(config, deps))
    await act(async () => { result.current.enter() })

    api.transcribeAudio.mockResolvedValue({ status: 'ok', text: '' })
    await act(async () => { await result.current.startListening() })
    await act(async () => { await result.current.stopListening() })

    await waitFor(() => expect(rec.record).toHaveBeenCalledTimes(2))
    await act(async () => { await result.current.stopListening() })

    // Anden tomme runde: nu holder den inde i stedet for at blive ved.
    await new Promise((r) => setTimeout(r, 600))
    expect(rec.record).toHaveBeenCalledTimes(2)
    expect(result.current.problem).toMatch(/hørte ikke noget/)
  })
})
