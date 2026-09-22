/**
 * Valget mellem bobbler og rækker.
 *
 * Lokal præference, samme mønster som `composerPrefs` — den hører til
 * skærmen, ikke til kontoen, og skal virke uden netværk.
 *
 * `useSyncExternalStore` og ikke bare et opslag ved render: `MessageRow` er
 * memoiseret, så et localStorage-opslag i renderkroppen ville aldrig blive
 * kørt igen når man slår knappen om — visningen ville først skifte ved næste
 * besked. Abonnementet her er dét der gør skiftet øjeblikkeligt på HELE
 * tråden.
 */
import { useSyncExternalStore } from 'react'

export const RAEKKE_KEY = 'jarvis-desk:raekkevisning'

type Lytter = () => void
const lyttere = new Set<Lytter>()

export function readRaekkevisning(): boolean {
  try {
    return localStorage.getItem(RAEKKE_KEY) === '1'
  } catch {
    // Privat vindue eller blokeret lager: bobblevisningen er standarden.
    return false
  }
}

export function writeRaekkevisning(til: boolean): void {
  try {
    localStorage.setItem(RAEKKE_KEY, til ? '1' : '0')
  } catch { /* uden lager gaelder valget kun denne session */ }
  for (const l of lyttere) l()
}

function abonner(l: Lytter): () => void {
  lyttere.add(l)
  // `storage` fyrer kun i ANDRE faner, men desk kan have flere vinduer
  // aabne mod samme profil — saa foelger de med uden at skulle genstartes.
  const fraAndetVindue = (e: StorageEvent) => { if (e.key === RAEKKE_KEY) l() }
  try { window.addEventListener('storage', fraAndetVindue) } catch { /* ingen window i test */ }
  return () => {
    lyttere.delete(l)
    try { window.removeEventListener('storage', fraAndetVindue) } catch { /* ignore */ }
  }
}

/** Live-værdien. Skifter med det samme når knappen slås om. */
export function useRaekkevisning(): boolean {
  return useSyncExternalStore(abonner, readRaekkevisning, () => false)
}
