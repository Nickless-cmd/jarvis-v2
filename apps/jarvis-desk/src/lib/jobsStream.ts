import type { ApiConfig } from './api'
import type { LiveJobEvent } from './liveJobs'

const MAX_FRAME_BYTES = 1024 * 1024
const BACKOFF = [500, 1000, 2000, 4000, 8000]

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
      try {
        const query = new URLSearchParams()
        if (handlers.sessionId) query.set('session_id', handlers.sessionId)
        if (cursor !== undefined) query.set('after', String(cursor))
        const response = await fetch(
          `${config.apiBaseUrl.replace(/\/$/, '')}/api/jobs/stream?${query.toString()}`,
          {
            headers: config.authToken ? { Authorization: `Bearer ${config.authToken}` } : {},
            signal: controller.signal,
          },
        )
        if (response.status === 401 || response.status === 403) {
          throw new JobsStreamError('Adgang til jobstrømmen blev afvist', 'auth')
        }
        if (!response.ok || !response.body) {
          throw new JobsStreamError(`Jobstrøm HTTP ${response.status}`, 'network')
        }
        const reader = response.body.getReader()
        const decoder = new TextDecoder()
        let pending = ''
        while (!controller.signal.aborted) {
          const { value, done } = await reader.read()
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
      } catch (error) {
        if (controller.signal.aborted) return
        const typed = error instanceof JobsStreamError
          ? error : new JobsStreamError(error instanceof Error ? error.message : 'Netværksfejl', 'network')
        if (typed.kind === 'auth' || typed.kind === 'protocol' || attempt >= BACKOFF.length) {
          handlers.onError(typed)
          return
        }
        await new Promise((resolve) => setTimeout(resolve, BACKOFF[attempt]))
      }
    }
  }
  void run()
  return { abort: () => controller.abort() }
}
