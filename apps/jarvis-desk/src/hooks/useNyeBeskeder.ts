import { useEffect, useRef, useState } from 'react'

/** localStorage: sessionId → id på den sidste besked man har SET. */
const NOEGLE = 'jarvis-desk:sidst-set'
const MAKS = 300

function laes(): Record<string, string> {
  try { return JSON.parse(localStorage.getItem(NOEGLE) ?? '{}') as Record<string, string> } catch { return {} }
}
function skriv(sid: string, id: string): void {
  try {
    const m = laes()
    if (m[sid] === id) return
    delete m[sid]
    m[sid] = id
    const noegler = Object.keys(m)
    for (const k of noegler.slice(0, Math.max(0, noegler.length - MAKS))) delete m[k]
    localStorage.setItem(NOEGLE, JSON.stringify(m))
  } catch { /* localStorage utilgængelig — ingen skillelinje, intet brud */ }
}

/** En optimistisk besked (`u-…`) får et nyt id af serveren; den kan ikke huskes. */
const erEndelig = (id: string) => !id.startsWith('u-')

/**
 * «Nye beskeder»-skillelinjen — Claude Desktops `role="separator"` (§10).
 * Returnerer id'et på den FØRSTE besked man ikke har set, eller null.
 *
 * To veje til en skillelinje:
 * - Man åbner en samtale hvor der er kommet noget siden sidst (Jarvis svarede
 *   på telefonen, et autonomt run skrev).
 * - Man har scrollet op, og der lander nye beskeder imens.
 *
 * Positionen FRYSES når den er fundet: en linje der flyttede sig mens man læste,
 * ville pege forkert. Den nulstilles først når man skifter samtale.
 */
export function useNyeBeskeder(sessionId: string | null, ids: string[], iBund: boolean): string | null {
  const [ny, setNy] = useState<string | null>(null)
  const afgjort = useRef<string | null>(null)
  const forrigeAntal = useRef(0)

  useEffect(() => {
    if (!sessionId) { setNy(null); afgjort.current = null; forrigeAntal.current = 0; return }
    if (afgjort.current !== sessionId) {
      if (ids.length === 0) return
      afgjort.current = sessionId
      forrigeAntal.current = ids.length
      const sidst = laes()[sessionId]
      const i = sidst ? ids.indexOf(sidst) : -1
      setNy(i >= 0 && i < ids.length - 1 ? ids[i + 1]! : null)
      return
    }
    // Samme samtale: kom der nyt mens man var scrollet op?
    if (ids.length > forrigeAntal.current && !iBund) {
      const foerste = ids[forrigeAntal.current]
      setNy((n) => n ?? foerste ?? null)
    }
    forrigeAntal.current = ids.length
  }, [sessionId, ids.length]) // eslint-disable-line react-hooks/exhaustive-deps

  // Husk hvad man har set — kun når man er i bund og faktisk kigger.
  useEffect(() => {
    if (!sessionId || !iBund || typeof document !== 'undefined' && document.visibilityState !== 'visible') return
    const sidste = [...ids].reverse().find(erEndelig)
    if (sidste) skriv(sessionId, sidste)
  }, [sessionId, ids.length, iBund]) // eslint-disable-line react-hooks/exhaustive-deps

  return ny
}
