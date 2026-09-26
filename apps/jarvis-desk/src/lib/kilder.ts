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

/**
 * KUN de værktøjer der slår op på nettet giver kilder (Bjørn 26/9-2026).
 *
 * Før scannede vi ALLE tool-inputs og -resultater for URL'er. Det var
 * misvisende: læser man en fil — en test, et dokument, en config — står der
 * adresser i den, og de dukkede op som «kilder». Målt i Bjørns miljø-panel:
 * 180 kilder, hvoraf de synlige var «d», «apkcombo.com», «ude.dk» og
 * «dr.dk» — alle sammen fixture-tekst fra filer, ikke sider han havde hentet.
 * En kilde er en side man slog OP, ikke en streng man læste.
 *
 * `bash` med `curl` henter ganske vist ogsaa en side, men den samme kommando
 * kan lige saa godt vaere `grep` i en fil. Vi kan ikke se forskel, og en regel
 * der gaetter er vaerre end en regel der er smal.
 */
export const WEB_TOOLS: ReadonlySet<string> = new Set([
  'web_fetch', 'web_search', 'web_scrape', 'operator_webfetch', 'get_news',
])

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

/** URL-parseren som både chatview og Miljø-evidens bruger. */
export function kilderFraTekst(tekst: string): Kilde[] {
  const ud = new Map<string, Kilde>()
  saml(tekst, ud)
  return [...ud.values()]
}

function tilfoej(kilder: Kilde[], ud: Map<string, Kilde>): void {
  for (const kilde of kilder) {
    if (!ud.has(kilde.url)) ud.set(kilde.url, kilde)
  }
}

/** Alle kilder i en tur, i brugsrækkefølge. Tomt array når han ikke slog noget op. */
export function kilderFraBlokke(blokke: ContentBlock[] | null | undefined): Kilde[] {
  const ud = new Map<string, Kilde>()
  for (const b of blokke ?? []) {
    // Kun WEB_TOOLS: se noten dér. Et `read_file` er ikke en kilde.
    if (b?.type === 'tool_use' && WEB_TOOLS.has(b.name)) {
      tilfoej(kilderFraTekst(JSON.stringify(b.input ?? {})), ud)
      if (typeof b.result === 'string') tilfoej(kilderFraTekst(b.result), ud)
    }
  }
  // Svarteksten sidst: citerer han selv en adresse, hører den med — men efter
  // dem han rent faktisk hentede.
  for (const b of blokke ?? []) {
    if (b?.type === 'text') tilfoej(kilderFraTekst(b.text ?? ''), ud)
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
