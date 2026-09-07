import type { ContentBlock } from './sseProtocol'

/**
 * Kilderne bag et svar — hentet fra hvad han FAKTISK slog op.
 *
 * Desk viste dem slet ikke i chatten. Der FANDTES en «Kilder»-rubrik, men kun
 * i kodetilstandens miljøpanel, og den viste et mærkat («Websøgning») frem for
 * adresser man kunne klikke på. Mobilen havde den modsatte fejl: kilder under
 * streaming, væk bagefter.
 *
 * Dataen har ligget der hele tiden. `content_json` bærer 29-119 blokke pr. tur,
 * og `foldToolResults` samler svaret ind i `tool_use.result`. Adressen på en
 * web-hentning står i `input`, mens en søgnings kilder først dukker op i
 * `result` — læser man kun det ene, mister man halvdelen.
 */

export interface Kilde {
  url: string
  domaene: string
}

const URL_RE = /https?:\/\/[^\s<>"'`)\]}(|$&]+/gi

/** Hans eget maskineri er ikke en kilde. */
const INTERN = /^(localhost|127\.|0\.0\.0\.0|10\.|192\.168\.|172\.(1[6-9]|2\d|3[01])\.|\[?::1)/i

function ryd(raa: string): Kilde | null {
  const url = raa.replace(/[.,;:!?)\]}>]+$/, '')
  try {
    const u = new URL(url)
    const domaene = u.hostname.replace(/^www\./i, '').toLowerCase()
    if (!domaene || INTERN.test(domaene)) return null
    return { url, domaene }
  } catch {
    return null
  }
}

function saml(tekst: string, ud: Map<string, Kilde>): void {
  for (const traef of String(tekst || '').matchAll(URL_RE)) {
    const k = ryd(traef[0])
    if (k && !ud.has(k.url)) ud.set(k.url, k)
  }
}

/** Alle kilder i en tur, i brugsrækkefølge. Tomt array når han ikke slog noget op. */
export function kilderFraBlokke(blokke: ContentBlock[] | null | undefined): Kilde[] {
  const ud = new Map<string, Kilde>()
  for (const b of blokke ?? []) {
    if (b?.type === 'tool_use') {
      saml(JSON.stringify(b.input ?? {}), ud)
      if (typeof b.result === 'string') saml(b.result, ud)
    }
  }
  // Svarteksten sidst: citerer han selv en adresse, hører den med — men efter
  // dem han rent faktisk hentede.
  for (const b of blokke ?? []) {
    if (b?.type === 'text') saml(b.text ?? '', ud)
  }
  return [...ud.values()]
}

/** Ét punkt pr. domæne, til rækken under svaret. */
export function kilderPrDomaene(kilder: Kilde[], maks = 8): Kilde[] {
  const set = new Set<string>()
  const ud: Kilde[] = []
  for (const k of kilder) {
    if (set.has(k.domaene)) continue
    set.add(k.domaene)
    ud.push(k)
    if (ud.length >= maks) break
  }
  return ud
}
