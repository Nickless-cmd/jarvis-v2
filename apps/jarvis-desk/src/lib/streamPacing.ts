/**
 * Hvilket pacing-lag Code Mode's tekst ruller med.
 *
 * ## Hvorfor der er to
 *
 * Chat Mode og Code Mode har hver sit ur paa teksten, og de er ikke ens:
 *
 *  - `usePacedBlocks` (code): 33 ms-interval, 5–28 tegn pr. tick, op til
 *    ~848 tegn i sekundet, springer frem ved 330 tegns efterslaeb og viser
 *    korte svar (≤32 tegn) straks.
 *  - `useChatPacedBlocks` (chat): requestAnimationFrame med maalt `dt`,
 *    48–72 kodepunkter pr. SEKUND, fordeler efterslaebet over 12 s og ruller
 *    faerdig efter `message_stop` hvis blokken blev set live.
 *
 * Forskellen er ikke visningen — begge tegner samme trae, samme fold og
 * samme teleportering af slutsvaret. Det er KURVEN.
 *
 * ## Hvorfor det er en lokal praeference og ikke en serverindstilling
 *
 * Det er et spoergsmaal om hvordan MIN skaerm skal foele, ikke om hvad
 * serveren skal goere — praecis som `visningsPref`. Den skal virke uden
 * netvaerk, og den skal kunne skiftes MIDT I en stroem saa man kan maerke
 * forskellen paa den samme tekst.
 *
 * `useSyncExternalStore` af samme grund som i `visningsPref`: `MessageRow` er
 * memoiseret, saa et localStorage-opslag i renderkroppen ville aldrig blive
 * koert igen naar knappen slaas om — skiftet ville foerst slaa igennem ved
 * naeste besked.
 *
 * ## Standard er `code`
 *
 * Den nuvarende adfaerd. Et skift af standarden ville aendre hvordan alle
 * samtaler foeles uden at nogen bad om det.
 */
import { useSyncExternalStore } from 'react'

export const PACE_MODE_KEY = 'jarvis-desk:code-pacing'

/** `code` = det hidtidige lag. `chat` = det jaevne. */
export type PaceMode = 'code' | 'chat'

type Lytter = () => void
const lyttere = new Set<Lytter>()

export function readPaceMode(): PaceMode {
  try {
    // Alt andet end det praecise ord `chat` falder tilbage til standarden —
    // ogsaa en halvskrevet eller fremmed vaerdi fra en aeldre build.
    return localStorage.getItem(PACE_MODE_KEY) === 'chat' ? 'chat' : 'code'
  } catch {
    // Privat vindue eller blokeret lager: den nuvarende kurve er standarden.
    return 'code'
  }
}

export function writePaceMode(mode: PaceMode): void {
  try {
    localStorage.setItem(PACE_MODE_KEY, mode)
  } catch { /* uden lager gaelder valget kun denne session */ }
  for (const l of lyttere) l()
}

function abonner(l: Lytter): () => void {
  lyttere.add(l)
  // `storage` fyrer kun i ANDRE faner, men desk kan have flere vinduer aabne
  // mod samme profil — saa foelger de med uden at skulle genstartes.
  const fraAndetVindue = (e: StorageEvent) => { if (e.key === PACE_MODE_KEY) l() }
  try { window.addEventListener('storage', fraAndetVindue) } catch { /* ingen window i test */ }
  return () => {
    lyttere.delete(l)
    try { window.removeEventListener('storage', fraAndetVindue) } catch { /* ignore */ }
  }
}

/** Live-vaerdien. Skifter med det samme naar knappen slaas om. */
export function usePaceMode(): PaceMode {
  return useSyncExternalStore(abonner, readPaceMode, () => 'code')
}
