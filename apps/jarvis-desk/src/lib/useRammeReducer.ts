import { useCallback, useEffect, useRef, useState } from 'react'

/**
 * `useReducer`, men events samles og anvendes ÉN gang pr. kadence-vindue.
 *
 * Profileret 19/9-2026: stream-konteksten ændrede sig ved HVER delta, og
 * React gennemgik hele komponenttræet (57.000 DOM-elementer i en lang
 * samtale) for at finde konteksts forbrugere — propagateContextChanges ~5 %
 * af render-tråden, oven i én render pr. delta. Deltaer kommer hurtigere end
 * skærmen kan vise dem; ét opdateringsskridt pr. frame er alt øjet ser.
 *
 * KADENCE (målt 29/9-2026): serveren leverer nu ~66 deltaer/s jævnt (median
 * gap 13 ms efter poll-fixet i chat_stream_v2 — 95 ms-kvantiseringen er væk).
 * Ét rAF gav derfor op til ~60 opdateringer/s — mere end skærmen viser og
 * mere end øjet følger, og nok til at mætte render-tråden på en lang samtale.
 * KADENCE_FRAMES = 3 lægger ~50 ms mellem opdateringerne ved 60 Hz → et loft
 * på ~20/s. Samme mønster som DeepSeek Harness bruger i sit assembly-lag
 * (tre nestede rAF), og det er dér deres stream føles glat ved samme kilde.
 *
 * Det er en KADENCE-BEGRÆNSER, ikke en burst-samler: en burst på 0,5 ms
 * kollapser til én render under både ét og tre frames. Vinduet er FAST —
 * nye events forlænger det ikke, så kadencen er forudsigelig (hverken for
 * hurtig eller for langsom), i modsætning til en debounce.
 *
 * - Rækkefølgen bevares: køen reduceres i den orden eventsne kom.
 * - rAF kører IKKE når vinduet er skjult (desk i bakken). Derfor også en
 *   timer på 100 ms — ellers hobede eventsne sig op og tilstanden stod
 *   stille (fx «færdig»-notifikationen) til vinduet blev vist igen.
 * - Reduceren skal være ren; den kan kaldes to gange i StrictMode.
 */
export const FALDBAGSKALD_MS = 100

/** Antal frames et opdaterings-vindue spænder over. 3 ≈ 50 ms ved 60 Hz → ~20/s. */
export const KADENCE_FRAMES = 3

export function useRammeReducer<S, E>(reducer: (s: S, e: E) => S, init: () => S): [S, (e: E) => void] {
  const [state, setState] = useState(init)
  const koe = useRef<E[]>([])
  const planlagt = useRef<{ raf: number[]; timer: ReturnType<typeof setTimeout> } | null>(null)
  const reducerRef = useRef(reducer)
  reducerRef.current = reducer

  const toem = useCallback(() => {
    const p = planlagt.current
    if (p) {
      for (const r of p.raf) cancelAnimationFrame(r)
      clearTimeout(p.timer)
      planlagt.current = null
    }
    const events = koe.current
    if (events.length === 0) return
    koe.current = []
    setState((s) => events.reduce(reducerRef.current, s))
  }, [])

  const dispatch = useCallback((e: E) => {
    koe.current.push(e)
    if (!planlagt.current) {
      // Tre nestede rAF: den tredje tømmer køen. Vinduet er fast — et event
      // der ankommer midt i det arver den ventende frist i stedet for at
      // forlænge den.
      const raf: number[] = []
      const vent = (tilbage: number) => {
        raf.push(requestAnimationFrame(() => {
          if (tilbage <= 1) toem()
          else vent(tilbage - 1)
        }))
      }
      vent(KADENCE_FRAMES)
      planlagt.current = { raf, timer: setTimeout(toem, FALDBAGSKALD_MS) }
    }
  }, [toem])

  useEffect(() => () => {
    const p = planlagt.current
    if (p) {
      for (const r of p.raf) cancelAnimationFrame(r)
      clearTimeout(p.timer)
    }
  }, [])

  return [state, dispatch]
}
