import { useCallback, useEffect, useRef, useState } from 'react'
import type { ApiConfig } from './api'
import type { SideTask } from './sideTasksApi'
import { getAlleSideTasks } from './sideTasksApi'

/**
 * Én forbindelse til sideopgave-listen — i stedet for tre pollere.
 *
 * ## Hvorfor (25/10-2026)
 *
 * Tre visninger læste samme data med hver sin kadence: panelet kun ved mount,
 * listen hvert 8. sekund, kortet i chatten hvert 6. Bjørn: «side opgave panelet
 * burde osse streames for at undgå poll storm og sikre instans levering».
 *
 * Målt: tre forbindelser for data der ændrer sig få gange i timen — og panelet
 * opdagede slet ikke at Jarvis oprettede eller lukkede en opgave i baggrunden.
 *
 * ## Hvorfor serveren sender listen og ikke bare et signal
 *
 * Et «hent igen»-signal ville give tre fetches ved hver ændring — tre pollere
 * var så blot blevet til tre fetches. Serveren har allerede læst lageret når
 * den publicerer, så den sender det med. Klienten tegner, den spørger ikke.
 *
 * ## Degradering, ikke primær vej
 *
 * Fejler strømmen (auth, netværk, protokol), falder den tilbage til ét fetch
 * med 20 sekunders mellemrum. Det er langsommere end i dag, men det er en
 * nødløsning der holder listen brugbar — ikke den vej vi regner med.
 */

const FALLBACK_POLL_MS = 20_000
const BACKOFF = [1000, 2000, 4000, 8000, 15_000]

export interface SideTasksStreamHandlers {
  onOpgaver: (opgaver: SideTask[]) => void
  onFejl?: (besked: string) => void
}

export function startSideTasksStream(
  config: ApiConfig,
  handlers: SideTasksStreamHandlers,
): { abort(): void } {
  const controller = new AbortController()
  let fallbackTimer: ReturnType<typeof setTimeout> | null = null
  let fallbackPoll: ReturnType<typeof setInterval> | null = null
  let brugtFallback = false

  const stopFallback = () => {
    if (fallbackTimer) { clearTimeout(fallbackTimer); fallbackTimer = null }
    if (fallbackPoll) { clearInterval(fallbackPoll); fallbackPoll = null }
  }

  const fallback = async (grund: string) => {
    if (brugtFallback || controller.signal.aborted) return
    brugtFallback = true
    handlers.onFejl?.(grund)
    const hent = async () => {
      if (controller.signal.aborted) return
      try {
        handlers.onOpgaver(await getAlleSideTasks(config))
      } catch {
        // Fejlen er allerede meldt én gang; en tavs gentagelse er ærligere
        // end en fejlbesked hvert 20. sekund.
      }
    }
    await hent()
    fallbackPoll = setInterval(() => void hent(), FALLBACK_POLL_MS)
  }

  const run = async () => {
    for (let forsøg = 0; !controller.signal.aborted; forsøg += 1) {
      try {
        const response = await fetch(
          `${config.apiBaseUrl.replace(/\/$/, '')}/cowork/side-tasks/stream`,
          {
            headers: config.authToken ? { Authorization: `Bearer ${config.authToken}` } : {},
            signal: controller.signal,
          },
        )
        if (response.status === 401 || response.status === 403) {
          await fallback('Strømmen blev afvist — hentet med mellemrum i stedet')
          return
        }
        if (!response.ok || !response.body) {
          throw new Error(`Sideopgave-strøm HTTP ${response.status}`)
        }
        const reader = response.body.getReader()
        const decoder = new TextDecoder()
        let pending = ''
        while (!controller.signal.aborted) {
          const { value, done } = await reader.read()
          if (done) throw new Error('Sideopgave-strømmen lukkede')
          pending += decoder.decode(value, { stream: true })
          let graense = pending.indexOf('\n\n')
          while (graense >= 0) {
            const raw = pending.slice(0, graense)
            pending = pending.slice(graense + 2)
            graense = pending.indexOf('\n\n')
            if (!raw.trim() || raw.startsWith(':')) continue // keepalive-ping
            const data = raw
              .split('\n')
              .filter((line) => line.startsWith('data:'))
              .map((line) => line.slice(5).trimStart())
              .join('\n')
            if (!data) continue
            let parsed: { type?: string; opgaver?: SideTask[] }
            try { parsed = JSON.parse(data) } catch { continue }
            if (parsed.type === 'snapshot' && Array.isArray(parsed.opgaver)) {
              handlers.onOpgaver(parsed.opgaver)
            }
          }
        }
      } catch (error) {
        if (controller.signal.aborted) return
        if (forsøg >= BACKOFF.length) {
          await fallback(
            error instanceof Error ? error.message : 'Strømmen kunne ikke åbnes',
          )
          return
        }
        await new Promise((resolve) => setTimeout(resolve, BACKOFF[forsøg]))
      }
    }
  }

  void run()

  return {
    abort: () => {
      controller.abort()
      stopFallback()
    },
  }
}

/**
 * Sideopgaver via strømmen. `null` betyder «ikke hentet endnu» — en tom liste
 * og en manglende liste er ikke det samme, og det var hele det problem
 * panelet blev bygget for at løse.
 */
export function useSideTasks(config?: ApiConfig): {
  opgaver: SideTask[] | null
  fejl: string
  hent: () => Promise<void>
} {
  const [opgaver, setOpgaver] = useState<SideTask[] | null>(null)
  const [fejl, setFejl] = useState('')
  const streamRef = useRef<{ abort(): void } | null>(null)

  /** Efter en handling (luk, redigér, skjul) — så svaret ikke venter på et signal. */
  const hent = useCallback(async () => {
    if (!config) return
    try {
      setOpgaver(await getAlleSideTasks(config))
      setFejl('')
    } catch (e) {
      setFejl(e instanceof Error ? e.message : 'Kunne ikke hente sideopgaverne')
    }
  }, [config])

  useEffect(() => {
    if (!config) return
    // Første visning: ét fetch med det samme. Strømmen etablerer sig først
    // efter en round-trip, og listen skal stå der inden da — ellers ville
    // panelet blinke tomt hver gang det åbnes.
    void hent()
    streamRef.current?.abort()
    streamRef.current = startSideTasksStream(config, {
      onOpgaver: (liste) => { setOpgaver(liste); setFejl('') },
      onFejl: (besked) => setFejl(besked),
    })
    return () => { streamRef.current?.abort(); streamRef.current = null }
  }, [config?.apiBaseUrl, config?.authToken]) // eslint-disable-line react-hooks/exhaustive-deps

  return { opgaver, fejl, hent }
}
