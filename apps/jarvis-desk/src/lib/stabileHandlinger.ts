import { useCallback, useLayoutEffect, useRef } from 'react'

/**
 * Stabile funktioner til memoiserede rækker (profileret 19/9-2026).
 *
 * MessageRow er memo — men visningerne gav hver række nye funktioner ved
 * hver render (`onTogglePin={() => …}`, `onResend={resend}`), og i chat også
 * et nyt `config`-objekt. Så holdt memo'en aldrig: HVER afsluttet besked
 * (260 i Bjørns code-session) blev renderet om ved HVER stream-opdatering —
 * kilder, artefakt-genkendelse, ikoner og DOM-commits for hele samtalen.
 *
 * Funktionerne her har samme identitet hele komponentens levetid, men kalder
 * altid den SENESTE udgave — så en række der ikke renderes om, bruger aldrig
 * en forældet tilstand (arbejdsområde, session, præferencer).
 */
export function useSenesteFn<A extends unknown[], R>(fn: (...a: A) => R): (...a: A) => R {
  const ref = useRef(fn)
  useLayoutEffect(() => { ref.current = fn })
  return useCallback((...a: A) => ref.current(...a), [])
}

/** Én stabil funktion pr. id: `forRaekke(m.id)` giver den samme funktion hver
 *  gang for samme besked, og den kalder den seneste `fn(id)`. */
export function useRaekkeFn(fn: (id: string) => void): (id: string) => () => void {
  const seneste = useSenesteFn(fn)
  const cache = useRef(new Map<string, () => void>())
  return useCallback((id: string) => {
    let f = cache.current.get(id)
    if (!f) { f = () => seneste(id); cache.current.set(id, f) }
    return f
  }, [seneste])
}
