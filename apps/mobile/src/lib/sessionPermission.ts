import { apiFetch } from './apiClient'
import type { ApiConfig } from './types'

/**
 * Samtalens tilladelses-niveau — ÉN sandhed, på serveren (Bjørn 20/9-2026).
 *
 *   ask   — Jarvis spørger før et værktøj muterer noget (godkendelses-kort)
 *   trust — fuld adgang, ingen kort
 *
 * ## Hvorfor den bor på serveren
 *
 * Før lå valget to steder: desk i `localStorage` og telefonen i SecureStore,
 * hver for sig, pr. samtale. To klienter kunne derfor vise hver sin sandhed,
 * mens runnet kørte med den ene — desk stod på fuld adgang, telefonen på
 * «spørg først», og serveren svarede ud fra hvad den ene havde sendt med.
 * Bjørn: «så bliver serveren forvirret».
 *
 * Nu skriver begge klienter til samme felt på samtalen, og begge læser det
 * ved samtale-skift. Telefonen arver dermed desk'ens valg i det sekund den
 * åbner samtalen — og omvendt.
 *
 * ## To ting denne fil IKKE løser
 *
 * Et KØRENDE run beholder sin mode. `trust_all` sættes ud fra `approval_mode`
 * ved run-start (`core/services/visible_runs.py`) og kan ikke skifte undervejs.
 * Et skift her gælder altså fra næste tur. Det er med vilje: et run må ikke
 * kunne eskalere privilegier midt i en opgave.
 *
 * Og `ask` er standarden. Er serveren tavs, vælger vi den sikre vej frem for
 * at gætte på fuld adgang.
 */

export type ApprovalMode = 'ask' | 'trust'

export function erApprovalMode(v: unknown): v is ApprovalMode {
  return v === 'ask' || v === 'trust'
}

/** Samtalens niveau. Ukendt/ugyldigt svar → `ask` (den sikre vej). */
export async function hentSessionPermission(
  config: ApiConfig, sessionId: string,
): Promise<ApprovalMode> {
  const r = await apiFetch<{ approval_mode?: string }>(
    config, `/chat/sessions/${encodeURIComponent(sessionId)}/permission`,
  )
  return erApprovalMode(r?.approval_mode) ? r.approval_mode : 'ask'
}

/** Sæt niveauet. Serveren er kilden, så vi returnerer dens svar — ikke vores. */
export async function saetSessionPermission(
  config: ApiConfig, sessionId: string, mode: ApprovalMode,
): Promise<ApprovalMode> {
  const r = await apiFetch<{ approval_mode?: string }>(
    config, `/chat/sessions/${encodeURIComponent(sessionId)}/permission`,
    { method: 'POST', body: { approval_mode: mode } },
  )
  return erApprovalMode(r?.approval_mode) ? r.approval_mode : mode
}
