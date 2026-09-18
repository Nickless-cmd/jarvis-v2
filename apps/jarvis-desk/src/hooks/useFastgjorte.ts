import { useCallback, useEffect, useState } from 'react'
import { laesPins, skiftPin } from '../lib/fastgjorteBeskeder'

/**
 * Sessionens fastgjorte beskeder — ét sted for både Chat og Code.
 *
 * Listen nulstilles ved sessionsskift og læses forfra, så en pin i én samtale
 * ikke lyser op i en anden. Uden session er listen tom: der er ikke noget at
 * fastgøre endnu.
 */
export function useFastgjorte(sessionId: string | null) {
  const [pins, setPins] = useState<string[]>([])

  useEffect(() => {
    setPins(sessionId ? laesPins(sessionId) : [])
  }, [sessionId])

  const skift = useCallback((messageId: string) => {
    if (!sessionId) return
    setPins(skiftPin(sessionId, messageId))
  }, [sessionId])

  return { pins, skift }
}
