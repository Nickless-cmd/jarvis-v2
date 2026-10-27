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
  // Interne pseudo-hrefs (fx `#side-opgave=side-xxxx`, `#agent=asg-…`,
  // `#fil=sti/fil.ts`) peger ikke på en ekstern ressource — de styrer kun
  // UI-tilstand i appen selv, og skal derfor IKKE afvises af URL-parseren som
  // kun kender http/https/mailto.
  //
  // 27/10-2026: listen var ÉN regex for side-opgaver. Da agent-, worktree-,
  // wake-, run- og fil-referencer blev tilføjet, faldt de allesammen ud her og
  // blev gjort døde UDEN en fejl nogen steder — et link der bliver en <span> er
  // tavst. Derfor er reglen nu generaliseret, men stadig lukket: kun de kendte
  // præfikser, kun tegn der kan indgå i et id eller en sti, og intet scheme.
  if (/^#(?:side-opgave|agent|worktree|wake|run|fil)=[\w./-]{1,120}$/i.test(raw)) return raw
  let url: URL
  try {
    url = new URL(raw)
  } catch {
    return null
  }
  if (!ALLOWED_LINK_SCHEMES.has(url.protocol.toLowerCase())) return null
  return raw
}

/** Raster-billeder som data-URL. SVG er BEVIDST udeladt: en svg+xml-data-URL
 *  kan bære script, og den vej holdes blokeret. */
const ALLOWED_DATA_IMG = /^data:image\/(png|jpe?g|webp|gif|avif);base64,[A-Za-z0-9+/]+=*$/i

/** Returnér img-src hvis tilladt kilde, ellers null.
 *  Tilladt: relative backend-stier (/...), https:, og raster-billeder som
 *  data-URL — main læser lokale filer og giver dem videre sådan (se
 *  electron/billede.ts). Blokeret: file:, blob:, http, og SVG-data-URLs. */
export function safeImageSrc(raw: string): string | null {
  if (!raw) return null
  if (raw.startsWith('/')) return raw // backend-attachment relativ sti
  if (ALLOWED_DATA_IMG.test(raw)) return raw
  let url: URL
  try {
    url = new URL(raw)
  } catch {
    return null
  }
  if (url.protocol.toLowerCase() === 'https:') return raw
  return null
}
