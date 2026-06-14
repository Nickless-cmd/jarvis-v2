/**
 * App-dispatch watcher (§18.5 Fase 2).
 *
 * Poller serveren for runtime→app instruktioner og udfører dem lokalt:
 *   - notify → native OS-notifikation
 *   - send_message/send_report (Discord) → via den lokale Discord-gateway
 * Hver instruktion ack'es bagefter (også 'unsupported', så køen ikke clogger).
 *
 * Best-effort: netværksfejl springes over til næste tick. Rører IKKE den live
 * server-side Discord-gateway — additiv udgående kanal via brugerens egen app.
 */
import { Notification } from 'electron'
import { planDispatch, type AppInstruction } from './appDispatch'

interface WatcherDeps {
  apiBaseUrl: string
  authToken?: string
  /** Send en proaktiv besked via lokal Discord-gateway (null hvis ingen gateway). */
  sendDiscord: (channelName: string, text: string) => Promise<boolean>
  log?: (msg: string) => void
}

const POLL_MS = 6000

export class AppDispatchWatcher {
  private timer: ReturnType<typeof setInterval> | null = null
  private busy = false
  private readonly base: string
  private readonly authToken?: string
  private readonly sendDiscord: (c: string, t: string) => Promise<boolean>
  private readonly log: (m: string) => void

  constructor(deps: WatcherDeps) {
    this.base = deps.apiBaseUrl.replace(/\/$/, '')
    this.authToken = deps.authToken
    this.sendDiscord = deps.sendDiscord
    this.log = deps.log ?? (() => {})
  }

  start(): void {
    this.stop()
    this.timer = setInterval(() => { void this.tick() }, POLL_MS)
  }

  stop(): void {
    if (this.timer) { clearInterval(this.timer); this.timer = null }
  }

  private headers(): Record<string, string> {
    const h: Record<string, string> = { 'Content-Type': 'application/json' }
    if (this.authToken) h['Authorization'] = `Bearer ${this.authToken}`
    return h
  }

  private async tick(): Promise<void> {
    if (this.busy) return
    this.busy = true
    try {
      const r = await fetch(`${this.base}/api/cowork/app-dispatch/pending`, { headers: this.headers() })
      if (!r.ok) return
      const data = (await r.json()) as { pending?: AppInstruction[] }
      for (const instr of data.pending ?? []) {
        await this.execute(instr)
        await this.ack(instr.id)
      }
    } catch (e) {
      this.log(`appDispatch tick-fejl: ${String(e).slice(0, 120)}`)
    } finally {
      this.busy = false
    }
  }

  private async execute(instr: AppInstruction): Promise<void> {
    const plan = planDispatch(instr)
    if (plan.kind === 'notify') {
      if (Notification.isSupported()) {
        new Notification({ title: plan.title, body: plan.body }).show()
      }
    } else if (plan.kind === 'discord') {
      const ok = await this.sendDiscord(plan.channelName, plan.text)
      if (!ok) this.log(`appDispatch: kunne ikke sende til Discord-kanal '${plan.channelName}'`)
    } else {
      this.log(`appDispatch: springer over (${plan.reason})`)
    }
  }

  private async ack(id: string): Promise<void> {
    try {
      await fetch(`${this.base}/api/cowork/app-dispatch/${encodeURIComponent(id)}/ack`,
        { method: 'POST', headers: this.headers() })
    } catch { /* best-effort */ }
  }
}
