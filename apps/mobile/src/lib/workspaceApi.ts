import { apiFetch } from './apiClient'
import type { ApiConfig } from './types'

export type WsArt = 'container' | 'workstation'

export interface ServerRod {
  /** Navnet ruten kender den under — «repo», «jarvis-v2», «workspace». */
  navn: string
  /** Den faktiske sti. Uden den er et valg et gæt. */
  sti: string
}

export interface TraePost {
  navn: string
  mappe: boolean
}

/**
 * De navngivne server-roots brugeren må vælge imellem.
 *
 * Desk har listen hårdkodet i to konstanter. Det virker dér, men en hårdkodet
 * liste i hver klient er en liste der forfalder hver for sig — og rollen
 * bestemmer allerede hvad man må se. Serveren siger nu bare hvad den fandt.
 */
export async function hentServerRoedder(config: ApiConfig): Promise<ServerRod[]> {
  const d = await apiFetch<{ roots?: { name?: string; path?: string }[] }>(config, '/chat/roots')
  return (d.roots ?? [])
    .filter((r) => typeof r.name === 'string' && r.name)
    .map((r) => ({ navn: String(r.name), sti: String(r.path ?? '') }))
}

/**
 * Kig i en mappe — på serveren eller på brugerens egen computer.
 *
 * `kind: 'workstation'` går gennem broen (`operator_list_dir`). Svarer broen
 * ikke, kaster den; kalderen skal sige det højt frem for at vise en tom mappe,
 * for en tom mappe og en død forbindelse ser ens ud og betyder stik modsat.
 */
export async function hentTrae(
  config: ApiConfig, kind: WsArt, root: string, path = '',
): Promise<TraePost[]> {
  const qs = new URLSearchParams({ kind, root, path }).toString()
  const d = await apiFetch<{ entries?: { name?: string; kind?: string }[] }>(
    config, `/chat/tree?${qs}`,
  )
  return (d.entries ?? [])
    .filter((e) => typeof e.name === 'string' && e.name)
    .map((e) => ({ navn: String(e.name), mappe: e.kind === 'dir' }))
}

/** Bind samtalen til et workspace. */
export async function saetSessionWorkspace(
  config: ApiConfig, sessionId: string, kind: WsArt, root: string,
): Promise<void> {
  await apiFetch(config, `/chat/sessions/${encodeURIComponent(sessionId)}/workspace`, {
    method: 'POST',
    body: { kind, root },
  })
}

/**
 * Sæt en sti sammen af en mappe og et navn — uden dobbelte skråstreger.
 *
 * Ser trivielt ud, men `/` + `/home` gav `//home`, og `operator_list_dir`
 * svarer ikke det samme på de to. Derfor ét sted frem for i hver knap.
 */
export function underSti(base: string, navn: string): string {
  const b = String(base || '').replace(/\/+$/, '')
  return `${b}/${navn}`
}

/** Ét niveau op. Roden er sin egen forælder — man kan ikke gå over «/». */
export function forael(sti: string): string {
  const rent = String(sti || '/').replace(/\/+$/, '')
  const i = rent.lastIndexOf('/')
  if (i <= 0) return '/'
  return rent.slice(0, i)
}
