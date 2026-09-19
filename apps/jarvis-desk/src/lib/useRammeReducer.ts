import { useCallback, useEffect, useRef, useState } from 'react'

/**
 * `useReducer`, men events samles og anvendes ÉN gang pr. frame.
 *
 * Profileret 19/9-2026: stream-konteksten ændrede sig ved HVER delta, og
 * React gennemgik hele komponenttræet (57.000 DOM-elementer i en lang
 * samtale) for at finde konteksts forbrugere — propagateContextChanges ~5 %
 * af render-tråden, oven i én render pr. delta. Deltaer kommer hurtigere end
 * skærmen kan vise dem; ét opdateringsskridt pr. frame er alt øjet ser.
 *
 * - Rækkefølgen bevares: køen reduceres i den orden eventsne kom.
 * - rAF kører IKKE når vinduet er skjult (desk i bakken). Derfor også en
 *   timer på 100 ms — ellers hobede eventsne sig op og tilstanden stod
 *   stille (fx «færdig»-notifikationen) til vinduet blev vist igen.
 * - Reduceren skal være ren; den kan kaldes to gange i StrictMode.
 */
export const FALDBAGSKALD_MS = 100

export function useRammeReducer<S, E>(reducer: (s: S, e: E) => S, init: () => S): [S, (e: E) => void] {
  const [state, setState] = useState(init)
  const koe = useRef<E[]>([])
  const planlagt = useRef<{ raf: number; timer: ReturnType<typeof setTimeout> } | null>(null)
  const reducerRef = useRef(reducer)
  reducerRef.current = reducer

  const toem = useCallback(() => {
    const p = planlagt.current
    if (p) { cancelAnimationFrame(p.raf); clearTimeout(p.timer); planlagt.current = null }
    const events = koe.current
    if (events.length === 0) return
    koe.current = []
    setState((s) => events.reduce(reducerRef.current, s))
  }, [])

  const dispatch = useCallback((e: E) => {
    koe.current.push(e)
    if (!planlagt.current) {
      planlagt.current = { raf: requestAnimationFrame(toem), timer: setTimeout(toem, FALDBAGSKALD_MS) }
    }
  }, [toem])

  useEffect(() => () => {
    const p = planlagt.current
    if (p) { cancelAnimationFrame(p.raf); clearTimeout(p.timer) }
  }, [])

  return [state, dispatch]
}
