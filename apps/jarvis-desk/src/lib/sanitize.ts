/**
 * Sikkerheds-sanitizers for rendret indhold. Prod-gate: tool-resultater og
 * model-output kan indeholde fjendtligt indhold (fx web_fetch af en ondsindet
 * side), så links og billed-kilder skal valideres før de røres.
 */

const ALLOWED_LINK_SCHEMES = new Set(['http:', 'https:', 'mailto:'])

/** Returnér href hvis sikker at åbne via shell.openExternal, ellers null.
 *  Blokerer javascript:, file:, data:, blob:, custom schemes + malformet URL. */
export function safeLinkHref(raw: string): string | null {
  if (!raw) return null
  let url: URL
  try {
    url = new URL(raw)
  } catch {
    return null
  }
  if (!ALLOWED_LINK_SCHEMES.has(url.protocol.toLowerCase())) return null
  return raw
}

/** Returnér img-src hvis tilladt kilde, ellers null.
 *  Tilladt: relative backend-stier (/...), https:. Blokeret default: file:,
 *  data: (inkl. svg+xml script-vektor), blob:, http (mixed content). */
export function safeImageSrc(raw: string): string | null {
  if (!raw) return null
  if (raw.startsWith('/')) return raw // backend-attachment relativ sti
  let url: URL
  try {
    url = new URL(raw)
  } catch {
    return null
  }
  if (url.protocol.toLowerCase() === 'https:') return raw
  return null
}
