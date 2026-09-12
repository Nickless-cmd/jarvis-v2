import type { VoiceState } from './useVoiceConversation'

export function voiceStatusCopy(input: { state: VoiceState; canInterrupt?: boolean }) {
  if (input.state === 'listening') return { primary: 'Jeg lytter', hint: 'Tal frit' }
  if (input.state === 'transcribing') return { primary: 'Hører hvad du sagde', hint: 'Lyden bliver gjort til tekst' }
  if (input.state === 'thinking') return { primary: 'Tænker', hint: 'Jarvis arbejder på svaret' }
  if (input.state === 'speaking') return { primary: 'Taler', action: input.canInterrupt ? 'Afbryd' : '', hint: 'Tryk for at afbryde' }
  return {
    primary: '',
    hint: 'Tal frit - jeg sender når du holder pause'
  }
}
