import type { MatrixKarakter } from './api'

/** «Déjà Vu — ufrivillig erindring» → { navn: 'Déjà Vu', beskrivelse: 'ufrivillig erindring' }.
 *  Uden tankestreg er hele teksten beskrivelsen, og navnet falder tilbage på producer-navnet. */
export function splitFunktion(funktion: string, fallbackNavn: string): { navn: string; beskrivelse: string } {
  const tekst = (funktion ?? '').trim()
  const m = tekst.match(/^(.+?)\s+[—–]\s+(.+)$/)
  // `noUncheckedIndexedAccess`: regex-grupperne er muligvis undefined for TS,
  // selvom `.+?` garanterer dem. Fald tilbage på det vi kom ind med.
  if (m) return { navn: (m[1] ?? fallbackNavn).trim(), beskrivelse: (m[2] ?? tekst).trim() }
  return { navn: fallbackNavn.replace(/_/g, ' '), beskrivelse: tekst }
}

/** Cooldown i minutter → «45 min», «6 t», «1 d». Hele tal, ingen falsk præcision. */
export function formatMinutter(min: number): string {
  if (!Number.isFinite(min) || min <= 0) return '—'
  // grænsen var 90: `Math.round(90/60)` = 2, så 90 min blev vist som «2 t» —
  // 33 % for højt, og 89 min stod ved siden af som «89 min». 120 min er den
  // første værdi hvor afrunding til hele timer er ærlig.
  if (min < 120) return `${Math.round(min)} min`
  if (min < 48 * 60) return `${Math.round(min / 60)} t`
  return `${Math.round(min / 1440)} d`
}

/** «effektiv × tempo»: den EFFEKTIVE cooldown, med den rå og tempoet som forklaring
 *  når de afviger. Tempo 1 → kun tallet (ingen modulation at forklare). */
export function formatCooldown(k: Pick<MatrixKarakter, 'cooldown_minutes' | 'effektiv_cooldown_minutes'>, tempo: number): string {
  const eff = formatMinutter(k.effektiv_cooldown_minutes)
  if (Math.abs(tempo - 1) < 0.005) return eff
  return `${eff} (${formatMinutter(k.cooldown_minutes)} × ${tempo.toFixed(2)})`
}

/** Hvor længe siden, på dansk. null/ugyldig → «aldrig set» (ikke et gæt). */
export function formatSidste(iso: string | null | undefined, nu: Date = new Date()): string {
  if (!iso) return 'aldrig set'
  const t = Date.parse(iso)
  if (Number.isNaN(t)) return 'aldrig set'
  const min = Math.max(0, Math.round((nu.getTime() - t) / 60000))
  if (min < 1) return 'lige nu'
  if (min < 90) return `${min} min siden`
  if (min < 48 * 60) return `${Math.round(min / 60)} t siden`
  return `${Math.round(min / 1440)} d siden`
}

export type UdfaldVisning = { tekst: string; tone: string; title?: string }

/** Udfalds-kolonnen. Intet udfald er «ukendt» — aldrig «ok». En karakter der ikke har
 *  meldt et udfald har ikke bevist noget, og må ikke se grøn ud. */
export function udfaldVisning(k: Pick<MatrixKarakter, 'udfald' | 'udfald_at'>): UdfaldVisning {
  if (!k.udfald) return { tekst: 'ukendt', tone: 'ukendt', title: 'Ingen kørsel med udfald er set endnu' }
  return { tekst: k.udfald.tekst, tone: k.udfald.tone, title: k.udfald.outcome }
}

/** Ugyldig/manglende payload → tom liste, så visningen kan sige «ingen» i stedet for at vælte. */
export function karakterListe(data: { karakterer?: unknown } | null | undefined): MatrixKarakter[] {
  return Array.isArray(data?.karakterer) ? (data!.karakterer as MatrixKarakter[]) : []
}
