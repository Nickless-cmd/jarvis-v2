/**
 * Lokal Discord-gateway (TOTP Fase 5, Lag 2 — spec §5.2).
 *
 * Kører på BRUGERENS maskine (Electron main). Forbinder til brugerens EGEN
 * Discord-server med deres bot-token — token forlader ALDRIG maskinen (Claude-
 * Desktop-model). Native Bjørn-server er urørt (separat, server-side gateway).
 *
 * Flow pr. besked:
 *   1. on messageCreate (spring egne/bot-beskeder over)
 *   2. capturer baseline-svar-ts → POST /plugins/channel/{id}/inbound
 *      (serveren håndhæver plugin_ruleset hardblock + dispatcher Jarvis-run)
 *   3. poll /plugins/channel/{id}/response til nyt assistant-svar → channel.send()
 *
 * Robust: multi-server, reconnection-backoff (discord.js auto-reconnecter +
 * login-retry), status-rapportering, attachments-prefix.
 */
import {
  Client, GatewayIntentBits, Events, Partials,
  type Message,
} from 'discord.js'

export interface ChannelPluginConfig {
  id: string          // plugin_id (fx "discord-local" eller "discord-local:<serverId>")
  name: string
  botToken: string    // KLIENT-side, sendes aldrig til Jarvis-serveren
  serverId: string
}

interface GatewayDeps {
  apiBaseUrl: string
  authToken?: string
  log?: (msg: string) => void
}

const POLL_INTERVAL_MS = 1500
const POLL_TIMEOUT_MS = 120_000
const MAX_BACKOFF_MS = 60_000

export class LocalDiscordGateway {
  private clients = new Map<string, Client>()
  private backoff = new Map<string, number>()
  private stopped = false
  private readonly apiBaseUrl: string
  private readonly authToken?: string
  private readonly log: (m: string) => void

  constructor(deps: GatewayDeps) {
    this.apiBaseUrl = deps.apiBaseUrl.replace(/\/$/, '')
    this.authToken = deps.authToken
    this.log = deps.log ?? (() => {})
  }

  start(configs: ChannelPluginConfig[]): void {
    this.stopped = false
    for (const cfg of configs) {
      if (cfg.botToken && cfg.serverId) this.connectServer(cfg)
    }
  }

  stop(): void {
    this.stopped = true
    for (const [, client] of this.clients) {
      try { void client.destroy() } catch { /* noop */ }
    }
    this.clients.clear()
  }

  /** Proaktiv udgående besked (§18.5 Fase 2): find en tekst-kanal ved navn på
   *  tværs af forbundne servere og send. Returnerer true ved første succes. */
  async sendToChannel(channelName: string, text: string): Promise<boolean> {
    const want = channelName.trim().toLowerCase().replace(/^#/, '')
    for (const [, client] of this.clients) {
      const ch = client.channels.cache.find(
        (c) => 'name' in c && typeof (c as { name?: string }).name === 'string'
          && (c as { name: string }).name.toLowerCase() === want
          && c.isTextBased() && 'send' in c,
      )
      if (!ch) continue
      try {
        const sendable = ch as unknown as { send: (c: string) => Promise<unknown> }
        for (const chunk of chunkText(text, 1900)) await sendable.send(chunk)
        return true
      } catch (e) {
        this.log(`sendToChannel[${channelName}]: ${String(e).slice(0, 120)}`)
      }
    }
    return false
  }

  private connectServer(cfg: ChannelPluginConfig): void {
    if (this.stopped) return
    const client = new Client({
      intents: [
        GatewayIntentBits.Guilds,
        GatewayIntentBits.GuildMessages,
        GatewayIntentBits.MessageContent,
        GatewayIntentBits.DirectMessages,
      ],
      partials: [Partials.Channel],
    })

    client.once(Events.ClientReady, (c) => {
      this.backoff.set(cfg.id, 0)
      this.log(`localDiscord[${cfg.name}]: forbundet som ${c.user.tag}`)
      void this.reportStatus(cfg.id, 'connected', c.user.tag)
    })

    client.on(Events.MessageCreate, (msg) => { void this.onMessage(cfg, msg) })

    client.on(Events.Error, (err) => {
      this.log(`localDiscord[${cfg.name}]: fejl ${String(err).slice(0, 120)}`)
      void this.reportStatus(cfg.id, 'failed', String(err).slice(0, 120))
    })

    client.on(Events.ShardDisconnect, () => {
      void this.reportStatus(cfg.id, 'offline', 'shard disconnected')
    })

    this.clients.set(cfg.id, client)
    client.login(cfg.botToken).catch((err) => {
      void this.reportStatus(cfg.id, 'failed', String(err).slice(0, 120))
      this.scheduleReconnect(cfg)
    })
  }

  private scheduleReconnect(cfg: ChannelPluginConfig): void {
    if (this.stopped) return
    const prev = this.backoff.get(cfg.id) ?? 0
    const next = Math.min(prev ? prev * 2 : 2000, MAX_BACKOFF_MS)
    const jitter = Math.floor(next * 0.2 * ((cfg.serverId.length % 5) / 5))
    this.backoff.set(cfg.id, next)
    this.log(`localDiscord[${cfg.name}]: genforbinder om ${next + jitter}ms`)
    setTimeout(() => {
      try { void this.clients.get(cfg.id)?.destroy() } catch { /* noop */ }
      this.clients.delete(cfg.id)
      this.connectServer(cfg)
    }, next + jitter)
  }

  private async onMessage(cfg: ChannelPluginConfig, msg: Message): Promise<void> {
    try {
      if (msg.author.bot) return // spring bots inkl. os selv over
      const ch = msg.channel
      if (!ch.isTextBased() || !('send' in ch)) return // kun sendbare tekst-kanaler
      const channelName = ('name' in ch ? (ch as { name?: string }).name : '') || ''
      const attachmentPrefix = msg.attachments.size
        ? `[vedhæftet: ${[...msg.attachments.values()].map((a) => a.name).join(', ')}] `
        : ''
      const text = attachmentPrefix + (msg.content || '')
      if (!text.trim()) return

      // 1. baseline — seneste svar FØR vi sender, så vi kun poster det NYE svar
      const sessionId = `plugin-${cfg.id}-${channelName}`
      const baseline = await this.getResponse(cfg.id, sessionId, '')
      const baselineTs = baseline?.ts ?? ''

      // 2. inbound (serveren håndhæver ruleset + dispatcher run)
      const inbound = await this.postInbound(cfg.id, {
        channel: channelName,
        text,
        author_role: 'member',
        hour: new Date().getHours(),
      })
      if (!inbound || !inbound.allowed) return

      // 3. poll til nyt svar → post i kanalen
      const reply = await this.pollResponse(cfg.id, inbound.session_id, baselineTs)
      if (reply) {
        // Discord-beskedgrænse 2000 tegn — del op hvis nødvendigt.
        const sendable = ch as { send: (c: string) => Promise<unknown> }
        for (const chunk of chunkText(reply, 1900)) {
          await sendable.send(chunk)
        }
      }
    } catch (e) {
      this.log(`localDiscord[${cfg.name}]: onMessage-fejl ${String(e).slice(0, 120)}`)
    }
  }

  private async postInbound(
    pluginId: string,
    body: { channel: string; text: string; author_role: string; hour: number },
  ): Promise<{ allowed: boolean; session_id?: string } | null> {
    try {
      const r = await fetch(`${this.apiBaseUrl}/api/plugins/channel/${encodeURIComponent(pluginId)}/inbound`, {
        method: 'POST',
        headers: this.headers(),
        body: JSON.stringify({ body }),
      })
      if (!r.ok) return null
      return (await r.json()) as { allowed: boolean; session_id?: string }
    } catch { return null }
  }

  private async getResponse(pluginId: string, sessionId: string, afterTs: string): Promise<{ ready: boolean; text: string; ts: string } | null> {
    try {
      const url = `${this.apiBaseUrl}/api/plugins/channel/${encodeURIComponent(pluginId)}/response`
        + `?session_id=${encodeURIComponent(sessionId)}&after_ts=${encodeURIComponent(afterTs)}`
      const r = await fetch(url, { headers: this.headers() })
      if (!r.ok) return null
      return (await r.json()) as { ready: boolean; text: string; ts: string }
    } catch { return null }
  }

  private async pollResponse(pluginId: string, sessionId: string | undefined, afterTs: string): Promise<string> {
    if (!sessionId) return ''
    const deadline = Date.now() + POLL_TIMEOUT_MS
    while (Date.now() < deadline && !this.stopped) {
      const res = await this.getResponse(pluginId, sessionId, afterTs)
      if (res?.ready && res.text) return res.text
      await sleep(POLL_INTERVAL_MS)
    }
    return ''
  }

  private async reportStatus(pluginId: string, status: string, detail = ''): Promise<void> {
    try {
      const url = `${this.apiBaseUrl}/api/plugins/channel/${encodeURIComponent(pluginId)}/status`
        + `?status=${encodeURIComponent(status)}&detail=${encodeURIComponent(detail)}`
      await fetch(url, { method: 'POST', headers: this.headers() })
    } catch { /* best-effort */ }
  }

  private headers(): Record<string, string> {
    const h: Record<string, string> = { 'Content-Type': 'application/json' }
    if (this.authToken) h['Authorization'] = `Bearer ${this.authToken}`
    return h
  }
}

function chunkText(s: string, size: number): string[] {
  const out: string[] = []
  for (let i = 0; i < s.length; i += size) out.push(s.slice(i, i + size))
  return out.length ? out : ['']
}

function sleep(ms: number): Promise<void> {
  return new Promise((r) => setTimeout(r, ms))
}
