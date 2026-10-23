import { apiFetch, type ApiConfig } from './api'

/** Svarstil pr. bruger — serveren gemmer den og minder Jarvis om den hver tur. */
export type Svarstil = 'balanced' | 'concise' | 'detailed' | 'technical'
export type ChatStyle = {
  tone: 'adaptive' | 'warm' | 'direct' | 'playful'
  emoji: 'adaptive' | 'rare' | 'expressive'
  profanity: 'adaptive' | 'avoid' | 'comfortable'
  visuals: 'adaptive' | 'plain' | 'rich'
  questions: 'adaptive' | 'rare' | 'curious'
}
export type SvarPreferences = { outputStyle: Svarstil; chatStyle: ChatStyle }

export const DEFAULT_CHAT_STYLE: ChatStyle = {
  tone: 'adaptive', emoji: 'adaptive', profanity: 'adaptive',
  visuals: 'adaptive', questions: 'adaptive',
}

export const SVARSTILE: Array<{ value: Svarstil; navn: string; forklaring: string }> = [
  { value: 'balanced', navn: 'Normal', forklaring: 'Som han selv finder passende' },
  { value: 'concise', navn: 'Kort', forklaring: 'Korte, tætte svar uden indledning' },
  { value: 'detailed', navn: 'Uddybende', forklaring: 'Ræsonnement, kanttilfælde og eksempler' },
  { value: 'technical', navn: 'Teknisk', forklaring: 'Kode, stier og file:linje frem for prosa' },
]

export async function hentSvarstil(config: ApiConfig): Promise<Svarstil> {
  const r = await apiFetch<{ output_style?: string }>(config, '/api/preferences')
  const v = r.output_style as Svarstil
  return SVARSTILE.some((s) => s.value === v) ? v : 'balanced'
}

export async function hentSvarPreferences(config: ApiConfig): Promise<SvarPreferences> {
  const r = await apiFetch<{ output_style?: string; chat_style?: Partial<ChatStyle> }>(config, '/api/preferences')
  const outputStyle = SVARSTILE.some((s) => s.value === r.output_style) ? r.output_style as Svarstil : 'balanced'
  return { outputStyle, chatStyle: { ...DEFAULT_CHAT_STYLE, ...(r.chat_style ?? {}) } }
}

export async function saetSvarstil(config: ApiConfig, stil: Svarstil): Promise<void> {
  await apiFetch(config, '/api/preferences', { method: 'POST', body: { output_style: stil } })
}

export async function saetChatStyle(config: ApiConfig, update: Partial<ChatStyle>): Promise<void> {
  await apiFetch(config, '/api/preferences', { method: 'POST', body: { chat_style: update } })
}
