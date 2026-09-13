import type { VoiceState } from './useVoiceConversation'

type Translator = (key: string) => string

const DA: Record<string, string> = {
  'voice.idle.primary': 'Klar',
  'voice.idle.hint': 'Tal frit - jeg sender når du holder pause',
  'voice.listening.primary': 'Jeg lytter',
  'voice.listening.hint': 'Tal frit',
  'voice.transcribing.primary': 'Forstår lyden',
  'voice.transcribing.hint': 'Lyden bliver gjort til tekst',
  'voice.thinking.primary': 'Tænker',
  'voice.thinking.hint': 'Jarvis arbejder på svaret',
  'voice.speaking.primary': 'Taler',
  'voice.speaking.action': 'Afbryd',
  'voice.speaking.hint': 'Tryk for at afbryde',
}

const fallbackT: Translator = (key) => DA[key] ?? key

export function voiceStatusCopy(input: { state: VoiceState; canInterrupt?: boolean }, t: Translator = fallbackT) {
  if (input.state === 'listening') return { primary: t('voice.listening.primary'), hint: t('voice.listening.hint') }
  if (input.state === 'transcribing') return { primary: t('voice.transcribing.primary'), hint: t('voice.transcribing.hint') }
  if (input.state === 'thinking') return { primary: t('voice.thinking.primary'), hint: t('voice.thinking.hint') }
  if (input.state === 'speaking') {
    return {
      primary: t('voice.speaking.primary'),
      action: input.canInterrupt ? t('voice.speaking.action') : '',
      hint: t('voice.speaking.hint'),
    }
  }
  return {
    primary: t('voice.idle.primary'),
    hint: t('voice.idle.hint')
  }
}
