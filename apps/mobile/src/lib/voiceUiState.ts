import type { VoiceMode, VoiceState } from './useVoiceConversation'

export function voiceStatusCopy(input: { state: VoiceState; mode: VoiceMode; canInterrupt?: boolean }) {
  if (input.state === 'listening') return { primary: 'Jeg lytter', hint: input.mode === 'push' ? 'Slip for at sende' : 'Tal frit' }
  if (input.state === 'transcribing') return { primary: 'Hører hvad du sagde', hint: 'Lyden bliver gjort til tekst' }
  if (input.state === 'thinking') return { primary: 'Tænker', hint: 'Jarvis arbejder på svaret' }
  if (input.state === 'speaking') return { primary: 'Taler', action: input.canInterrupt ? 'Afbryd' : '', hint: 'Tryk for at afbryde' }
  return {
    primary: '',
    hint: input.mode === 'push' ? 'Hold kuglen mens du taler' : 'Tal frit - jeg sender når du holder pause'
  }
}
