/**
 * Kilderne bag et svar — hentet fra hvad han FAKTISK slog op.
 *
 * Før dette blev «Kilder» udledt af `sourceDomains(message.content)`, altså
 * ved at rive domæner ud af URL'er i selve svarteksten. Det havde to følger,
 * begge målt på enheden 7/9-2026:
 *
 * 1. Under streaming så man kilderne, fordi de levende tool-blokke blev
 *    tegnet med. Når turen var forbi, faldt de væk igen — den persisterede
 *    visning viser `tool_use` men ikke `tool_result`, og en søgnings kilder
 *    ligger i RESULTATET, ikke i kaldet.
 * 2. Skrev han et svar uden at citere URL'erne — hvilket han som regel gør —
 *    stod der ingen kilder overhovedet, selv om han havde hentet fem sider.
 *
 * Kilderne står i `content_json`, som serveren har gemt hele tiden: 29-119
 * blokke pr. tur med både `tool_use` og `tool_result`. Dataen manglede aldrig;
 * ingen læste den.
 */

export interface Kilde {
  /** Fuld URL, så visningen kan linke og ikke bare vise et domæne. */
  url: string
  /** Vist navn: domænet uden www. */
  domaene: string
}

/** URL'er i fritekst. Afsluttende tegnsætning hører ikke med til adressen. */
const URL_RE = /https?:\/\/[^\s<>"'`)\]}(|$&]+/gi

/** Interne adresser er ikke «kilder» — de er hans eget maskineri. */
const INTERN = /^(localhost|127\.|0\.0\.0\.0|10\.|192\.168\.|172\.(1[6-9]|2\d|3[01])\.|\[?::1)/i

/** Felter i et tool-input der plejer at bære en adresse. */
const URL_FELTER = ["url", "uri", "link", "address", "adresse", "endpoint"]

function ryd(raa: string): Kilde | null {
  // Markdown og prosa efterlader gerne ) . , : ; klistret på enden.
  const url = raa.replace(/[.,;:!?)\]}>]+$/, "")
  try {
    const u = new URL(url)
    const domaene = u.hostname.replace(/^www\./i, "").toLowerCase()
    if (!domaene || INTERN.test(domaene)) return null
    return { url, domaene }
  } catch {
    return null
  }
}

function samlFraTekst(tekst: string, ud: Map<string, Kilde>): void {
  for (const traef of String(tekst || "").matchAll(URL_RE)) {
    const k = ryd(traef[0])
    // Første forekomst vinder: den er som regel den kanoniske, mens senere
    // er sporingsvarianter af samme side.
    if (k && !ud.has(k.url)) ud.set(k.url, k)
  }
}

export interface KildeBlok {
  type?: string
  text?: string
  name?: string
  input?: Record<string, unknown>
  content?: string
}

/**
 * Alle kilder i en tur, i den rækkefølge de blev brugt.
 *
 * Både kaldet og svaret læses: en web-hentning bærer adressen i `input.url`,
 * mens en søgning først har den i resultatet. Læser man kun det ene, mister
 * man halvdelen — og det var netop halvdelen der forsvandt når streamen
 * stoppede.
 */
export function kilderFraBlokke(
  blokke: KildeBlok[] | null | undefined, fritekst?: string
): Kilde[] {
  const ud = new Map<string, Kilde>()
  for (const b of blokke ?? []) {
    if (b?.type === "tool_use" && b.input) {
      for (const felt of URL_FELTER) {
        const v = b.input[felt]
        if (typeof v === "string") samlFraTekst(v, ud)
      }
      // Nogle værktøjer lægger adressen i en fritekst-parameter (query,
      // command). Hele inputtet skannes derfor, men kun for hele URL'er.
      samlFraTekst(JSON.stringify(b.input), ud)
    } else if (b?.type === "tool_result" && typeof b.content === "string") {
      samlFraTekst(b.content, ud)
    }
  }
  // Svarteksten sidst: citerer han selv en adresse, hører den med — men efter
  // dem han rent faktisk hentede.
  if (fritekst) samlFraTekst(fritekst, ud)
  return [...ud.values()]
}

/** Ét punkt pr. domæne, til den kompakte visning under et svar. */
export function kilderPrDomaene(kilder: Kilde[], maks = 6): Kilde[] {
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
