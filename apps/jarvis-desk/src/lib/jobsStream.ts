import type { ApiConfig } from './api'
import type { LiveJobEvent } from './liveJobs'

const MAX_FRAME_BYTES = 1024 * 1024

/**
 * Genforbindelses-trin. Det sidste trin GENTAGES — strømmen giver ikke op.
 *
 * ## Hvorfor (17/11-2026)
 *
 * Før gav den op efter fem forsøg, i alt 15,5 sekunder, og kaldte `onError`.
 * Panelet hentede så ét snapshot og stod stille indtil Bjørn lukkede og
 * genåbnede det — hvilket ikke var en genforbindelse, men en frisk mount.
 *
 * 15,5 sekunder er kortere end en API-genstart. Enhver deploy dræber alle
 * åbne jobpaneler, og de rejste sig aldrig igen. De to andre streams i Desk
 * tålte 31 s (sideopgaver) og op til 30 s (chatten); jobs-strømmen var den
 * mest skrøbelige af de tre — og den der viser maskinens arbejde.
 *
 * Nu: uendeligt mange forsøg med 15 s som loft. En strøm der ikke kan
 * etablere sig koster ét kald hvert 15. sekund — det er billigere end et
 * panel der lyver om at være levende.
 */
const BACKOFF = [500, 1000, 2000, 4000, 8000, 15_000]

/**
 * Serveren sender `heartbeat` hver 15. sekund når der er stille
 * (`jarvisx_processes.py`: `asyncio.wait_for(..., timeout=15.0)`). Tre gange
 * den kadence er grænsen.
 *
 * ## Hvorfor den findes
 *
 * `reader.read()` på en socket der døde under dvale eller et netværksskift
 * hverken fejler eller returnerer — den venter for evigt. Uden denne vagt ser
 * panelet forbundet ud og står bare stille, mens Bjørn ser et indhold der
 * hænger. Serverens heartbeat kan ikke redde det: den sendes, men når aldrig
 * frem over en død socket, og klienten kan ikke skelne «ingen ændringer» fra
 * «ingen forbindelse».
 */
const IDLE_TIMEOUT_MS = 45_000

export class JobsStreamError extends Error {
  constructor(message: string, readonly kind: 'network' | 'auth' | 'protocol') {
    super(message)
    this.name = 'JobsStreamError'
  }
}

export interface JobsStreamHandlers {
  sessionId?: string | null
  after?: number
  onEvent: (event: LiveJobEvent) => void
  onError: (error: JobsStreamError) => void
}

export function startJobsStream(config: ApiConfig, handlers: JobsStreamHandlers): { abort(): void } {
  const controller = new AbortController()
  let cursor = handlers.after

  const run = async () => {
    for (let attempt = 0; !controller.signal.aborted; attempt += 1) {
      // Én controller pr. FORBINDELSE, koblet til den ydre. Idle-vagten
      // aborterer kun denne forbindelse — den ydre er brugerens, og en
      // genforbindelse må ikke kunne lukke panelet.
      const forbindelse = new AbortController()
      const afbrydYdre = () => forbindelse.abort()
      controller.signal.addEventListener('abort', afbrydYdre, { once: true })
      let idleTimer: ReturnType<typeof setTimeout> | null = null
      let idleUdløb = false
      // Læseren kendes først efter `fetch`, men vagten skal kunne frigøre
      // den: en pending `read()` på en død socket bliver ikke altid afvist
      // af et abort alene, og så ville den ligge og holde bufferen.
      let aktivLæser: ReadableStreamDefaultReader<Uint8Array> | null = null
      const nulstilIdle = () => {
        if (idleTimer) clearTimeout(idleTimer)
        idleTimer = setTimeout(() => {
          idleUdløb = true
          forbindelse.abort()
          void aktivLæser?.cancel().catch(() => {})
        }, IDLE_TIMEOUT_MS)
      }
      const stopIdle = () => {
        if (idleTimer) { clearTimeout(idleTimer); idleTimer = null }
      }

      try {
        const query = new URLSearchParams()
        if (handlers.sessionId) query.set('session_id', handlers.sessionId)
        if (cursor !== undefined) query.set('after', String(cursor))
        nulstilIdle()
        const response = await fetch(
          `${config.apiBaseUrl.replace(/\/$/, '')}/api/jobs/stream?${query.toString()}`,
          {
            headers: config.authToken ? { Authorization: `Bearer ${config.authToken}` } : {},
            signal: forbindelse.signal,
          },
        )
        if (response.status === 401 || response.status === 403) {
          throw new JobsStreamError('Adgang til jobstrømmen blev afvist', 'auth')
        }
        if (!response.ok || !response.body) {
          throw new JobsStreamError(`Jobstrøm HTTP ${response.status}`, 'network')
        }
        const reader = response.body.getReader()
        aktivLæser = reader
        const decoder = new TextDecoder()
        let pending = ''
        while (!controller.signal.aborted) {
          const { value, done } = await reader.read()
          nulstilIdle()
          if (done) throw new JobsStreamError('Jobstrømmen lukkede', 'network')
          pending += decoder.decode(value, { stream: true })
          let boundary = pending.indexOf('\n\n')
          while (boundary >= 0) {
            const raw = pending.slice(0, boundary)
            if (raw.length > MAX_FRAME_BYTES) {
              throw new JobsStreamError('For stor SSE-ramme', 'protocol')
            }
            pending = pending.slice(boundary + 2)
            const data = raw.split('\n')
              .filter((line) => line.startsWith('data:'))
              .map((line) => line.slice(5).trimStart()).join('\n')
            if (data) {
              let parsed: LiveJobEvent
              try { parsed = JSON.parse(data) as LiveJobEvent } catch {
                throw new JobsStreamError('Ugyldig JSON i jobstrømmen', 'protocol')
              }
              if (!parsed || typeof parsed.type !== 'string') {
                throw new JobsStreamError('Jobevent mangler type', 'protocol')
              }
              if (Number.isFinite(parsed.cursor)) cursor = parsed.cursor
              handlers.onEvent(parsed)
            }
            boundary = pending.indexOf('\n\n')
          }
          if (pending.length > MAX_FRAME_BYTES) {
            throw new JobsStreamError('For stor SSE-ramme', 'protocol')
          }
        }
        return
      } catch (error) {
        // Brugeren lukkede panelet — intet at genforbinde til.
        if (controller.signal.aborted) return
        const typed = idleUdløb
          ? new JobsStreamError('Jobstrømmen var stille for længe', 'network')
          : error instanceof JobsStreamError
            ? error
            : new JobsStreamError(error instanceof Error ? error.message : 'Netværksfejl', 'network')
        // Auth og protokol kan ikke løses ved at prøve igen: tokenet er
        // ugyldigt, eller serveren taler et andet sprog end os.
        if (typed.kind === 'auth' || typed.kind === 'protocol') {
          handlers.onError(typed)
          return
        }
        const vent = BACKOFF[Math.min(attempt, BACKOFF.length - 1)]
        await new Promise((resolve) => setTimeout(resolve, vent))
      } finally {
        stopIdle()
        controller.signal.removeEventListener('abort', afbrydYdre)
      }
    }
  }
  void run()
  return { abort: () => controller.abort() }
}
