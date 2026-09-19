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
