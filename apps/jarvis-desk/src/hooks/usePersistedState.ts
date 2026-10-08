import { useEffect, useRef, useState } from 'react'

/**
 * En `useState` der huskes i localStorage — så UI-tilstand overlever mode-skift
 * og app-genstart.
 *
 * Bjørn 4/10-2026: «hvis jeg skriver noget i composer … og lige hopper til
 * arbejde eller chat mode, så glemmer composer hvad jeg har skrevet … tekst i
 * composer skulle gerne overleve både mode skift og app genstart … det samme
 * med ændrings panel og baggrundsjobs panel og browser panel — appen husker ikk
 * om de var åbne … alle paneler nulstiller ved app genstart».
 *
 * Alt det boede i løse `useState(...)`, der nulstilles i det øjeblik komponenten
 * unmountes (mode-skift) eller processen genstarter. Denne hook giver dem ét
 * sted at bo.
 *
 * Læsningen sker i initializeren og ikke i en effekt: første render har ALLEREDE
 * den gemte værdi. Lå den i en effekt, ville man se standardværdien blinke — og
 * for et panel der var åbent, ville det betyde at det først tegnede lukket.
 *
 * Skrivningen er debounced (150 ms), så et tastetryk pr. tegn ikke bliver et
 * disk-skriv pr. tegn. Værdien er altid JSON, så både `boolean`, `string` og
 * objekter kan gemmes med samme mekanisme.
 *
 * Self-safe: en utilgængelig localStorage (privat mode, fuld disk) giver
 * standardværdien frem for en kastet fejl — en UI-præference må aldrig vælte
 * fladen.
 */
export function usePersistedState<T>(key: string, fallback: T, persist = true) {
  const [value, setValue] = useState<T>(() => {
    if (!persist) return fallback
    try {
      const raw = localStorage.getItem(key)
      if (raw === null) return fallback
      return JSON.parse(raw) as T
    } catch {
      return fallback
    }
  })

  // Den nyeste værdi i en ref, så unmount-cleanup'en kan skrive den uden at
  // effekten skal gøre det for hver ændring (det ville ophæve debouncen).
  const nyeste = useRef(value)
  nyeste.current = value
  const persistRef = useRef(persist)
  persistRef.current = persist
  const previousPersist = useRef(persist)

  useEffect(() => {
    if (previousPersist.current === persist) return
    previousPersist.current = persist
    if (!persist) {
      setValue(fallback)
    } else {
      try {
        const raw = localStorage.getItem(key)
        setValue(raw === null ? fallback : JSON.parse(raw) as T)
      } catch {
        setValue(fallback)
      }
    }
  }, [persist, key, fallback])

  useEffect(() => {
    if (!persist) return
    const id = setTimeout(() => {
      try { localStorage.setItem(key, JSON.stringify(nyeste.current)) } catch { /* ignoreres — UI-præference, ikke kritisk */ }
    }, 150)
    return () => clearTimeout(id)
  }, [key, value, persist])

  // Skriv ved unmount. Et mode-skift kan ske INDEN FOR debounce-vinduet — målt i
  // test: unmount efter 0 ms — og så ville kladden aldrig nå disken, som er
  // præcis den fejl denne hook findes for at lukke.
  useEffect(() => () => {
    if (!persistRef.current) return
    try { localStorage.setItem(key, JSON.stringify(nyeste.current)) } catch { /* ignoreres */ }
  }, [key])

  return [value, setValue] as const
}
