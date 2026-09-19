import type { Opmaerksomhed, OpmTilstand } from '../lib/opmaerksomhed'

/**
 * Figurens regler — rene funktioner, så de kan testes uden et vindue.
 *
 * Codex (avatar-overlay, læst ordret 19/9-2026): en handling spilles TRE
 * gange og falder så til en langsom hvile. Ikke en GIF der kører i ring.
 * Samme her: `handling` er det der spilles, `hvile` er efterklangen.
 */
export type Handling = 'hvile' | 'vinker' | 'arbejder' | 'venter' | 'fejlede' | 'faerdig' | 'hopper'

export const HANDLING_FOR: Record<OpmTilstand, Handling> = {
  idle: 'hvile',
  running: 'arbejder',
  waiting: 'venter',
  failed: 'fejlede',
  review: 'faerdig',
}

export type Udtryk = 'rolig' | 'fokus' | 'venter' | 'noed' | 'glad'

/**
 * Ansigtets udtryk pr. handling.
 *
 * Kroppen viser HVAD han gør — ansigtet viser HVORDAN det føles. Uden den
 * skelnen kunne en kerne med to prikker ikke vise forskel på at arbejde og at
 * vente; kun farven bar det. Nu bærer øjnene og munden det også.
 */
export const UDTRYK_FOR: Record<Handling, Udtryk> = {
  hvile: 'rolig',
  vinker: 'glad',
  arbejder: 'fokus',
  venter: 'venter',
  fejlede: 'noed',
  faerdig: 'glad',
  hopper: 'glad',
}

export function udtryk(h: Handling): Udtryk {
  return UDTRYK_FOR[h] ?? 'rolig'
}

export interface Boble {
  noegle: string
  etiket: string
  titel: string
  tekst: string
  sessionId: string | null
  tilstand: OpmTilstand
}

/** Nøglen for det boblen taler om. Afviser man den, kommer den først igen
 *  når der er noget NYT — en anden samtale, et andet run eller en anden tilstand. */
export function boblensNoegle(o: Opmaerksomhed): string {
  const f = o.fokus
  return `${o.tilstand}|${f?.session_id ?? ''}|${f?.run_id ?? ''}|${f?.id ?? ''}`
}

export function boble(o: Opmaerksomhed | null, afvist: string | null): Boble | null {
  if (!o || o.tilstand === 'idle') return null
  const noegle = boblensNoegle(o)
  if (noegle === afvist) return null
  const antal = o.antal[o.tilstand as keyof Opmaerksomhed['antal']] ?? 0
  const f = o.fokus
  return {
    noegle,
    etiket: antal > 1 ? `${o.etiket} · ${antal}` : o.etiket,
    titel: f?.titel ?? '',
    tekst: f?.tekst ?? '',
    sessionId: f?.session_id || null,
    tilstand: o.tilstand,
  }
}

/**
 * Vinduets højde — i FASTE trin, ikke efter indholdet.
 *
 * Målt 19/9-2026 under et svar: figurvinduet skiftede størrelse 6 gange på
 * 30 s (174 → 237 → 256 → 290 → 174 px), hver gang taleboblens tekst fik en
 * linje mere eller mindre. Et gennemsigtigt X11-vindue der skifter størrelse,
 * kan vise et glimt — det var figurens «glitch med mellemrum».
 *
 * Nu: med boble reserveres plads til dens maksimum (etiket, titel og tre
 * linjer tekst), så teksten kan skifte uden at vinduet gør det. Højden
 * ændrer sig kun når boblen eller hurtig-chatten kommer eller går.
 */
export const HOEJDE_MED_BOBLE = 300
export const HOEJDE_HURTIGCHAT = 46

export function maalHoejde(maalt: number, boble: boolean, hurtigchat: boolean): number {
  const min = (boble ? HOEJDE_MED_BOBLE : 0) + (hurtigchat ? HOEJDE_HURTIGCHAT : 0)
  return Math.max(Math.ceil(maalt), min)
}
