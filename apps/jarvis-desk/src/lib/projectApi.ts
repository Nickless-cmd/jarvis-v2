import { apiFetch, type ApiConfig } from './api'

export interface ProjectFil {
  path: string        // absolut sti på API-værten
  rel: string         // relativt til roden — det brugeren ser og skriver
  size_bytes: number
}

/** Fladt filindeks under en projektrod.
 *
 *  `/chat/tree` giver ét mappeniveau ad gangen; til fuzzy-komplettering
 *  skal hele indekset ligge klar på én gang. Derfor denne, som endpointet
 *  også blev skrevet til ("for @file autocomplete") uden nogensinde at få
 *  en konsument. Ejer-gatet på serveren — den læser værtens disk.
 */
export async function listProjectFiles(
  config: ApiConfig,
  root: string,
  limit = 8000,
): Promise<ProjectFil[]> {
  const qs = `root=${encodeURIComponent(root)}&limit=${limit}`
  const d = await apiFetch<{ files?: ProjectFil[] }>(config, `/api/project/list?${qs}`, {
    timeoutMs: 20_000,
  })
  return d.files ?? []
}
