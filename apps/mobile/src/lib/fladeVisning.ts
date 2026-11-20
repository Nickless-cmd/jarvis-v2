/**
 * DIL lag 4: fallback der altid er med. Ren logik, ingen React — byte-identisk i desk og mobil.
 *
 * - `vaelgVisning`: et nyt program der fejler lader det SIDST VIRKENDE stå (i stedet for at
 *   `key={code}`-remount erstatter den gamle flade med intet).
 * - `fladeStatus` (S1): status-linje under fladen. Skiller KILDEN (`isSourceStreaming`: JSON-blokken
 *   er ikke lukket endnu) fra BESKEDEN (`hostMessageIsStreaming`: teksten omkring den løber stadig).
 * - `settleKontrol` (S3): efterkontrol af det TEGNEDE resultat når streamen stopper — antal
 *   elementer i programmet mod antal elementer i den tolkede flade, og at noget synligt blev tegnet.
 */
import type { FladeProgram } from './fladeProgram'

export interface Visning<T> {
  spec: T | null
  /** Sand når `spec` er det sidst virkende og IKKE det nyeste forsøg. */
  fallback: boolean
}

export function vaelgVisning<T>(ny: T | null, sidstVirkende: T | null): Visning<T> {
  if (ny) return { spec: ny, fallback: false }
  if (sidstVirkende) return { spec: sidstVirkende, fallback: true }
  return { spec: null, fallback: false }
}

export interface StatusInput {
  /** Kilden (fence-blokken) skrives stadig: JSON'en kan endnu ikke parses komplet. */
  isSourceStreaming: boolean
  /** Beskeden fladen sidder i streamer stadig — også efter at kilden er færdig. */
  hostMessageIsStreaming: boolean
  /** Visningen er det sidst virkende, fordi det nyeste forsøg ikke kunne tegnes. */
  fallback: boolean
  /** Efterkontrollens afvigelser (tom liste = ok eller endnu ikke kørt). */
  afvigelser: string[]
}

/** Teksten til status-linjen under fladen, eller `null` når der intet er at sige. */
export function fladeStatus(i: StatusInput): string | null {
  if (i.isSourceStreaming) return i.fallback ? 'fladen skrives — viser sidste virkende version' : 'fladen skrives…'
  if (i.hostMessageIsStreaming) return 'fladen er færdig — beskeden skrives stadig'
  if (i.fallback) return 'seneste version kunne ikke tegnes — viser den sidste der virkede'
  if (i.afvigelser.length > 0) return i.afvigelser[0] as string
  return null
}

const erObjekt = (v: unknown): v is Record<string, unknown> => !!v && typeof v === 'object' && !Array.isArray(v)

/** Antal elementer (objekter med `type`) i en tolket flade. */
export function taelElementer(spec: unknown): number {
  if (Array.isArray(spec)) return spec.reduce<number>((n, x) => n + taelElementer(x), 0)
  if (!erObjekt(spec)) return 0
  let n = typeof spec.type === 'string' && spec.type !== '' ? 1 : 0
  for (const v of Object.values(spec)) n += taelElementer(v)
  return n
}

export interface SettleResultat {
  ok: boolean
  afvigelser: string[]
}

/**
 * Efterkontrol når streamen er stoppet.
 *
 * @param program   Det kompilerede program for den endelige kilde.
 * @param spec      Det der blev tolket til rendering.
 * @param domTekst  Den tegnede tekst (kun hvor en DOM findes); `undefined` springer den kontrol over.
 */
export function settleKontrol(program: FladeProgram, spec: unknown, domTekst?: string): SettleResultat {
  const afvigelser: string[] = []
  if (program.diagnostik.length > 0) {
    const n = program.diagnostik.length
    afvigelser.push(`${n} element${n === 1 ? '' : 'er'} kunne ikke kompileres og er udeladt`)
  }
  const forventet = program.program.length
  const tegnet = taelElementer(spec)
  if (tegnet < forventet) {
    afvigelser.push(`${forventet - tegnet} af ${forventet} elementer blev ikke tegnet`)
  }
  if (domTekst !== undefined && forventet > 0 && domTekst.trim() === '') {
    afvigelser.push('fladen blev tegnet uden synlig tekst')
  }
  return { ok: afvigelser.length === 0, afvigelser }
}
