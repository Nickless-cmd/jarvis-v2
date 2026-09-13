import { voiceStatusCopy } from './voiceUiState'

it('turns voice runtime state into concise mobile copy', () => {
  expect(voiceStatusCopy({ state: 'listening' }).primary).toBe('Jeg lytter')
  expect(voiceStatusCopy({ state: 'speaking', canInterrupt: true }).action).toBe('Afbryd')
  expect(voiceStatusCopy({ state: 'idle' }).hint).toContain('Tal frit')
})

it('covers every voice state with primary copy', () => {
  expect(voiceStatusCopy({ state: 'idle' }).primary).toBe('Klar')
  expect(voiceStatusCopy({ state: 'listening' }).primary).toBe('Jeg lytter')
  expect(voiceStatusCopy({ state: 'transcribing' }).primary).toBe('Forstår lyden')
  expect(voiceStatusCopy({ state: 'thinking' }).primary).toBe('Tænker')
  expect(voiceStatusCopy({ state: 'speaking' }).primary).toBe('Taler')
})

it('can render voice copy through an English translator', () => {
  const dict: Record<string, string> = {
    'voice.idle.primary': 'Ready',
    'voice.idle.hint': 'Speak freely - I send when you pause',
    'voice.listening.primary': 'Listening',
    'voice.listening.hint': 'Speak freely',
    'voice.transcribing.primary': 'Understanding audio',
    'voice.transcribing.hint': 'Turning audio into text',
    'voice.thinking.primary': 'Thinking',
    'voice.thinking.hint': 'Jarvis is working on the answer',
    'voice.speaking.primary': 'Speaking',
    'voice.speaking.action': 'Interrupt',
    'voice.speaking.hint': 'Tap to interrupt',
  }
  const t = (key: string) => dict[key] ?? key

  expect(voiceStatusCopy({ state: 'listening' }, t).primary).toBe('Listening')
  expect(voiceStatusCopy({ state: 'speaking', canInterrupt: true }, t).action).toBe('Interrupt')
})
