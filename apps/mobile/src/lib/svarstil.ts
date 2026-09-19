import { apiFetch } from './apiClient'
import type { ApiConfig } from './types'

/** Svarstil pr. bruger — serveren gemmer den og minder Jarvis om den hver tur. */
export type Svarstil = 'balanced' | 'concise' | 'detailed' | 'technical'

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

// apiFetch stringifier selv — send objektet, ikke JSON.stringify.
export async function saetSvarstil(config: ApiConfig, stil: Svarstil): Promise<void> {
  await apiFetch(config, '/api/preferences', { method: 'POST', body: { output_style: stil } })
}
