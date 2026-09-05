/**
 * Beslutninger — de spørgsmål Jarvis selv har stillet.
 *
 * Ruterne har eksisteret hele tiden (`/mc/initiatives/{id}/approve|reject`,
 * `/mc/life-projects/{id}/abandon`). Der var bare ingen knap: 31 initiativer
 * udløb uden svar, og nul blev nogensinde besvaret. Denne fil er den manglende
 * halvdel.
 *
 * Læsesiden går gennem Centralens mind-hub, ikke direkte til køen — samme
 * projektion som desk viser, så de to flader ikke kan komme til at være uenige.
 */

import { apiFetch } from './apiClient'
import type { ApiConfig } from './types'

export type DecisionKind = 'initiative' | 'life_project'
export type DecisionAction = 'approve' | 'reject' | 'endorse' | 'abandon'

export interface Decision {
  kind: DecisionKind
  id: string
  /** Selve forslaget — det der skal tages stilling til. */
  text: string
  /** Hans begrundelse. Et forslag uden hvorfor er svært at svare på. */
  why: string
  priority: string
  created_at: string
  actions: DecisionAction[]
}

export interface DecisionsResponse {
  items: Decision[]
  /** Tallet der gør ondt: hvor mange han spurgte om og aldrig fik svar på. */
  expiredUnanswered: number
}

const ACTION_PATHS: Record<string, string> = {
  'initiative:approve': '/mc/initiatives/{id}/approve',
  'initiative:reject': '/mc/initiatives/{id}/reject',
  'life_project:endorse': '/mc/life-projects/{id}/endorse',
  'life_project:abandon': '/mc/life-projects/{id}/abandon'
}

const _ACTIONS = ['approve', 'reject', 'endorse', 'abandon'] as const

function asAction(raw: unknown): DecisionAction | null {
  return (_ACTIONS as readonly string[]).includes(String(raw))
    ? (raw as DecisionAction)
    : null
}

function normalise(raw: Record<string, unknown>): Decision | null {
  const id = typeof raw.id === 'string' ? raw.id : ''
  const text = typeof raw.text === 'string' ? raw.text : ''
  const kind = raw.kind === 'initiative' || raw.kind === 'life_project' ? raw.kind : null
  // Uden id kan der ikke handles, og uden tekst er der intet at tage stilling
  // til. Et halvt kort er værre end ingen: det ligner noget der venter.
  if (!id || !text || !kind) return null
  const actions = Array.isArray(raw.actions)
    ? raw.actions.map(asAction).filter((a): a is DecisionAction => a !== null)
    : []
  return {
    kind,
    id,
    text,
    why: typeof raw.why === 'string' ? raw.why : '',
    priority: typeof raw.priority === 'string' ? raw.priority : '',
    created_at: typeof raw.created_at === 'string' ? raw.created_at : '',
    actions: actions.filter((a) => ACTION_PATHS[`${kind}:${a}`] !== undefined)
  }
}

export async function fetchDecisions(config: ApiConfig): Promise<DecisionsResponse> {
  const raw = await apiFetch<{
    items?: unknown
    queue?: { expired_unanswered?: unknown }
  }>(config, '/central/mind?section=decisions')

  const items = Array.isArray(raw.items)
    ? raw.items
        .filter((x): x is Record<string, unknown> => typeof x === 'object' && x !== null)
        .map(normalise)
        .filter((d): d is Decision => d !== null)
    : []

  const expired = raw.queue?.expired_unanswered
  return { items, expiredUnanswered: typeof expired === 'number' ? expired : 0 }
}

/**
 * Svar på ét spørgsmål.
 *
 * Serveren svarer HTTP 200 med `ok: false` når et id ikke findes — typisk
 * fordi posten udløb mens skærmen stod åben. Derfor er det `ok` der afgør, ikke
 * status-koden.
 */
export async function actOnDecision(
  config: ApiConfig,
  decision: Decision,
  action: DecisionAction
): Promise<{ ok: boolean; error?: string }> {
  const template = ACTION_PATHS[`${decision.kind}:${action}`]
  if (!template) {
    return { ok: false, error: `${action} findes ikke for ${decision.kind}` }
  }
  const path = template.replace('{id}', encodeURIComponent(decision.id))
  const raw = await apiFetch<{ ok?: unknown; error?: unknown }>(config, path, { method: 'POST' })
  return {
    ok: raw.ok === true,
    error: typeof raw.error === 'string' ? raw.error : undefined
  }
}
