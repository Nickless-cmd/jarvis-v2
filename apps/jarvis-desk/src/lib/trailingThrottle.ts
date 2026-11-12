/** Højst ét kald pr. `ms`: det første straks, og ét sidste når strømmen er forbi.
 *
 *  Til en WebSocket-strøm der skal udløse en genhentning. Uden en throttle blev hver
 *  eneste besked en fuld GET-runde (6 endpoints → ~490 × 429 pr. endpoint på 5 minutter,
 *  12/11-2026). «Trailing» sikrer at den sidste besked i en byge ikke glemmes: tilstanden
 *  efter den byge bliver hentet.
 *
 *  `fn` der kaster rammer hverken throttle eller de næste kald. */
export function lavTrailingThrottle(fn: () => void, ms: number): { kald: () => void; annuller: () => void } {
  let sidste = Number.NEGATIVE_INFINITY
  let ventende: ReturnType<typeof setTimeout> | null = null

  const koer = () => {
    sidste = Date.now()
    try { fn() } catch { /* en fejlet genhentning må ikke vælte strømmen */ }
  }

  return {
    kald() {
      const gaaet = Date.now() - sidste
      if (gaaet >= ms) { koer(); return }
      if (ventende) return                    // et trailing kald er allerede planlagt
      ventende = setTimeout(() => { ventende = null; koer() }, ms - gaaet)
    },
    annuller() {
      if (ventende) { clearTimeout(ventende); ventende = null }
    },
  }
}

/** Hvor ofte en WebSocket-besked højst må udløse en genhentning. */
export const WS_GENHENT_MS = 3000
