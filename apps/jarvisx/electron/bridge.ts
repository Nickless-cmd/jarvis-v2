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
import {
  readFileSync,
  writeFileSync,
  mkdirSync,
  readdirSync,
  lstatSync,
  appendFileSync,
} from 'node:fs'
import { homedir } from 'node:os'
import { dirname, join, isAbsolute, resolve } from 'node:path'
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

/** Resolve a path argument — accept absolute or relative-to-home. */
function resolveOperatorPath(p: unknown): string {
  const raw = String(p ?? '').trim()
  if (!raw) throw new Error('path required')
  // Expand leading ~ to home dir (Jarvis often passes ~/foo paths).
  if (raw === '~') return homedir()
  if (raw.startsWith('~/')) return join(homedir(), raw.slice(2))
  if (isAbsolute(raw)) return raw
  return resolve(homedir(), raw)
}

/** Lightweight glob → regex, supports **, *, ?. Handles bash-style patterns. */
function globToRegex(pattern: string): RegExp {
  // Escape regex special chars except for our glob chars.
  let re = ''
  let i = 0
  while (i < pattern.length) {
    const c = pattern[i]
    if (c === '*' && pattern[i + 1] === '*') {
      re += '.*'
      i += 2
      // Skip trailing slash in **/ — treat ** as "any depth"
      if (pattern[i] === '/') i++
    } else if (c === '*') {
      re += '[^/]*'
      i++
    } else if (c === '?') {
      re += '[^/]'
      i++
    } else if ('.+^$()[]{}|\\'.includes(c)) {
      re += '\\' + c
      i++
    } else {
      re += c
      i++
    }
  }
  return new RegExp('^' + re + '$')
}

/** Recursive directory walk, capped at max files to avoid runaway. */
function* walkDir(root: string, max: number): Generator<string> {
  let count = 0
  const stack: string[] = [root]
  while (stack.length && count < max) {
    const dir = stack.pop()!
    let entries: string[]
    try {
      entries = readdirSync(dir)
    } catch {
      continue
    }
    for (const name of entries) {
      if (count >= max) return
      // Skip common heavy dirs by default
      if (name === 'node_modules' || name === '.git' || name === '__pycache__') continue
      const full = join(dir, name)
      let st
      try {
        st = lstatSync(full)
      } catch {
        continue
      }
      if (st.isDirectory()) {
        stack.push(full)
      } else if (st.isFile()) {
        yield full
        count++
      }
    }
  }
}

/** Built-in handlers — Phase 1+2: read/write/edit/glob/grep/list_dir. */
const handlers: Record<string, ToolHandler> = {
  operator_read_file: (args) => {
    const path = resolveOperatorPath(args.path)
    return readFileSync(path, 'utf8')
  },

  operator_write_file: (args) => {
    const path = resolveOperatorPath(args.path)
    const content = String(args.content ?? '')
    // Create parent dirs as needed (mkdir -p style)
    try {
      mkdirSync(dirname(path), { recursive: true })
    } catch {}
    writeFileSync(path, content, 'utf8')
    return { bytes_written: Buffer.byteLength(content, 'utf8'), path }
  },

  operator_edit_file: (args) => {
    const path = resolveOperatorPath(args.path)
    const oldStr = String(args.old_string ?? '')
    const newStr = String(args.new_string ?? '')
    const replaceAll = Boolean(args.replace_all)
    if (!oldStr) throw new Error('old_string is required and must be non-empty')
    const orig = readFileSync(path, 'utf8')
    const occurrences = orig.split(oldStr).length - 1
    if (occurrences === 0) {
      throw new Error(`old_string not found in ${path}`)
    }
    if (occurrences > 1 && !replaceAll) {
      throw new Error(
        `old_string appears ${occurrences} times in ${path}; set replace_all=true to replace all, or provide more context`,
      )
    }
    const updated = replaceAll
      ? orig.split(oldStr).join(newStr)
      : orig.replace(oldStr, newStr)
    writeFileSync(path, updated, 'utf8')
    return { replacements: replaceAll ? occurrences : 1, path }
  },

  operator_glob: (args) => {
    const pattern = String(args.pattern ?? '')
    if (!pattern) throw new Error('pattern is required')
    const cwd = args.cwd ? resolveOperatorPath(args.cwd) : homedir()
    const maxResults = Number(args.max_results) || 200
    const re = globToRegex(pattern)
    const out: string[] = []
    for (const file of walkDir(cwd, maxResults * 20)) {
      // Match against path relative to cwd, with forward slashes.
      const rel = file.startsWith(cwd + '/') ? file.slice(cwd.length + 1) : file
      if (re.test(rel)) {
        out.push(file)
        if (out.length >= maxResults) break
      }
    }
    return out
  },

  operator_grep: (args) => {
    const pattern = String(args.pattern ?? '')
    if (!pattern) throw new Error('pattern is required')
    const searchPath = args.path ? resolveOperatorPath(args.path) : homedir()
    const fileGlob = args.glob ? String(args.glob) : null
    const ci = Boolean(args.case_insensitive)
    const maxResults = Number(args.max_results) || 200
    const flags = ci ? 'i' : ''
    let regex: RegExp
    try {
      regex = new RegExp(pattern, flags)
    } catch (e) {
      throw new Error(`invalid regex pattern: ${e}`)
    }
    const globRe = fileGlob ? globToRegex(fileGlob) : null

    const out: Array<{ file: string; line: number; text: string }> = []
    let st
    try { st = lstatSync(searchPath) } catch { return out }

    const files: Iterable<string> = st.isFile()
      ? [searchPath]
      : walkDir(searchPath, maxResults * 50)

    for (const file of files) {
      if (out.length >= maxResults) break
      if (globRe) {
        const rel = file.startsWith(searchPath + '/') ? file.slice(searchPath.length + 1) : file
        if (!globRe.test(rel)) continue
      }
      let content: string
      try {
        content = readFileSync(file, 'utf8')
      } catch {
        continue
      }
      const lines = content.split('\n')
      for (let i = 0; i < lines.length; i++) {
        if (regex.test(lines[i])) {
          out.push({ file, line: i + 1, text: lines[i].slice(0, 240) })
          if (out.length >= maxResults) break
        }
      }
    }
    return out
  },

  operator_list_dir: (args) => {
    const path = resolveOperatorPath(args.path)
    const entries = readdirSync(path)
    return entries.map((name) => {
      const full = join(path, name)
      let st
      try {
        st = lstatSync(full)
      } catch {
        return { name, type: 'unknown', size: 0 }
      }
      const type = st.isSymbolicLink()
        ? 'symlink'
        : st.isDirectory()
          ? 'dir'
          : st.isFile()
            ? 'file'
            : 'other'
      return { name, type, size: Number(st.size) || 0 }
    })
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
