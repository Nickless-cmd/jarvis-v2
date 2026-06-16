import { apiFetch, type ApiConfig } from './api'

export interface Connector {
  id: string
  name: string
  kind: 'oauth' | 'local'
  category: string
  icon: string
  desc: string
  scopes: string[]
  post_connect_hint: string | null
  connected: boolean
  enabled: boolean
}

/** Hele connector-kataloget beriget med per-bruger status. */
export async function getConnectors(config: ApiConfig): Promise<Connector[]> {
  const d = await apiFetch<{ connectors: Connector[] }>(config, '/api/connectors')
  return d.connectors ?? []
}

/** Slå en connector til/fra (beholder token ved fra). */
export async function setEnabled(config: ApiConfig, id: string, enabled: boolean): Promise<void> {
  await apiFetch(config, `/api/connectors/${id}/enabled`, { method: 'POST', body: { enabled } })
}

/** Afbryd & slet: revoke hos provider + wipe lokalt (GDPR). */
export async function deleteConnector(config: ApiConfig, id: string): Promise<void> {
  await apiFetch(config, `/api/connectors/${id}`, { method: 'DELETE' })
}

/** Start OAuth-flow: hent authorize-URL (åbnes i brugerens browser af kalderen). */
export async function startConnect(config: ApiConfig, id: string): Promise<string | null> {
  const d = await apiFetch<{ authorize_url?: string }>(config, `/api/oauth/${id}/start`)
  return d.authorize_url ?? null
}
