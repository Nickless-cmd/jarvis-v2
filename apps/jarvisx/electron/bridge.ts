/**
 * JarvisX tool-bridge client.
 *
 * Opens a WebSocket to Jarvis-runtime, registers as a bridge for the
 * configured user, then handles tool_invoke messages by executing them
 * locally on the operator's desktop. Spec:
 * docs/superpowers/specs/2026-05-26-jarvisx-tool-bridge.md
 *
 * Phase 1: operator_read_file only. Add more tools by extending the
 * `handlers` map below.
 */
import { readFileSync, appendFileSync } from 'node:fs'
import { homedir } from 'node:os'
import { join } from 'node:path'
import WebSocket from 'ws'

const LOG_PATH = join(homedir(), '.config', 'jarvisx', 'bridge.log')

function fileLog(msg: string): void {
  try {
    appendFileSync(LOG_PATH, `${new Date().toISOString()} ${msg}\n`)
  } catch {}
}

export interface BridgeConfig {
  /** Jarvis-runtime base URL, e.g. "http://10.0.0.39" */
  apiBaseUrl: string
  /** User identity (matches X-JarvisX-User claim). */
  userId: string
  /** Optional bearer token (required if runtime has jarvisx_auth_required=true). */
  authToken?: string
  /** Optional logger for diagnostics. */
  log?: (msg: string) => void
}

type ToolHandler = (args: Record<string, unknown>) => Promise<unknown> | unknown

/** Built-in handlers — Phase 1: read-only filesystem access. */
const handlers: Record<string, ToolHandler> = {
  operator_read_file: (args) => {
    const path = String(args.path ?? '')
    if (!path) throw new Error('operator_read_file: path required')
    return readFileSync(path, 'utf8')
  },
}

const RECONNECT_BACKOFF_MS = [1000, 2000, 4000, 8000, 15000, 30000]

export class JarvisXBridge {
  private ws: WebSocket | null = null
  private reconnectAttempt = 0
  private stopped = false
  private heartbeatTimer: NodeJS.Timeout | null = null

  constructor(private cfg: BridgeConfig) {}

  private log(msg: string): void {
    fileLog(msg)
    if (this.cfg.log) this.cfg.log(msg)
    else console.log(`[jarvisx-bridge] ${msg}`)
  }

  start(): void {
    this.stopped = false
    this.connect()
  }

  stop(): void {
    this.stopped = true
    if (this.heartbeatTimer) clearInterval(this.heartbeatTimer)
    if (this.ws) {
      try { this.ws.close(1000, 'client_stop') } catch {}
    }
  }

  private wsUrl(): string {
    // Convert http(s)://host[:port] to ws(s)://host[:port]/api/jarvisx-bridge/ws
    const base = this.cfg.apiBaseUrl.replace(/^http/, 'ws').replace(/\/$/, '')
    return `${base}/api/jarvisx-bridge/ws`
  }

  private connect(): void {
    if (this.stopped) return
    const url = this.wsUrl()
    const headers: Record<string, string> = {}
    if (this.cfg.authToken) headers['Authorization'] = `Bearer ${this.cfg.authToken}`

    this.log(`connecting to ${url}`)
    try {
      this.ws = new WebSocket(url, { headers })
    } catch (e) {
      this.log(`connect failed: ${e}`)
      this.scheduleReconnect()
      return
    }

    this.ws.on('open', () => {
      this.reconnectAttempt = 0
      this.log('ws open — sending register')
      this.send({
        type: 'register',
        user_id: this.cfg.userId,
        client: 'jarvisx-electron',
        version: process.env.npm_package_version || '0.0.0',
        platform: `${process.platform}-${process.arch}`,
        capabilities: Object.keys(handlers),
      })
      // Start heartbeat (every 25s, server expects activity within ~30s)
      this.heartbeatTimer = setInterval(() => this.send({ type: 'ping' }), 25_000)
    })

    this.ws.on('message', (raw) => {
      void this.handleMessage(String(raw))
    })

    this.ws.on('close', (code, reason) => {
      this.log(`ws close code=${code} reason=${reason || '(none)'}`)
      if (this.heartbeatTimer) {
        clearInterval(this.heartbeatTimer)
        this.heartbeatTimer = null
      }
      this.ws = null
      this.scheduleReconnect()
    })

    this.ws.on('error', (err) => {
      this.log(`ws error: ${err.message}`)
      // Let 'close' handle reconnection
    })
  }

  private scheduleReconnect(): void {
    if (this.stopped) return
    const idx = Math.min(this.reconnectAttempt, RECONNECT_BACKOFF_MS.length - 1)
    const wait = RECONNECT_BACKOFF_MS[idx]
    this.reconnectAttempt += 1
    this.log(`reconnect in ${wait}ms (attempt ${this.reconnectAttempt})`)
    setTimeout(() => this.connect(), wait)
  }

  private send(msg: unknown): void {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) return
    try {
      this.ws.send(JSON.stringify(msg))
    } catch (e) {
      this.log(`send failed: ${e}`)
    }
  }

  private async handleMessage(raw: string): Promise<void> {
    let msg: Record<string, unknown>
    try { msg = JSON.parse(raw) } catch { return }
    const mtype = String(msg.type ?? '')

    if (mtype === 'tool_invoke') {
      const correlation_id = String(msg.correlation_id ?? '')
      const tool = String(msg.tool ?? '')
      const args = (msg.args as Record<string, unknown>) || {}
      this.log(`tool_invoke tool=${tool} args=${JSON.stringify(args).slice(0, 120)}`)
      const handler = handlers[tool]
      if (!handler) {
        this.send({
          type: 'tool_result',
          correlation_id,
          status: 'error',
          result: null,
          error: `unknown_tool: ${tool}`,
        })
        this.log(`  → replied unknown_tool`)
        return
      }
      try {
        const result = await handler(args)
        this.send({
          type: 'tool_result',
          correlation_id,
          status: 'ok',
          result,
          error: null,
        })
        const preview = typeof result === 'string' ? result.slice(0, 60) : '(non-string)'
        this.log(`  → replied ok (${preview})`)
      } catch (e) {
        const err = e instanceof Error ? e.message : String(e)
        this.send({
          type: 'tool_result',
          correlation_id,
          status: 'error',
          result: null,
          error: err.slice(0, 240),
        })
        this.log(`  → replied error: ${err.slice(0, 100)}`)
      }
      return
    }

    if (mtype === 'ping') {
      this.send({ type: 'pong' })
      this.log('recv ping → sent pong')
      return
    }
    if (mtype === 'pong') {
      this.log('recv pong')
      return
    }
    if (mtype === 'registered') {
      this.log(`recv registered user_id=${msg.user_id}`)
      return
    }
    this.log(`recv unknown type=${mtype}`)
  }
}
