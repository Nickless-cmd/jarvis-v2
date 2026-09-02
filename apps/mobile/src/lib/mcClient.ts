/**
 * Mission-control-klient — Arbejde-rummet (V2 fase 1).
 *
 * Tynd oversættelse fra serverens svar til appens typer. Al auth og
 * fejlklassifikation genbruges fra `apiFetch`; denne fil tilføjer kun
 * form-udpakning og de to verber Arbejde-rummet har brug for.
 */

import { ApiError, apiFetch } from './apiClient'
import type { ApiConfig } from './types'
import type { Approval, McApprovalsResponse, McRun, McRunsResponse } from './mcTypes'

const DEFAULT_LIMIT = 20

export async function fetchRuns(config: ApiConfig, limit = DEFAULT_LIMIT): Promise<McRunsResponse> {
  const raw = await apiFetch<Partial<McRunsResponse>>(config, `/mc/runs?limit=${limit}`)
  return {
    active_run: raw.active_run ?? null,
    last_outcome: raw.last_outcome ?? null,
    recent_runs: Array.isArray(raw.recent_runs) ? raw.recent_runs : [],
    summary: raw.summary ?? { active: false, recent_count: 0, failed_count: 0 }
  }
}

export async function fetchApprovals(
  config: ApiConfig,
  limit = DEFAULT_LIMIT
): Promise<McApprovalsResponse> {
  const raw = await apiFetch<Partial<McApprovalsResponse>>(config, `/mc/approvals?limit=${limit}`)
  return {
    requests: Array.isArray(raw.requests) ? raw.requests : [],
    summary: raw.summary ?? { pending_count: 0, approved_count: 0, request_count: 0 }
  }
}

/**
 * Godkend OG udfør i ét kald.
 *
 * `/approve` alene stempler kun `approved_at` — der sker intet observerbart.
 * Fase 1's leverance-kriterie er at «run'et fortsætter», så vi bruger det
 * idempotente `approve-and-execute`. Uden det ville et tryk på Godkend føles
 * som om ingenting skete.
 */
export async function approveRequest(
  config: ApiConfig,
  requestId: string
): Promise<{ ok: boolean; request?: unknown; error?: string }> {
  try {
    return await apiFetch<{ ok: boolean; request?: unknown; error?: string }>(
      config,
      `/mc/capability-approval-requests/${encodeURIComponent(requestId)}/approve-and-execute`,
      { method: 'POST' }
    )
  } catch (error) {
    if (error instanceof ApiError && error.statusCode === 404) {
      throw new ApiError('unknown', 'Godkendelsen findes ikke længere', 404)
    }
    throw error
  }
}

/**
 * Godkend en tool-intent. Det er et ANDET system med et 15-minutters vindue —
 * serveren svarer 409 når vinduet er lukket, og det oversættes til en besked
 * brugeren kan forstå frem for en rå statuskode.
 */
export async function approveToolIntent(
  config: ApiConfig
): Promise<{ ok: boolean; request?: unknown }> {
  try {
    return await apiFetch<{ ok: boolean; request?: unknown }>(config, '/mc/tool-intent/approve', {
      method: 'POST'
    })
  } catch (error) {
    if (error instanceof ApiError && error.statusCode === 409) {
      throw new ApiError('unknown', 'Godkendelsesvinduet er udløbet', 409)
    }
    throw error
  }
}

/** Kun de kort der stadig kan handles på — resten er historik. */
export function pendingApprovals(list: Approval[]): Approval[] {
  return list.filter((a) => a.active === true && a.stale !== true)
}
