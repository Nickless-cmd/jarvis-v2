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
 * En HUKOMMELSES-kilde — hvor et svar fik sin viden fra, når det ikke kom fra nettet.
 *
 * Målt 24/10-2026: `recall` returnerer allerede `source` per hit (fx
 * `MEMORY.md`, `brain`, `chronicle`, `session_summary`), men den information
 * blev kun brugt internt i prompt-teksten og nåede aldrig klienten. Derfor
 * kunne kilder-ikonet kun vise webdomæner — hukommelsen var usynlig som kilde.
 *
 * Vi læser den nu ud af `recall`-værktøjets RESULTAT (JSON med `results[]`),
 * ikke af dets input: det er resultatet der bærer hvad der faktisk blev brugt.
 */
export interface HukommelsesKilde {
  /** Kildenavn som recall rapporterer det: MEMORY.md, brain, chronicle, … */
  kilde: string
  /** Menneske-læsbar etiket til rækken under svaret. */
  etiket: string
  /** Antal hits fra denne kilde i turen. */
  antal: number
}

/** Værktøjer hvis RESULTAT bærer hukommelses-kilder. */
export const HUKOMMELSE_TOOLS: ReadonlySet<string> = new Set([
  'recall', 'repo_recall', 'search_memory', 'recall_memories',
])

const KILDE_ETIKET: Record<string, string> = {
  'MEMORY.md': 'Langtidshukommelse',
  'USER.md': 'Om dig',
  'SOUL.md': 'Identitet',
  'PLAYBOOKS.md': 'Opskrifter',
  'STANDING_ORDERS.md': 'Stående ordrer',
  'SKILLS.md': 'Færdigheder',
  brain: 'Hjernen',
  private_brain: 'Indre liv',
  session_summary: 'Tidligere samtaler',
  chronicle: 'Kronik',
  chat: 'Chat-historik',
  sensory: 'Sanserne',
  workspace: 'Arbejdsfiler',
}

function etiketFor(kilde: string): string {
  const ren = kilde.replace(/\\/g, '/').split('/').pop() || kilde
  return KILDE_ETIKET[kilde] || KILDE_ETIKET[ren] || ren
}

/** Læs hukommelses-kilder ud af et `recall`-resultat. Robust mod ikke-JSON. */
export function hukommelseskilderFraResultat(raa: unknown): HukommelsesKilde[] {
  let data: unknown = raa
  if (typeof raa === 'string') {
    try { data = JSON.parse(raa) } catch { return [] }
  }
  const results = (data as { results?: unknown })?.results
  if (!Array.isArray(results)) return []
  const taeller = new Map<string, number>()
  for (const r of results) {
    const kilde = String((r as { source?: unknown })?.source || '').trim()
    if (!kilde) continue
    taeller.set(kilde, (taeller.get(kilde) || 0) + 1)
  }
  return [...taeller.entries()]
    .map(([kilde, antal]) => ({ kilde, etiket: etiketFor(kilde), antal }))
    .sort((a, b) => b.antal - a.antal)
}

/** Alle hukommelses-kilder i en tur, samlet pr. kilde. */
export function hukommelseskilderFraBlokke(
  blokke: ContentBlock[] | null | undefined,
): HukommelsesKilde[] {
  const taeller = new Map<string, number>()
  for (const b of blokke ?? []) {
    if (b?.type !== 'tool_use' || !HUKOMMELSE_TOOLS.has(b.name)) continue
    if (typeof b.result !== 'string') continue
    for (const k of hukommelseskilderFraResultat(b.result)) {
      taeller.set(k.kilde, (taeller.get(k.kilde) || 0) + k.antal)
    }
  }
  return [...taeller.entries()]
    .map(([kilde, antal]) => ({ kilde, etiket: etiketFor(kilde), antal }))
    .sort((a, b) => b.antal - a.antal)
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
