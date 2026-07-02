import { apiFetch, type ApiConfig } from './api'
import type { Valence } from '../components/PresenceOrb'

/** Spec E / E0-konsument: Centralens ægte valens + selv-tilstand (owner-only). */
export interface PresenceState {
  valence: Valence
  self: { describe?: string; il?: string | null; attention?: string | null; completeness?: number | null }
  generation?: number | null
}

export async function fetchPresenceState(config: ApiConfig): Promise<PresenceState | null> {
  try {
    return await apiFetch<PresenceState>(config, '/presence/state', { timeoutMs: 6000, retries: 1 })
  } catch {
    return null
  }
}
