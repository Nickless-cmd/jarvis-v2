import { useEffect, useRef, useState } from 'react'
import { AppState } from 'react-native'
import * as SecureStore from 'expo-secure-store'

/** Én nøgle pr. samtale: SecureStore advarer over 2 KB, et samlet kort ville vokse. */
const noegle = (sid: string) => `sidst-set.${sid.replace(/[^A-Za-z0-9._-]/g, '_')}`

/** En optimistisk besked har et midlertidigt id; den kan ikke huskes. */
const erEndelig = (id: string) => !/^(u-|opt-|local-|tmp-)/.test(id)

/**
 * «Nye beskeder»-skillelinjen — som desk'ens `useNyeBeskeder` (Claude Desktop
 * §10). Returnerer id'et på den FØRSTE besked man ikke har set, eller null.
 *
 * - Åbner man en samtale hvor der er kommet noget siden sidst, står linjen
 *   over det første nye.
 * - Har man scrollet op, og der lander nyt imens, markeres det første af det.
 *
 * Positionen fryses, til man skifter samtale — en linje der flyttede sig
 * mens man læste, ville pege forkert.
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
      setNy(null)
      const sid = sessionId
      const snapshot = ids
      void SecureStore.getItemAsync(noegle(sid)).then((sidst) => {
        if (afgjort.current !== sid) return
        const i = sidst ? snapshot.indexOf(sidst) : -1
        setNy(i >= 0 && i < snapshot.length - 1 ? snapshot[i + 1]! : null)
      }).catch(() => undefined)
      return
    }
    if (ids.length > forrigeAntal.current && !iBund) {
      const foerste = ids[forrigeAntal.current]
      setNy((n) => n ?? foerste ?? null)
    }
    forrigeAntal.current = ids.length
  }, [sessionId, ids.length]) // eslint-disable-line react-hooks/exhaustive-deps

  // Husk hvad man har set — kun i bund og kun når appen er fremme.
  useEffect(() => {
    if (!sessionId || !iBund || AppState.currentState !== 'active') return
    const sidste = [...ids].reverse().find(erEndelig)
    if (sidste) void SecureStore.setItemAsync(noegle(sessionId), sidste).catch(() => undefined)
  }, [sessionId, ids.length, iBund]) // eslint-disable-line react-hooks/exhaustive-deps

  return ny
}
