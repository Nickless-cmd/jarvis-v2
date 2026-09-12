import { apiFetch } from './apiClient'
import type { ApiConfig } from './types'

export interface SessionBillede {
  attachmentId: string
  sessionId: string
  filnavn: string
  mime: string
  oprettet: string
  /** Lavede Jarvis det, eller sendte man det selv? */
  lavetAfJarvis: boolean
}

/** Serveren mærker dem Jarvis genererede med denne kanal-type. */
const GENERERET = 'generated'

/**
 * Billederne i én samtale — både dem Jarvis lavede og dem man selv sendte.
 *
 * ## Hvorfor de to kan stå i samme liste nu
 *
 * Det kunne de ikke før 12/9-2026. Uploads lå i `channel_attachments` med et
 * session-id; genererede billeder blev skrevet til workspace'et med en
 * sidecar der ikke kendte nogen samtale, og de 392 assistent-beskeder med
 * billed-blokke havde tilsammen NUL af typen `image`. Jarvis kunne altså lave
 * et billede man aldrig kunne se. Registreringen er bygget; herfra deler de
 * substrat.
 *
 * Billeder fra FØR den rettelse dukker ikke op — de har intet at knytte sig
 * til, og et gæt på filnavnets tidsstempel ville lægge dem i tilfældige
 * samtaler.
 */
export async function hentSessionBilleder(
  config: ApiConfig, sessionId: string, limit = 200,
): Promise<SessionBillede[]> {
  const qs = new URLSearchParams({ limit: String(limit) })
  if (sessionId) qs.set('session_id', sessionId)
  const data = await apiFetch<{ items?: Record<string, unknown>[] }>(
    config, `/attachments/images?${qs.toString()}`,
  )
  return (data.items ?? []).map(normalisér).filter((b): b is SessionBillede => b !== null)
}

function normalisér(raw: Record<string, unknown>): SessionBillede | null {
  const id = typeof raw.attachment_id === 'string' ? raw.attachment_id : ''
  if (!id) return null
  return {
    attachmentId: id,
    sessionId: String(raw.session_id ?? ''),
    filnavn: String(raw.filename ?? 'billede'),
    mime: String(raw.mime_type ?? 'image/jpeg'),
    oprettet: String(raw.created_at ?? ''),
    lavetAfJarvis: String(raw.channel_type ?? '') === GENERERET,
  }
}

/** Hentes over den historiske rute — `/attachments/{id}` kender kun den
 *  aktuelle sessions registry og fejler på alt ældre. */
export function billedUrl(config: ApiConfig, attachmentId: string): string {
  return new URL(
    `/attachments/image/${encodeURIComponent(attachmentId)}`, config.apiBaseUrl,
  ).toString()
}
