/** Paste-store (desk-klient, spec 2026-07-09).
 *
 *  Store bruger-pastes eksternaliseres: composeren viser en kompakt reference-chip
 *  i stedet for en tekst-væg, og sender `[paste:<id> +N linjer]` i beskeden.
 *  Små pastes forbliver inline (uændret).
 *
 *  Ren logik her (tærskel/reference-format) → testbar uden DOM. API-kald ligger i api.ts.
 */
import { apiFetch, type ApiConfig } from './api'

/** Tærskler (spec §3): paste > ~20 linjer ELLER > ~2000 tegn → eksternalisér. */
export const PASTE_LINE_THRESHOLD = 20
export const PASTE_CHAR_THRESHOLD = 2000

/** Feature-flag: composer-eksternalisering (GUARDRAIL — default OFF indtil verificeret).
 *  Default ON (Bjørn 10. jul). Slå fra via localStorage `jarvis-desk:pasteStoreEnabled` = '0'. */
export const PASTE_STORE_ENABLED_KEY = 'jarvis-desk:pasteStoreEnabled'
export function pasteStoreEnabled(): boolean {
  try {
    return localStorage.getItem(PASTE_STORE_ENABLED_KEY) !== '0'
  } catch {
    return true
  }
}

/** Antal linjer i en tekst (trailing newline tæller ikke som ekstra tom linje). */
export function pasteLineCount(text: string): number {
  if (!text) return 0
  const stripped = text.endsWith('\n') ? text.slice(0, -1) : text
  return stripped.split('\n').length
}

/** Skal denne paste eksternaliseres? >20 linjer eller >2000 tegn. */
export function shouldExternalizePaste(text: string): boolean {
  if (!text) return false
  return text.length > PASTE_CHAR_THRESHOLD || pasteLineCount(text) > PASTE_LINE_THRESHOLD
}

/** Byg reference-strengen — SKAL matche backendens `build_paste_reference`. */
export function buildPasteReference(pasteId: string, lineCount: number): string {
  const n = Math.max(lineCount | 0, 0)
  return `[paste:${pasteId} +${n} linjer]`
}

/** Find første paste-reference i en tekst. Null hvis ingen. */
export function parsePasteReference(
  content: string,
): { pasteId: string; lineCount: number } | null {
  const m = /\[paste:([A-Za-z0-9_-]+)\s+\+(\d+)\s+linjer\]/.exec(content || '')
  if (!m || !m[1]) return null
  return { pasteId: m[1], lineCount: Number(m[2]) || 0 }
}

/** POST /paste → gem pasten, få id + reference-streng. */
export async function savePaste(
  config: ApiConfig,
  text: string,
): Promise<{ pasteId: string; reference: string; lineCount: number }> {
  const r = await apiFetch<{ paste_id: string; reference: string; line_count: number }>(
    config,
    '/paste',
    { method: 'POST', body: { text } },
  )
  return { pasteId: r.paste_id, reference: r.reference, lineCount: r.line_count }
}

/** GET /paste/{id} → fuld paste-tekst (lazy resolve til render). */
export async function getPaste(
  config: ApiConfig,
  pasteId: string,
): Promise<{ id: string; text: string; lineCount: number; createdAt: string }> {
  const r = await apiFetch<{
    id: string
    text: string
    line_count: number
    created_at: string
  }>(config, `/paste/${encodeURIComponent(pasteId)}`)
  return { id: r.id, text: r.text, lineCount: r.line_count, createdAt: r.created_at }
}
