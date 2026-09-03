import { act, renderHook, waitFor } from '@testing-library/react-native'
import * as audio from 'expo-audio'
import { streamReducer, initialStreamState } from './streamReducer'
import { useVoiceConversation } from './useVoiceConversation'
import type { ApiConfig } from './types'

jest.mock('./voiceApi', () => ({
  transcribeAudio: jest.fn(async () => ({ status: 'ok', text: 'fortæl mig noget' })),
  synthesizeTtsToFile: jest.fn(async () => ({ uri: 'file:///tts.mp3', provider: 'elevenlabs' })),
}))

const config = { apiBaseUrl: 'https://api.example.test', authToken: 'tok' } as ApiConfig

/** Præcis den rækkefølge serveren sender i — målt mod api.srvlab.dk:
 *  message_start, en thinking-blok, så en tekst-blok der vokser i deltas,
 *  og først flere sekunder senere message_stop. */
const EVENTS: unknown[] = [
  { type: 'message_start', message: { id: 'r1', model: 'm', provider: 'p', lane: 'visible', usage: { input_tokens: 10 } } },
  { type: 'content_block_start', index: 0, content_block: { type: 'thinking', thinking: '' } },
  { type: 'content_block_delta', index: 0, delta: { type: 'thinking_delta', thinking: 'hmm…' } },
  { type: 'content_block_start', index: 1, content_block: { type: 'text', text: '' } },
  { type: 'content_block_delta', index: 1, delta: { type: 'text_delta', text: 'Først løsner du hjulet helt. ' } },
  { type: 'content_block_delta', index: 1, delta: { type: 'text_delta', text: 'Derefter tager du dækket af fælgen. ' } },
  { type: 'content_block_delta', index: 1, delta: { type: 'text_delta', text: 'Til sidst pumper du det op igen.' } },
]

const extractText = (blocks: { type?: string; text?: string }[]) =>
  (blocks || []).filter((b) => b?.type === 'text').map((b) => b?.text || '').join(' ').trim()

it('læser første sætning op MENS svaret stadig skrives', async () => {
  const rec = {
    uri: 'file:///cache/a.m4a',
    prepareToRecordAsync: jest.fn(async () => undefined),
    record: jest.fn(),
    stop: jest.fn(async () => undefined),
    getStatus: () => ({ isRecording: true, metering: -160, url: null }),
  }
  ;(audio.useAudioRecorder as jest.Mock).mockReturnValue(rec)
  const api = jest.requireMock('./voiceApi') as { synthesizeTtsToFile: jest.Mock }

  let state = initialStreamState()
  const deps = {
    get status() { return state.status },
    get blocks() { return state.blocks as never },
    sendMessage: jest.fn(),
    extractText: extractText as never,
  }

  const { result, rerender } = await renderHook(() => useVoiceConversation(config, deps))
  await act(async () => { await result.current.startListening() })
  await act(async () => { await result.current.stopListening() })
  expect(deps.sendMessage).toHaveBeenCalled()

  for (const ev of EVENTS) {
    state = streamReducer(state, ev as never)
    await act(async () => { rerender({}) })
  }

  // message_stop er IKKE sendt endnu. Hvis han først taler her, har man ventet
  // på hele svaret — og det er præcis fejlen Bjørn beskriver.
  await waitFor(() => expect(api.synthesizeTtsToFile).toHaveBeenCalled())
  expect(api.synthesizeTtsToFile.mock.calls[0][1]).toContain('Først løsner du hjulet helt.')
})

// Et svar med værktøjskald kommer i FLERE runder, og hver runde nulstiller
// blokkene. Optællingen af «hvor langt er jeg nået» pegede så ind i den forrige
// rundes tekst: intet blev sagt undervejs, og slutningen kunne blive læst op
// fra midten. Det er dét Bjørn hører som «den venter til hele svaret er landet».
it('taler stadig efter en ny runde med værktøjskald', async () => {
  const rec = {
    uri: 'file:///cache/a.m4a',
    prepareToRecordAsync: jest.fn(async () => undefined),
    record: jest.fn(),
    stop: jest.fn(async () => undefined),
    getStatus: () => ({ isRecording: true, metering: -160, url: null }),
  }
  ;(audio.useAudioRecorder as jest.Mock).mockReturnValue(rec)
  const api = jest.requireMock('./voiceApi') as { synthesizeTtsToFile: jest.Mock }
  api.synthesizeTtsToFile.mockClear()

  let state = initialStreamState()
  const deps = {
    get status() { return state.status },
    get blocks() { return state.blocks as never },
    sendMessage: jest.fn(),
    extractText: extractText as never,
  }
  const { result, rerender } = await renderHook(() => useVoiceConversation(config, deps))
  await act(async () => { await result.current.startListening() })
  await act(async () => { await result.current.stopListening() })

  const feed = async (evs: unknown[]) => {
    for (const ev of evs) {
      state = streamReducer(state, ev as never)
      await act(async () => { rerender({}) })
    }
  }

  // Runde 1: en kort melding, så et værktøjskald.
  await feed([
    { type: 'message_start', message: { id: 'r1', model: 'm', provider: 'p', lane: 'visible', usage: { input_tokens: 1 } } },
    { type: 'content_block_start', index: 0, content_block: { type: 'text', text: '' } },
    { type: 'content_block_delta', index: 0, delta: { type: 'text_delta', text: 'Jeg kigger lige efter i loggen. ' } },
  ])
  await waitFor(() => expect(api.synthesizeTtsToFile).toHaveBeenCalled())

  // Runde 2 starter forfra — blokkene nulstilles af message_start.
  await feed([
    { type: 'message_start', message: { id: 'r2', model: 'm', provider: 'p', lane: 'visible', usage: { input_tokens: 1 } } },
    { type: 'content_block_start', index: 0, content_block: { type: 'text', text: '' } },
    { type: 'content_block_delta', index: 0, delta: { type: 'text_delta', text: 'Der står tre fejl fra i nat. ' } },
  ])

  await waitFor(() => expect(api.synthesizeTtsToFile.mock.calls.length).toBeGreaterThanOrEqual(2))
  const spoken = api.synthesizeTtsToFile.mock.calls.map((c: unknown[]) => c[1] as string)
  expect(spoken[0]).toContain('Jeg kigger lige efter i loggen.')
  expect(spoken[1]).toContain('Der står tre fejl fra i nat.')
})
