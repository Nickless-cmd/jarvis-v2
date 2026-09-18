/**
 * Ét levende øjebliksbillede af cheap lane — hentet én gang, opdateret af
 * Centrals egen strøm.
 *
 * ## Hvorfor ikke fire timere
 *
 * Panelet før dette hentede balancer, historik, fejl og register hver for sig,
 * hver med sin egen interval. På et API med én worker er hver ekstra strøm en
 * tråd der tages fra noget andet (`centralStream.ts` bærer den historie: to
 * paneler med hver sin SSE sultede hinanden). Og fire hentninger på fire
 * tidspunkter betyder fire forskellige sandheder på samme skærm.
 *
 * Her er der ét snapshot med et `generated_at`, og Centrals strøm siger
 * hvornår det er forældet.
 *
 * ## Hvorfor sammenlægning og ikke en hentning pr. begivenhed
 *
 * Cheap lane fyrer 100–500 kald i timen. Én hentning pr. begivenhed ville
 * gøre panelet til den største belastning på det system det overvåger.
 * Begivenheder inden for 300 ms bliver til ÉN hentning.
 *
 * ## Hvorfor der stadig er en poll
 *
 * En strøm kan dø stille. Skærmen ville så vise tal fra i går uden at sige
 * det — den værste af alle tilstande, fordi den ligner ro. Fejler strømmen,
 * skifter `liveState` til `polling`, tallene hentes hvert 15. sekund, og
 * første ægte begivenhed slår pollen fra igen.
 */
import { useCallback, useEffect, useRef, useState } from 'react'
import type { ApiConfig } from './api'
import { getDashboard, type Snapshot } from './cheapLaneApi'
import { subscribeCentralStream } from './centralStream'

/** Begivenheder inden for dette vindue bliver til én hentning. */
export const DEBOUNCE_MS = 300
/** Hvor ofte der hentes når strømmen er nede. */
export const POLL_MS = 15_000

export type LiveTilstand = 'indlæser' | 'live' | 'polling' | 'fejl'

export interface CheapLaneStore {
  snapshot: Snapshot | null
  liveState: LiveTilstand
  error: string
  /** Hentet på ny lige nu — til «opdater»-knappen. */
  refresh: () => void
  /** Hvornår tallene på skærmen blev lavet (serverens tid, ikke klientens). */
  observedAt: string
}

/** Begivenheder der betyder at cheap lane har flyttet sig. Navnene er
 *  serverens egne (`runtime.cheap_lane_*`); alt andet på Centrals strøm —
 *  hukommelse, hjerteslag, samtaler — skal IKKE udløse en hentning. */
function erCheapLane(item: unknown): boolean {
  const i = item as { kind?: string; nerve?: string; cluster?: string } | null
  const tekst = `${i?.kind ?? ''} ${i?.nerve ?? ''}`.toLowerCase()
  return tekst.includes('cheap_lane') || tekst.includes('cheap-lane')
}

export function useCheapLaneStore(config: ApiConfig | undefined, windowHours = 24): CheapLaneStore {
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null)
  const [liveState, setLiveState] = useState<LiveTilstand>('indlæser')
  const [error, setError] = useState('')

  const base = config?.apiBaseUrl
  const token = config?.authToken ?? null
  // Levende referencer, så effekten ikke skal genopbygges (og dermed
  // genabonnere på strømmen) hver gang et tal ændrer sig.
  const levende = useRef(true)
  const henter = useRef(false)
  const debounce = useRef<ReturnType<typeof setTimeout> | null>(null)
  const poll = useRef<ReturnType<typeof setInterval> | null>(null)

  const hent = useCallback(async () => {
    if (!base || henter.current) return
    henter.current = true
    try {
      const s = await getDashboard({ apiBaseUrl: base, authToken: token }, windowHours)
      if (!levende.current) return
      setSnapshot(s)
      setError('')
      // Kommer et svar igennem, er forbindelsen i orden — men kun strømmen
      // afgør om vi er LIVE. En poll der lykkes er stadig en poll.
      setLiveState((t) => (t === 'indlæser' || t === 'fejl' ? 'live' : t))
    } catch (e) {
      if (!levende.current) return
      setError(e instanceof Error ? e.message : String(e))
      setLiveState((t) => (t === 'polling' ? 'polling' : 'fejl'))
    } finally {
      henter.current = false
    }
  }, [base, token, windowHours])

  const stopPoll = useCallback(() => {
    if (poll.current) { clearInterval(poll.current); poll.current = null }
  }, [])

  const startPoll = useCallback(() => {
    if (poll.current) return
    poll.current = setInterval(() => { void hent() }, POLL_MS)
  }, [hent])

  // Første hentning + ny hentning når vinduet skifter. `levende` nulstilles
  // her og ikke kun ved unmount: et svar fra det GAMLE vindue må ikke skrive
  // sig ind over det nye.
  useEffect(() => {
    levende.current = true
    void hent()
    return () => { levende.current = false }
  }, [hent])

  // Strømmen: ét abonnement, uanset hvor mange faner der er åbne.
  useEffect(() => {
    if (!base) return
    const cfg = { apiBaseUrl: base, authToken: token }
    const af = subscribeCentralStream(
      cfg,
      (item) => {
        if (!erCheapLane(item)) return
        // Begivenheder kommer igen → strømmen lever, pollen er overflødig.
        stopPoll()
        setLiveState('live')
        if (debounce.current) clearTimeout(debounce.current)
        debounce.current = setTimeout(() => { debounce.current = null; void hent() }, DEBOUNCE_MS)
      },
      () => {
        setLiveState('polling')
        startPoll()
      },
    )
    return () => {
      af()
      if (debounce.current) { clearTimeout(debounce.current); debounce.current = null }
      stopPoll()
    }
  }, [base, token, hent, startPoll, stopPoll])

  const refresh = useCallback(() => { void hent() }, [hent])

  return {
    snapshot,
    liveState,
    error,
    refresh,
    observedAt: snapshot?.generated_at ?? '',
  }
}
