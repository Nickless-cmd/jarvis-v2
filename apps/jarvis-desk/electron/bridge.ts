// @ts-nocheck — verbatim port af JarvisX bridge.ts (type-checket i jarvisx).
// GUI/browser-værktøjer bruger valgfri dynamiske imports (nut-js/puppeteer);
// de fejler pænt ved kald hvis deps mangler. FS/bash/webfetch er pure node.
//
// ⚠️ GROUND TRUTH (mod gentagen konfabulering, 2026-06-13): DENNE fil ER
// integreret i Electron-appen. main.ts importerer den dynamisk (`await
// import('./bridge.js')`), instantierer `new JarvisXBridge(...)` og kalder
// `.start()` fra `app.whenReady()` → `bootstrapBridge()`; stoppes ved
// `before-quit`. Den kører IN-PROCESS i Electrons main-proces — IKKE en separat
// Node-proces der kan "crashe"/blive "zombie". Den får config FRA appen
// (apiBaseUrl/userId/authToken), ikke en hardcoded ~/.config/jarvisx-fil (kun
// bridge.LOG ligger der, kosmetisk). Broen = OPERATOR-tools (operator_*),
// HELT separat fra chat-streaming (/chat/stream/v2 SSE i streamClient.ts).
// Søg efter `JarvisXBridge` i electron/, IKKE i src/ (renderer), før du
// konkluderer "orphaned".
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
  existsSync,
} from 'node:fs'
import { homedir } from 'node:os'
import { dirname, join, isAbsolute, resolve } from 'node:path'
import { spawnSync } from 'node:child_process'
import { platform as osPlatform } from 'node:os'
import {
  dialog,
  desktopCapturer,
  screen,
  shell as electronShell,
  BrowserWindow,
} from 'electron'

/**
 * Race a native confirmation dialog against an auto-reject timer.
 *
 * BEMÆRK 2026-05-28: Alle 6 operator-tools bruger nu runtime chat-card
 * godkendelse i stedet for OS-dialoger (se refactoring commit). Denne
 * helper er IKKE KALDT i øjeblikket, men beholdes til fremtidige tools
 * der har brug for en nativ dialog uden for runtime-mediation.
 *
 * CRITICAL: must parent the dialog to a BrowserWindow. On Linux (and
 * sometimes on Wayland-only sessions) `dialog.showMessageBox(options)`
 * without a parent creates a modal that *never visually appears* — the
 * Promise never resolves, so the only way out is the timeout. Bjørn
 * caught this 2026-05-28: the dialog seemed to "arrive after 20 sec"
 * because that's when the auto-reject branch won and briefly flashed
 * the dialog as it was being torn down.
 *
 * With a parent (the JarvisX main window), the modal shows immediately
 * and the user can actually click before timeout.
 *
 * Returns:
 *   - true  if the user picked the `accept_button_index`
 *   - false if the user picked any other button OR the timer fired
 */
// Eksporteret så TS ikke klager over "declared but never read" —
// fremtidige callers kan importere den direkte.
export async function approvalRace(
  options: Electron.MessageBoxOptions,
  acceptButtonIndex: number,
  timeoutMs: number = 20_000,
): Promise<boolean> {
  const parent =
    BrowserWindow.getFocusedWindow() ||
    BrowserWindow.getAllWindows().find((w) => !w.isDestroyed()) ||
    null
  // dialog.showMessageBox has two overloads: with and without parent.
  // Call the parented form whenever we have a window — that's the only
  // reliable way to get the modal to actually render.
  const dialogPromise: Promise<{ response: number }> = parent
    ? dialog.showMessageBox(parent, options)
    : dialog.showMessageBox(options)
  const timeoutPromise = new Promise<{ response: number }>((resolve) =>
    setTimeout(() => resolve({ response: -1 }), timeoutMs),
  )
  const choice = await Promise.race([dialogPromise, timeoutPromise])
  return choice.response === acceptButtonIndex
}
import { spawn } from 'node:child_process'
import { randomUUID } from 'node:crypto'
import WebSocket from 'ws'

// Module-level reference to the currently-connected bridge's config so
// handlers (operator_speak, anything else that needs to call back into
// the backend) can read apiBaseUrl + authToken without each handler
// having to figure out where they live. Populated by JarvisXBridge's
// constructor; refreshed on every reconnect.
let _activeBridgeCfg: BridgeConfig | null = null
export function getActiveBridgeCfg(): BridgeConfig | null {
  return _activeBridgeCfg
}

// §17.6.1: operator tools eksekverer KUN lokalt i code mode. chat/cowork må ikke
// køre dem på brugerens maskine. Tom mode = legacy (serveren sender endnu ikke mode)
// → tillad, så bagudkompatibilitet bevares indtil serveren altid sender mode.
const _LOCAL_EXECUTION_MODES = new Set(['code', ''])
export function isLocalExecutionMode(mode: string | null | undefined): boolean {
  return _LOCAL_EXECUTION_MODES.has(String(mode ?? '').toLowerCase())
}

// Den session brugeren aktuelt har fremme i jarvis-desk. Renderer pusher den
// ved hvert session-skift (run:setSession). Bruges så en operator_wakeup kan
// re-engagere i NETOP den session — ikke en frisk/forkert (Bjørn 2026-06-13).
let _activeSessionId: string | null = null
export function setActiveSessionId(sessionId: string | null): void {
  _activeSessionId = (sessionId || '').trim() || null
}

/** Resolve which shell to use for operator_bash based on the OS the
 * JarvisX-app is running on. Linux/macOS use bash; Windows defaults to
 * PowerShell (more capable than cmd.exe, still ubiquitous on Windows 10+). */
function selectShell(): { cmd: string; args: (command: string) => string[] } {
  const p = osPlatform()
  if (p === 'win32') {
    return {
      cmd: 'powershell.exe',
      // -NoProfile keeps startup fast; -Command takes the inline command
      args: (command) => ['-NoProfile', '-NonInteractive', '-Command', command],
    }
  }
  return {
    cmd: 'bash',
    args: (command) => ['-c', command],
  }
}

/** First audio capture device discovered via ffmpeg dshow. Cached for
 * process lifetime so we don't spawn ffmpeg twice per recording. dshow
 * names look like `Mikrofon (NOS X500)` — must match EXACTLY; bare
 * 'default' is not a valid dshow source on Windows. */
let _dshowAudioDevice: string | null | undefined = undefined
function findDshowAudioDevice(): string | null {
  if (_dshowAudioDevice !== undefined) return _dshowAudioDevice
  if (osPlatform() !== 'win32') {
    _dshowAudioDevice = null
    return null
  }
  try {
    const probe = spawnSync(
      'ffmpeg',
      ['-hide_banner', '-list_devices', 'true', '-f', 'dshow', '-i', 'dummy'],
      { encoding: 'utf8', timeout: 5000 },
    )
    // ffmpeg writes device listings to stderr by convention.
    const blob = (probe.stderr || '') + (probe.stdout || '')
    // Lines: [dshow @ ...]  "Device Name"  (audio)
    const m = [...blob.matchAll(/"([^"]+)"\s*\(audio\)/g)]
    _dshowAudioDevice = m.length > 0 ? m[0][1] : null
    return _dshowAudioDevice
  } catch {
    _dshowAudioDevice = null
    return null
  }
}

/** Resolve ImageMagick binary path. On Windows the bare `convert` name
 * collides with a built-in disk-conversion utility; we prefer the unified
 * `magick.exe` from ImageMagick 7+ and probe well-known install paths
 * because winget often doesn't refresh PATH for already-running processes. */
let _imCache: string | null = null
function findImageMagick(): string {
  if (_imCache) return _imCache
  if (osPlatform() !== 'win32') {
    _imCache = 'magick'
    return _imCache
  }
  const roots = ['C:\\Program Files', 'C:\\Program Files (x86)']
  for (const root of roots) {
    try {
      for (const e of readdirSync(root)) {
        if (e.startsWith('ImageMagick-')) {
          const candidate = join(root, e, 'magick.exe')
          if (existsSync(candidate)) {
            _imCache = candidate
            return _imCache
          }
        }
      }
    } catch {}
  }
  _imCache = 'magick.exe'  // last-ditch bare-name lookup via PATH
  return _imCache
}

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
  /** UUID4 der binder denne installation til owner-sessionen (TOTP Fase 2). */
  appId?: string
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

// ── Async spawn helper — does NOT block the event loop ──────────────
// Critical for WebSocket health: asyncSpawn does not block Node's event loop,
// so ping/pong fails and the server closes the connection mid-command.
interface AsyncSpawnResult {
  stdout: string
  stderr: string
  status: number | null
  signal: string | null
  timed_out: boolean
  error?: string
}
async function asyncSpawn(
  cmd: string,
  args: string[],
  opts: { cwd?: string; timeout?: number; maxBuffer?: number } = {},
): Promise<AsyncSpawnResult> {
  return new Promise((resolve) => {
    const child = spawn(cmd, args, {
      cwd: opts.cwd,
      stdio: ['pipe', 'pipe', 'pipe'],
      shell: false,
    })
    const stdoutBuf: Buffer[] = []
    const stderrBuf: Buffer[] = []
    child.stdout?.on('data', (d: Buffer) => stdoutBuf.push(d))
    child.stderr?.on('data', (d: Buffer) => stderrBuf.push(d))

    let timedOut = false
    let timer: ReturnType<typeof setTimeout> | undefined
    if (opts.timeout && opts.timeout > 0) {
      timer = setTimeout(() => {
        timedOut = true
        child.kill('SIGTERM')
      }, opts.timeout)
    }

    child.on('close', (code, sig) => {
      if (timer) clearTimeout(timer)
      const maxBuf = opts.maxBuffer ?? 5 * 1024 * 1024
      let stdout = Buffer.concat(stdoutBuf).toString('utf8')
      let stderr = Buffer.concat(stderrBuf).toString('utf8')
      if (stdout.length > maxBuf) stdout = stdout.slice(0, maxBuf)
      if (stderr.length > maxBuf) stderr = stderr.slice(0, maxBuf)
      resolve({ stdout, stderr, status: code, signal: sig, timed_out: timedOut })
    })
    child.on('error', (err) => {
      if (timer) clearTimeout(timer)
      resolve({ stdout: '', stderr: '', status: null, signal: null, timed_out: false, error: err.message })
    })
  })
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
    // Snapshot pre-write so the LLM knows whether this was a fresh
    // creation or an overwrite (and by how much). Phase 2.
    let bytes_before: number | null = null
    let was_new_file = true
    try {
      const existing = readFileSync(path, 'utf8')
      bytes_before = Buffer.byteLength(existing, 'utf8')
      was_new_file = false
    } catch { /* file didn't exist — fresh creation */ }
    try {
      mkdirSync(dirname(path), { recursive: true })
    } catch {}
    writeFileSync(path, content, 'utf8')
    const bytes_after = Buffer.byteLength(content, 'utf8')
    return {
      bytes_written: bytes_after,
      bytes_before,
      bytes_after,
      was_new_file,
      delta_bytes: bytes_before == null ? bytes_after : bytes_after - bytes_before,
      path,
    }
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
    // Auto-diff: surface a compact unified diff of the changed region so
    // the LLM SEES what landed without having to re-read. Phase 2 of the
    // code-discipline work — "enforce, don't remind".
    const oldLines = oldStr.split('\n')
    const newLines = newStr.split('\n')
    const maxPreviewLines = 30
    const truncLine = (s: string) => (s.length > 200 ? s.slice(0, 200) + ' …[truncated]' : s)
    const diff_preview = [
      `--- ${path} (before)`,
      `+++ ${path} (after)`,
      ...oldLines.slice(0, maxPreviewLines).map((l) => '-' + truncLine(l)),
      ...(oldLines.length > maxPreviewLines ? [`-… (${oldLines.length - maxPreviewLines} more removed lines)`] : []),
      ...newLines.slice(0, maxPreviewLines).map((l) => '+' + truncLine(l)),
      ...(newLines.length > maxPreviewLines ? [`+… (${newLines.length - maxPreviewLines} more added lines)`] : []),
    ].join('\n')
    return {
      replacements: replaceAll ? occurrences : 1,
      path,
      diff_preview,
      bytes_before: Buffer.byteLength(orig, 'utf8'),
      bytes_after: Buffer.byteLength(updated, 'utf8'),
    }
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

  operator_webfetch: async (args) => {
    const url = String(args.url ?? '').trim()
    if (!url) throw new Error('url is required')
    const method = String(args.method ?? 'GET').toUpperCase()
    const headers = (args.headers as Record<string, string>) || {}
    const body = args.body !== null && args.body !== undefined ? String(args.body) : undefined
    const timeoutMs = Math.min(Math.max(Number(args.timeout_s) || 30, 1), 120) * 1000

    const controller = new AbortController()
    const timer = setTimeout(() => controller.abort(), timeoutMs)
    try {
      const resp = await fetch(url, {
        method,
        headers,
        body: ['GET', 'HEAD'].includes(method) ? undefined : body,
        signal: controller.signal,
      })
      const contentType = resp.headers.get('content-type') || ''
      const isText = /^(text\/|application\/(json|xml|javascript|x-www-form-urlencoded))/i.test(contentType)
      let resBody: string
      if (isText) {
        const text = await resp.text()
        resBody = text.slice(0, 100_000)
      } else {
        const buf = await resp.arrayBuffer()
        // Cap binary at 64KB then base64-encode
        const slice = buf.byteLength > 64 * 1024 ? buf.slice(0, 64 * 1024) : buf
        resBody = Buffer.from(slice).toString('base64')
      }
      const headersObj: Record<string, string> = {}
      resp.headers.forEach((v, k) => { headersObj[k] = v })
      return {
        status: resp.status,
        headers: headersObj,
        body: resBody,
        content_type: contentType,
        is_base64: !isText,
      }
    } finally {
      clearTimeout(timer)
    }
  },

  operator_bash: async (args) => {
    const command = String(args.command ?? '').trim()
    if (!command) throw new Error('command is required')
    const cwd = args.cwd ? resolveOperatorPath(args.cwd) : homedir()
    const timeoutS = Math.min(Math.max(Number(args.timeout_s) || 30, 1), 300)

    // Platform-aware shell selection: bash on Linux/macOS, PowerShell
    // on Windows. Same surface for the LLM — shell-features (pipes,
    // redirects, env-vars) work in both.
    const shell = selectShell()
    const result = await asyncSpawn(shell.cmd, shell.args(command), {
      cwd,
      timeout: timeoutS * 1000,
      maxBuffer: 5 * 1024 * 1024, // 5 MB stdout cap
    })

    return {
      platform: osPlatform(),
      shell: shell.cmd,
      stdout: (result.stdout ?? '').slice(0, 100_000),
      stderr: (result.stderr ?? '').slice(0, 50_000),
      exit_code: result.status,
      timed_out: result.timed_out,
    }
  },

  operator_screenshot: async (args) => {
    // Capture the operator's screen and return PNG bytes (base64) plus
    // metadata. Backend tool wrapper writes the bytes to a temp file on
    // Jarvis-side so the LLM can hand it to analyze_image.
    //
    // Args:
    //   display_id?: number  — specific display to capture; default = primary
    //   save_path?: string   — also save to this path on the operator's
    //                          machine (handy for debugging / history)
    //   format?: 'png'|'jpeg' — default png
    //   jpeg_quality?: number — 1-100, only used for jpeg, default 85
    const fmt = String(args.format ?? 'png').toLowerCase()
    if (fmt !== 'png' && fmt !== 'jpeg') {
      throw new Error("format must be 'png' or 'jpeg'")
    }
    const jpegQuality = Math.min(Math.max(Number(args.jpeg_quality ?? 85), 1), 100)

    const displays = screen.getAllDisplays()
    const targetDisplay = args.display_id != null
      ? displays.find((d) => d.id === Number(args.display_id)) ?? screen.getPrimaryDisplay()
      : screen.getPrimaryDisplay()

    // Request thumbnails at the display's native pixel resolution.
    const px = {
      width: Math.round(targetDisplay.size.width * targetDisplay.scaleFactor),
      height: Math.round(targetDisplay.size.height * targetDisplay.scaleFactor),
    }

    const sources = await desktopCapturer.getSources({
      types: ['screen'],
      thumbnailSize: px,
    })
    if (sources.length === 0) throw new Error('no screen sources available')

    // Match source to requested display when possible; desktopCapturer's
    // display_id is a string of the Electron display id.
    let source = sources[0]
    const matched = sources.find((s) => s.display_id === String(targetDisplay.id))
    if (matched) source = matched

    const img = source.thumbnail
    const sz = img.getSize()
    const buf = fmt === 'jpeg' ? img.toJPEG(jpegQuality) : img.toPNG()

    let savedPath: string | null = null
    if (args.save_path) {
      const p = resolveOperatorPath(args.save_path)
      mkdirSync(dirname(p), { recursive: true })
      writeFileSync(p, buf)
      savedPath = p
    }

    return {
      data_base64: buf.toString('base64'),
      mime_type: `image/${fmt}`,
      width: sz.width,
      height: sz.height,
      display_id: targetDisplay.id,
      display_label: source.name,
      bytes: buf.length,
      operator_path: savedPath,
    }
  },

  operator_open_url: async (args) => {
    // Godkendelse håndteres nu af runtime via chat-card FØR denne handler
    // kaldes. Når vi når hertil, har brugeren allerede godkendt i chatten.
    const url = String(args.url ?? '').trim()
    if (!url) throw new Error('url is required')
    // Restrict to common navigable schemes to prevent abuse via file://
    // or javascript: URIs being shelled out.
    let parsed: URL
    try {
      parsed = new URL(url)
    } catch {
      throw new Error(`invalid url: ${url}`)
    }
    const allowed = ['http:', 'https:', 'mailto:']
    if (!allowed.includes(parsed.protocol)) {
      throw new Error(`scheme not allowed: ${parsed.protocol}`)
    }

    // electronShell.openExternal is the OS-native "open" — defers to
    // the default handler (browser for http/https, mail client for mailto).
    await electronShell.openExternal(url)
    return { opened: true, url }
  },

  operator_launch_app: async (args) => {
    // Godkendelse håndteres nu af runtime via chat-card FØR denne handler
    // kaldes. Når vi når hertil, har brugeren allerede godkendt i chatten.
    // Launch an installed application. Accepts either a full path or a
    // name resolvable on PATH (e.g. 'notepad', 'code', 'chrome').
    // For UWP apps, pass the AppId like 'shell:appsFolder\\<AppId>' as `path`.
    const target = String(args.path ?? args.app ?? '').trim()
    if (!target) throw new Error('path (or app) is required')

    const cliArgs: string[] = Array.isArray(args.args)
      ? args.args.map((a) => String(a))
      : []
    const cwd = args.cwd ? resolveOperatorPath(args.cwd) : homedir()

    // Spawn detached so the new process doesn't tie to JarvisX' lifetime.
    // shell:true lets PATH resolution (e.g. 'notepad') and shell:appsFolder
    // URIs work the same way Start-Process would resolve them.
    try {
      const child = spawn(target, cliArgs, {
        cwd,
        detached: true,
        stdio: 'ignore',
        shell: true,
      })
      child.unref()
      return {
        started: true,
        path: target,
        pid: child.pid ?? null,
      }
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e)
      return { started: false, path: target, error: msg }
    }
  },

  // ── GUI control via nut.js ───────────────────────────────────────────
  // The nut.js module is imported lazily so the bridge still loads even
  // if native build fails on a given install. Each handler imports the
  // pieces it actually needs.

  operator_mouse_move: async (args) => {
    const x = Number(args.x)
    const y = Number(args.y)
    if (!Number.isFinite(x) || !Number.isFinite(y)) {
      throw new Error('x and y are required numeric coordinates')
    }
    const { mouse, Point, straightTo } = await import('@nut-tree-fork/nut-js')
    // Smooth=false → instantaneous teleport. Smooth path takes longer but
    // looks human; useful when an app cares about mouseover events.
    if (args.smooth) {
      await mouse.move(straightTo(new Point(x, y)))
    } else {
      await mouse.setPosition(new Point(x, y))
    }
    return { moved: true, x, y, smooth: Boolean(args.smooth) }
  },

  operator_mouse_click: async (args) => {
    const { mouse, Point, Button } = await import('@nut-tree-fork/nut-js')
    // Optional pre-move; useful so the LLM doesn't have to chain two calls.
    if (args.x != null && args.y != null) {
      const x = Number(args.x), y = Number(args.y)
      if (Number.isFinite(x) && Number.isFinite(y)) {
        await mouse.setPosition(new Point(x, y))
      }
    }
    const btnName = String(args.button ?? 'left').toLowerCase()
    const btn =
      btnName === 'right' ? Button.RIGHT :
      btnName === 'middle' ? Button.MIDDLE :
      Button.LEFT
    if (args.double) {
      await mouse.doubleClick(btn)
    } else {
      await mouse.click(btn)
    }
    return { clicked: true, button: btnName, double: Boolean(args.double) }
  },

  operator_mouse_position: async () => {
    const { mouse } = await import('@nut-tree-fork/nut-js')
    const p = await mouse.getPosition()
    return { x: p.x, y: p.y }
  },

  operator_keyboard_type: async (args) => {
    const text = String(args.text ?? '')
    if (!text) throw new Error('text is required')
    const { keyboard } = await import('@nut-tree-fork/nut-js')
    // nut.js Keyboard.type accepts variadic args; each string is typed.
    // Tune delay between keystrokes via setKeyboardDelay if needed.
    if (args.delay_ms != null) {
      keyboard.config.autoDelayMs = Math.max(0, Number(args.delay_ms))
    }
    await keyboard.type(text)
    return { typed: true, length: text.length }
  },

  operator_keyboard_press: async (args) => {
    // Accept either a single key string ("Enter") or array of modifiers
    // + key for hotkeys (["Control", "C"]).
    const keysArg = args.keys
    if (!keysArg) throw new Error('keys is required (string or string[])')
    const keys: string[] = Array.isArray(keysArg)
      ? keysArg.map(String)
      : [String(keysArg)]

    const nut = await import('@nut-tree-fork/nut-js')
    const { Key, keyboard } = nut
    // Map human names to nut.js Key enum.
    const resolveKey = (name: string): unknown => {
      const norm = name.trim().replace(/\s+/g, '')
      // Try exact match first, then case-insensitive
      const direct = (Key as unknown as Record<string, unknown>)[norm]
      if (direct !== undefined) return direct
      const lower = norm.toLowerCase()
      for (const k of Object.keys(Key)) {
        if (k.toLowerCase() === lower) {
          return (Key as unknown as Record<string, unknown>)[k]
        }
      }
      throw new Error(`unknown key: ${name}`)
    }
    const resolved = keys.map(resolveKey)
    await keyboard.pressKey(...(resolved as never[]))
    await keyboard.releaseKey(...(resolved as never[]))
    return { pressed: true, keys }
  },

  operator_screen_size: async () => {
    const { screen: nutScreen } = await import('@nut-tree-fork/nut-js')
    const width = await nutScreen.width()
    const height = await nutScreen.height()
    return { width, height }
  },

  // ── Browser automation via puppeteer-core ─────────────────────────────
  // One persistent browser session per JarvisX run, lazily created on
  // first browser tool call. Auto-closes after BROWSER_IDLE_MS of
  // inactivity. Browser binary is auto-detected (Chrome → Edge).

  operator_browser_open: async (args) => {
    const url = String(args.url ?? '').trim()
    if (!url) throw new Error('url is required')
    const waitUntil = String(args.wait_until ?? 'load') as
      | 'load' | 'domcontentloaded' | 'networkidle0' | 'networkidle2'
    const sess = await ensureBrowserSession()
    const resp = await sess.page.goto(url, {
      waitUntil,
      timeout: Number(args.timeout_ms ?? 30000),
    })
    const title = await sess.page.title()
    return {
      url: sess.page.url(),
      title,
      status: resp?.status() ?? null,
      ok: resp?.ok() ?? false,
    }
  },

  operator_browser_get_text: async (args) => {
    const sess = await ensureBrowserSession()
    const selector = args.selector ? String(args.selector) : null
    const maxChars = Math.max(100, Number(args.max_chars ?? 50000))
    let text: string
    if (selector) {
      text = await sess.page.$eval(selector, (el: Element) => el.textContent ?? '')
    } else {
      text = await sess.page.evaluate(() => document.body?.innerText ?? '')
    }
    const truncated = text.length > maxChars
    return {
      text: truncated ? text.slice(0, maxChars) + '…' : text,
      length: text.length,
      truncated,
      selector,
    }
  },

  operator_browser_get_links: async () => {
    const sess = await ensureBrowserSession()
    const links: { href: string; text: string }[] = await sess.page.evaluate(() => {
      const out: { href: string; text: string }[] = []
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      ;(globalThis as any).document.querySelectorAll('a[href]').forEach((a: Element) => {
        const href = (a as HTMLAnchorElement).href
        const text = ((a as HTMLAnchorElement).textContent ?? '').trim().slice(0, 200)
        if (href) out.push({ href, text })
      })
      return out
    })
    return { count: links.length, links: links.slice(0, 500) }
  },

  operator_browser_click: async (args) => {
    const selector = String(args.selector ?? '').trim()
    if (!selector) throw new Error('selector is required')
    const sess = await ensureBrowserSession()
    if (args.wait_for_selector !== false) {
      await sess.page.waitForSelector(selector, {
        timeout: Number(args.timeout_ms ?? 5000),
      })
    }
    if (args.wait_navigation) {
      const [resp] = await Promise.all([
        sess.page.waitForNavigation({ timeout: 15000 }).catch(() => null),
        sess.page.click(selector),
      ])
      return {
        clicked: true,
        selector,
        navigated: !!resp,
        url: sess.page.url(),
      }
    }
    await sess.page.click(selector)
    return { clicked: true, selector, navigated: false, url: sess.page.url() }
  },

  operator_browser_type: async (args) => {
    const selector = String(args.selector ?? '').trim()
    const text = String(args.text ?? '')
    if (!selector) throw new Error('selector is required')
    const sess = await ensureBrowserSession()
    await sess.page.waitForSelector(selector, { timeout: 5000 })
    if (args.clear_first) {
      // Triple-click to select all, then type to replace.
      await sess.page.click(selector, { clickCount: 3 })
    } else {
      await sess.page.focus(selector)
    }
    await sess.page.type(selector, text, {
      delay: Number(args.delay_ms ?? 0),
    })
    return { typed: true, selector, length: text.length }
  },

  operator_browser_screenshot: async (args) => {
    const sess = await ensureBrowserSession()
    const fullPage = Boolean(args.full_page)
    const fmt = String(args.format ?? 'png').toLowerCase() as 'png' | 'jpeg'
    if (fmt !== 'png' && fmt !== 'jpeg') {
      throw new Error("format must be 'png' or 'jpeg'")
    }
    const buf = (await sess.page.screenshot({
      fullPage,
      type: fmt,
      quality: fmt === 'jpeg' ? Math.min(Math.max(Number(args.jpeg_quality ?? 85), 1), 100) : undefined,
    })) as Buffer
    const viewport = sess.page.viewport()
    return {
      data_base64: buf.toString('base64'),
      mime_type: `image/${fmt}`,
      width: viewport?.width ?? null,
      height: viewport?.height ?? null,
      full_page: fullPage,
      url: sess.page.url(),
      bytes: buf.length,
    }
  },

  operator_browser_evaluate: async (args) => {
    // Godkendelse håndteres nu af runtime via chat-card FØR denne handler
    // kaldes. Når vi når hertil, har brugeren allerede godkendt i chatten.
    // Run arbitrary JS in the page context. Returns whatever the script
    // returns (must be JSON-serializable).
    const script = String(args.script ?? '')
    if (!script) throw new Error('script is required')

    const sess = await ensureBrowserSession()
    // Wrap script in a function so we can return arbitrary expressions.
    // The model can use either `return X;` syntax or just an expression.
    const wrapped = `(async () => { ${script} })()`
    const result = await sess.page.evaluate(wrapped)
    return { executed: true, result }
  },

  operator_browser_status: async () => {
    if (!browserSession) {
      return { open: false }
    }
    const title = await browserSession.page.title()
    const vp = browserSession.page.viewport()
    return {
      open: true,
      url: browserSession.page.url(),
      title,
      viewport: vp,
      idle_for_ms: Date.now() - browserSession.lastUsed,
    }
  },

  operator_browser_close: async () => {
    if (!browserSession) return { closed: false, reason: 'no_session' }
    try {
      await browserSession.browser.close()
    } catch {}
    browserSession = null
    return { closed: true }
  },

  // ── Tier-1 wishlist tools ────────────────────────────────────────────

  operator_clipboard_read: async () => {
    // Electron's built-in clipboard module — cross-platform, no native deps.
    const { clipboard } = await import('electron')
    const text = clipboard.readText()
    return { text }
  },

  operator_clipboard_write: async (args) => {
    const text = String(args.text ?? '')
    const { clipboard } = await import('electron')
    clipboard.writeText(text)
    return { written: true, length: text.length }
  },

  operator_list_windows: async () => {
    // OS-specific window enumeration. nut.js' Window API was unreliable
    // across Linux/Windows in the installed version, so we use platform
    // commands directly — they're well-supported and fast.
    //   Linux: wmctrl -l (requires wmctrl installed)
    //   Windows: PowerShell Get-Process | MainWindowTitle filter
    const platform = osPlatform()
    if (platform === 'win32') {
      const res = await asyncSpawn('powershell.exe', [
        '-NoProfile', '-NonInteractive', '-Command',
        'Get-Process | Where-Object {$_.MainWindowTitle -ne ""} | Select-Object Id,MainWindowTitle | ConvertTo-Json -Compress',
      ], { timeout: 10000 })
      if (res.error) throw new Error(res.error)
      let procs: { Id: number; MainWindowTitle: string }[] = []
      try {
        const parsed = JSON.parse(res.stdout.trim() || '[]')
        procs = Array.isArray(parsed) ? parsed : [parsed]
      } catch {}
      const out = procs.map((p) => ({ title: p.MainWindowTitle, id: p.Id }))
      return { count: out.length, windows: out }
    } else if (platform === 'darwin') {
      // macOS: osascript + System Events to enumerate visible window titles.
      // Returns lines like "Safari||Jarvis — bridge.ts"  (appName || windowTitle).
      const script = `
        tell application "System Events"
          set vis to every process whose visible is true
          set output to ""
          repeat with p in vis
            set pname to name of p
            try
              set wins to title of every window of p
              repeat with w in wins
                if w is not "" then
                  set output to output & pname & "||" & w & linefeed
                end if
              end repeat
            end try
          end repeat
          return output
        end tell`
      const res = await asyncSpawn('osascript', ['-e', script], { timeout: 10000 })
      if (res.error) throw new Error(res.error)
      const out: { title: string; app: string }[] = []
      for (const line of res.stdout.split('\n').filter(Boolean)) {
        const sep = line.indexOf('||')
        if (sep > 0) {
          out.push({ app: line.slice(0, sep), title: line.slice(sep + 2) })
        }
      }
      return { count: out.length, windows: out }
    } else {
      // Linux: wmctrl -l  →  "0x00400003  0 hostname  Window Title"
      const res = await asyncSpawn('wmctrl', ['-l'], { timeout: 10000 })
      if (res.error) {
        throw new Error(
          `wmctrl failed: ${res.error}. ` +
            `Install wmctrl (apt install wmctrl) on the operator's Linux desktop.`,
        )
      }
      const out: { title: string; id: string }[] = []
      for (const line of res.stdout.split('\n')) {
        const m = line.match(/^(0x[0-9a-f]+)\s+\d+\s+\S+\s+(.+)$/)
        if (m) out.push({ title: m[2].trim(), id: m[1] })
      }
      return { count: out.length, windows: out }
    }
  },

  operator_focus_window: async (args) => {
    // Accept handle as either a number (Windows process Id) or a string
    // (Linux X11 hex like "0x00400003"). On Linux, wmctrl wants the hex
    // form; on Windows we pass the title to WScript.Shell.AppActivate.
    const titleSub = args.title_substring != null ? String(args.title_substring) : null
    const handleRaw = args.handle != null ? String(args.handle) : null
    if (titleSub === null && handleRaw === null) {
      throw new Error('title_substring or handle is required')
    }
    const platform = osPlatform()
    if (platform === 'win32') {
      // AppActivate matches by title substring. If only a numeric handle
      // was provided, we can't use it directly (PID != HWND) — best we can
      // do is use the title.
      const target = titleSub ?? handleRaw ?? ''
      const res = await asyncSpawn('powershell.exe', [
        '-NoProfile', '-NonInteractive', '-Command',
        `(New-Object -ComObject WScript.Shell).AppActivate("${target.replace(/"/g, '\\"')}")`,
      ], { timeout: 10000 })
      if (res.error) throw new Error(res.error)
      return { focused: true, title: target, handle: handleRaw }
    } else if (platform === 'darwin') {
      // macOS: use `open -a` to activate the app by bundle/process name,
      // or osascript for more granular window targeting.
      const appName = titleSub ?? handleRaw ?? ''
      if (!appName) throw new Error('title_substring or handle is required on macOS')
      const res = await asyncSpawn('open', ['-a', appName], { timeout: 10000 })
      return { focused: res.status === 0, title: appName, handle: handleRaw }
    } else {
      // Linux: wmctrl -a "title substring"  OR  wmctrl -ia <hex_id>
      if (titleSub !== null) {
        const res = await asyncSpawn('wmctrl', ['-a', titleSub], { timeout: 10000 })
        if (res.error) {
          throw new Error(
            `wmctrl failed: ${res.error}. ` +
              `Install wmctrl (apt install wmctrl) on the operator's Linux desktop.`,
          )
        }
        return { focused: res.status === 0, title: titleSub, handle: null }
      } else {
        const res = await asyncSpawn('wmctrl', ['-ia', String(handleRaw)], { timeout: 10000 })
        if (res.error) throw new Error(`wmctrl failed: ${res.error}`)
        return { focused: res.status === 0, title: '', handle: handleRaw }
      }
    }
  },

  operator_mouse_scroll: async (args) => {
    const direction = String(args.direction ?? 'down')
    const amount = Math.max(1, Number(args.amount ?? 3))
    if (!['up', 'down', 'left', 'right'].includes(direction)) {
      throw new Error(`direction must be one of: up, down, left, right — got: ${direction}`)
    }
    const { mouse } = await import('@nut-tree-fork/nut-js')
    if (direction === 'up') {
      await mouse.scrollUp(amount)
    } else if (direction === 'down') {
      await mouse.scrollDown(amount)
    } else if (direction === 'left') {
      await mouse.scrollLeft(amount)
    } else {
      await mouse.scrollRight(amount)
    }
    return { scrolled: true, direction, amount }
  },

  operator_mouse_drag: async (args) => {
    const fromX = Number(args.from_x)
    const fromY = Number(args.from_y)
    const toX = Number(args.to_x)
    const toY = Number(args.to_y)
    for (const [name, val] of [['from_x', fromX], ['from_y', fromY], ['to_x', toX], ['to_y', toY]]) {
      if (!Number.isFinite(val as number)) throw new Error(`${name} must be a finite number`)
    }
    const btnName = String(args.button ?? 'left').toLowerCase()
    const { mouse, Point, Button } = await import('@nut-tree-fork/nut-js')
    const btn = btnName === 'right' ? Button.RIGHT : Button.LEFT
    // Move to start → press → move to end → release.
    await mouse.setPosition(new Point(fromX, fromY))
    await mouse.pressButton(btn)
    await mouse.setPosition(new Point(toX, toY))
    await mouse.releaseButton(btn)
    return { dragged: true, from_x: fromX, from_y: fromY, to_x: toX, to_y: toY, button: btnName }
  },

  operator_list_processes: async (args) => {
    const filterStr = args.filter != null ? String(args.filter).toLowerCase() : null
    const platform = osPlatform()
    let procs: { pid: number; name: string; cpu: number; memMB: number }[] = []
    if (platform === 'win32') {
      // PowerShell: sorted by CPU descending, top 60.
      const res = await asyncSpawn('powershell.exe', [
        '-NoProfile', '-NonInteractive', '-Command',
        'Get-Process | Select-Object Id,ProcessName,CPU,WorkingSet | Sort-Object CPU -Descending | Select-Object -First 60 | ConvertTo-Json -Compress',
      ], { timeout: 15000 })
      if (res.error) throw new Error(res.error)
      let raw: { Id: number; ProcessName: string; CPU: number | null; WorkingSet: number }[] = []
      try {
        const parsed = JSON.parse(res.stdout.trim())
        raw = Array.isArray(parsed) ? parsed : [parsed]
      } catch {}
      procs = raw.map((p) => ({
        pid: p.Id,
        name: p.ProcessName,
        cpu: Number(p.CPU ?? 0),
        memMB: Math.round(Number(p.WorkingSet ?? 0) / 1024 / 1024),
      }))
    } else {
      // Linux: ps -eo pid,comm,pcpu,rss (rss is in KiB), sort by cpu.
      const res = await asyncSpawn('ps', ['-eo', 'pid,comm,pcpu,rss', '--sort=-pcpu', '--no-headers'], {
        timeout: 10000,
      })
      if (res.error) throw new Error(res.error)
      let count = 0
      for (const line of res.stdout.split('\n')) {
        if (count >= 60) break
        const parts = line.trim().split(/\s+/)
        if (parts.length < 4) continue
        procs.push({
          pid: parseInt(parts[0], 10),
          name: parts[1],
          cpu: parseFloat(parts[2]),
          memMB: Math.round(parseInt(parts[3], 10) / 1024),
        })
        count++
      }
    }
    if (filterStr) {
      procs = procs.filter((p) => p.name.toLowerCase().includes(filterStr))
    }
    return { count: procs.length, processes: procs }
  },

  operator_kill_process: async (args) => {
    // Godkendelse håndteres nu af runtime via chat-card FØR denne handler
    // kaldes. Når vi når hertil, har brugeren allerede godkendt i chatten.
    const pid = Number(args.pid)
    if (!Number.isInteger(pid) || pid <= 0) throw new Error('pid must be a positive integer')

    // Find process name for informative result.
    let procName = `PID ${pid}`
    const platform = osPlatform()
    try {
      if (platform === 'win32') {
        const r = await asyncSpawn('powershell.exe', [
          '-NoProfile', '-NonInteractive', '-Command',
          `Get-Process -Id ${pid} | Select-Object -ExpandProperty ProcessName`,
        ], { timeout: 5000 })
        const name = r.stdout.trim()
        if (name) procName = `${name} (PID ${pid})`
      } else {
        const r = await asyncSpawn('ps', ['-p', String(pid), '-o', 'comm='], { timeout: 5000 })
        const name = r.stdout.trim()
        if (name) procName = `${name} (PID ${pid})`
      }
    } catch {}

    // Send SIGTERM (Linux) / Stop-Process (Windows).
    if (platform === 'win32') {
      const res = await asyncSpawn('powershell.exe', [
        '-NoProfile', '-NonInteractive', '-Command',
        `Stop-Process -Id ${pid} -Force`,
      ], { timeout: 10000 })
      if (res.error) throw new Error(res.error)
      return { killed: true, pid, name: procName }
    } else {
      const res = await asyncSpawn('kill', [String(pid)], { timeout: 5000 })
      if (res.error) throw new Error(res.error)
      if (res.status !== 0) {
        return { killed: false, pid, name: procName, error: res.stderr.trim() }
      }
      return { killed: true, pid, name: procName }
    }
  },

  // ── Tier-2 wishlist tools ────────────────────────────────────────────

  operator_speak: async (args) => {
    // Primary path: backend /api/tts/synthesize (edge-tts, Danish neural).
    // Falls back to legacy SAPI/espeak below if the backend call fails
    // (offline, endpoint missing on an old deployment, etc.) so the tool
    // never goes completely silent.
    const cfg = _activeBridgeCfg
    if (cfg && cfg.apiBaseUrl) {
      try {
        const ttsText = String(args.text ?? '')
        if (!ttsText) throw new Error('text is required')
        const ttsVoice = args.voice != null ? String(args.voice) : 'da-DK-JeppeNeural'
        const ttsRate = args.rate != null && typeof args.rate === 'string' ? args.rate : '+0%'
        const ttsPitch = args.pitch != null && typeof args.pitch === 'string' ? args.pitch : '+0Hz'

        const headers: Record<string, string> = { 'Content-Type': 'application/json' }
        if (cfg.authToken) headers['Authorization'] = `Bearer ${cfg.authToken}`

        const url = cfg.apiBaseUrl.replace(/\/$/, '') + '/api/tts/synthesize'
        const res = await fetch(url, {
          method: 'POST',
          headers,
          body: JSON.stringify({ text: ttsText, voice: ttsVoice, rate: ttsRate, pitch: ttsPitch }),
        })
        if (!res.ok) {
          const errText = await res.text().catch(() => '')
          throw new Error(`tts http ${res.status}: ${errText.slice(0, 200)}`)
        }
        const mp3Bytes = Buffer.from(await res.arrayBuffer())

        const { tmpdir: ttsTmpdir } = await import('node:os')
        const { join: ttsJoin } = await import('node:path')
        const tmpFile = ttsJoin(ttsTmpdir(), `jarvisx-tts-${Date.now()}.mp3`)
        writeFileSync(tmpFile, mp3Bytes)

        // ffplay -nodisp -autoexit -loglevel quiet: silent, blocks until
        // playback ends. asyncSpawn ensures the bridge reply only fires
        // once speech actually finished (matches the "spoken" semantics).
        //
        // Anti-stutter flags:
        //   -infbuf           = unlimited input buffer (whole file in RAM
        //                       before playback starts).
        //   -probesize 1M     = scan more of the file up front so the
        //                       decoder commits to a stable bitrate plan.
        //   -af aresample=async=1000
        //                     = soft-resample timestamps within ±1s, which
        //                       smooths the small frame-boundary gaps
        //                       between edge-tts chunks ("hakkende" pauses).
        const play = await asyncSpawn(
          'ffplay',
          [
            '-nodisp',
            '-autoexit',
            '-loglevel', 'quiet',
            '-infbuf',
            '-probesize', '1M',
            '-af', 'aresample=async=1000',
            tmpFile,
          ],
          { timeout: 60_000 },
        )
        try {
          const { unlinkSync } = await import('node:fs')
          unlinkSync(tmpFile)
        } catch {}

        if (play.error) {
          throw new Error(
            `ffplay not found. Install: winget install Gyan.FFmpeg (Windows) ` +
              `or apt install ffmpeg (Linux). Underlying: ${play.error}`,
          )
        }
        if (play.status !== 0) {
          throw new Error(
            `ffplay exit ${play.status}: ${(play.stderr || '').trim().slice(0, 200)}`,
          )
        }
        return {
          spoken: true,
          length: ttsText.length,
          voice: ttsVoice,
          source: 'edge-tts',
          bytes: mp3Bytes.length,
        }
      } catch (e) {
        fileLog(
          `operator_speak: backend tts failed, falling back to local: ${e instanceof Error ? e.message : e}`,
        )
        // Intentional fall-through to legacy SAPI / espeak path below.
      }
    }

    // ── Legacy fallback (English SAPI / espeak-ng) ──────────────────
    // Kept as a safety net for offline operation or when the backend
    // doesn't have the /api/tts/synthesize endpoint yet (older deploys).
    const text = String(args.text ?? '')
    if (!text) throw new Error('text is required')
    const rate = Math.max(0, Math.min(10, Number(args.rate ?? 5)))
    const voiceArg = args.voice != null ? String(args.voice) : null
    const platform = osPlatform()

    if (platform === 'win32') {
      // Windows SAPI: rate is -10..10, map rate 0-10 → -10..10
      const sapiRate = Math.round(rate * 2 - 10)
      // Escape double-quotes in text to avoid breaking the PowerShell string.
      const safeText = text.replace(/"/g, '`"')
      const voiceLine = voiceArg
        ? `$s.SelectVoice("${voiceArg.replace(/"/g, '`"')}")`
        : ''
      const res = await asyncSpawn('powershell.exe', [
        '-NoProfile', '-NonInteractive', '-Command',
        `Add-Type -AssemblyName System.Speech; $s = New-Object System.Speech.Synthesis.SpeechSynthesizer; ${voiceLine} $s.Rate = ${sapiRate}; $s.Speak("${safeText}")`,
      ], { timeout: 30000 })
      if (res.error) throw new Error(res.error)
      if (res.status !== 0) {
        throw new Error(`SAPI Speak failed: ${res.stderr.trim()}`)
      }
    } else {
      // Linux: espeak-ng -s <wpm> [-v <voice>] "<text>"
      // Rate 0-10 → WPM 80-260
      const wpm = Math.round(80 + rate * 18)
      const speakArgs = ['-s', String(wpm)]
      if (voiceArg) speakArgs.push('-v', voiceArg)
      speakArgs.push(text)
      const res = await asyncSpawn('espeak-ng', speakArgs, { timeout: 30000 })
      if (res.error) {
        // Try plain espeak fallback
        const res2 = await asyncSpawn('espeak', speakArgs, { timeout: 30000 })
        if (res2.error) {
          throw new Error(
            `espeak-ng / espeak not found. Install on Linux: apt install espeak-ng`,
          )
        }
        if (res2.status !== 0) throw new Error(`espeak error: ${res2.stderr.trim()}`)
      } else if (res.status !== 0) {
        throw new Error(`espeak-ng error: ${res.stderr.trim()}`)
      }
    }
    return { spoken: true, length: text.length }
  },

  operator_screenshot_window: async (args) => {
    // Capture a specific window (by title substring or handle).
    // Linux: use wmctrl to resolve title→hex id, then ImageMagick `import -window <id>`.
    // Windows: focus the window then take a nut.js screen capture.
    const titleSub = args.title_substring != null ? String(args.title_substring) : null
    const handleArg = args.handle != null ? String(args.handle) : null
    const savePath = args.save_path != null ? String(args.save_path) : null

    if (titleSub === null && handleArg === null) {
      throw new Error('title_substring or handle is required')
    }

    const platform = osPlatform()
    const { tmpdir } = await import('node:os')
    const { join: pathJoin } = await import('node:path')
    const { readFileSync: readFS, unlinkSync, existsSync: existsFS } = await import('node:fs')

    const outPath = savePath ?? pathJoin(tmpdir(), `jarvisx_win_${Date.now()}.png`)

    if (platform === 'win32') {
      // Windows: focus the window first, then capture full screen, then crop.
      // Simpler than PrintWindow P/Invoke — focus + nut.js screen capture.
      const target = titleSub ?? handleArg ?? ''
      await asyncSpawn('powershell.exe', [
        '-NoProfile', '-NonInteractive', '-Command',
        `(New-Object -ComObject WScript.Shell).AppActivate("${target.replace(/"/g, '\\"')}")`,
      ], { timeout: 5000 })
      // Short delay to let the window come to front.
      await new Promise((r) => setTimeout(r, 400))
      const { screen: nutScreen } = await import('@nut-tree-fork/nut-js')
      const { FileType: FT } = await import('@nut-tree-fork/nut-js')
      await nutScreen.capture('jarvisx_win_snap', FT.PNG, outPath.replace(/\/[^/]+$/, ''), 'jarvisx_win_snap')
      // nut.js appends ext automatically — locate what it wrote.
      const nutOut = outPath.replace(/\/[^/]+$/, '') + '/jarvisx_win_snap.png'
      const imgBuf = readFS(existsFS(nutOut) ? nutOut : outPath)
      if (savePath) {
        if (nutOut !== outPath) {
          const { renameSync } = await import('node:fs')
          try { renameSync(nutOut, savePath) } catch {}
        }
        return { captured: true, path: savePath }
      }
      const b64 = imgBuf.toString('base64')
      try { unlinkSync(nutOut) } catch {}
      return { captured: true, base64: b64 }
    } else {
      // Linux: resolve window id via wmctrl, then ImageMagick `import -window`.
      let winId = handleArg

      if (titleSub !== null) {
        // wmctrl -l to find hex id matching title substring
        const listRes = await asyncSpawn('wmctrl', ['-l'], { timeout: 5000 })
        if (listRes.error) {
          throw new Error(
            `wmctrl not found. Install: apt install wmctrl`,
          )
        }
        for (const line of listRes.stdout.split('\n')) {
          const m = line.match(/^(0x[0-9a-f]+)\s+\d+\s+\S+\s+(.+)$/)
          if (m && m[2].toLowerCase().includes(titleSub.toLowerCase())) {
            winId = m[1]
            break
          }
        }
        if (!winId) {
          throw new Error(`No window found matching title: "${titleSub}"`)
        }
      }

      // ImageMagick import -window <id>
      const importRes = await asyncSpawn('import', ['-window', winId!, outPath], {
        timeout: 15000,
      })
      if (importRes.error) {
        throw new Error(
          `ImageMagick import not found. Install: apt install imagemagick`,
        )
      }
      if (importRes.status !== 0) {
        throw new Error(`ImageMagick import failed: ${importRes.stderr.trim()}`)
      }

      if (savePath) {
        return { captured: true, path: savePath }
      }
      const imgBuf = readFS(outPath)
      const b64 = imgBuf.toString('base64')
      try { const { unlinkSync: rmSync } = await import('node:fs'); rmSync(outPath) } catch {}
      return { captured: true, base64: b64 }
    }
  },

  operator_find_image: async (args) => {
    // Template-match a reference image against the current screen.
    // Uses nut.js screen.find() which does built-in image template matching.
    const templatePath = String(args.template_path ?? '')
    if (!templatePath) throw new Error('template_path is required')
    const confidence = Math.max(0.0, Math.min(1.0, Number(args.confidence ?? 0.85)))

    const { screen: nutScreen, imageResource } = await import('@nut-tree-fork/nut-js')
    // Set confidence threshold.
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    ;(nutScreen as any).config = {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      ...(nutScreen as any).config,
      confidence,
    }

    try {
      const img = await imageResource(templatePath)
      const region = await nutScreen.find(img)
      const cx = Math.round(region.left + region.width / 2)
      const cy = Math.round(region.top + region.height / 2)
      return { found: true, x: cx, y: cy, confidence }
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e)
      return { found: false, reason: `No match above confidence ${confidence}: ${msg}` }
    }
  },

  operator_ocr_region: async (args) => {
    // Extract text from screen region using Tesseract.
    // Flow: nut.js full-screen capture → ImageMagick crop → tesseract stdin → text.
    const x = Number(args.x)
    const y = Number(args.y)
    const width = Number(args.width)
    const height = Number(args.height)
    const lang = String(args.lang ?? 'eng')
    for (const [n, v] of [['x', x], ['y', y], ['width', width], ['height', height]]) {
      if (!Number.isFinite(v as number)) throw new Error(`${n} must be a finite number`)
    }
    if (width <= 0 || height <= 0) throw new Error('width and height must be positive')

    const { tmpdir } = await import('node:os')
    const { join: pathJoin } = await import('node:path')

    const tmpBase = pathJoin(tmpdir(), `jarvisx_ocr_${Date.now()}`)
    const cropPath = `${tmpBase}_crop.png`

    // 1. Capture full screen via nut.js
    const { screen: nutScreen, FileType: FT2 } = await import('@nut-tree-fork/nut-js')
    const snapDir = tmpdir()
    const snapName = `jarvisx_ocr_full_${Date.now()}`
    await nutScreen.capture(snapName, FT2.PNG, snapDir, snapName)
    const nutOut = pathJoin(snapDir, `${snapName}.png`)

    // 2. Crop to region using ImageMagick.
    // Windows has a built-in `convert.exe` (disk-conversion utility from
    // MS-DOS) that intercepts the bare `convert` call and fails with
    // "Invalid Parameter - -crop". ImageMagick 7+ ships a unified
    // `magick` binary which we prefer everywhere; on win32 we also probe
    // well-known install locations because winget often doesn't refresh
    // PATH for already-running processes.
    const cropGeom = `${width}x${height}+${x}+${y}`
    const im = findImageMagick()
    const useMagick = im.endsWith('magick.exe') || im === 'magick'
    const imArgs = useMagick
      ? ['convert', nutOut, '-crop', cropGeom, '+repage', cropPath]
      : [nutOut, '-crop', cropGeom, '+repage', cropPath]
    const cropRes = await asyncSpawn(im, imArgs, { timeout: 10000 })
    // Cleanup full screen shot.
    try { const { unlinkSync } = await import('node:fs'); unlinkSync(nutOut) } catch {}
    if (cropRes.error) {
      throw new Error(
        `ImageMagick convert not found. Install: apt install imagemagick`,
      )
    }
    if (cropRes.status !== 0) {
      throw new Error(`ImageMagick crop failed: ${cropRes.stderr.trim()}`)
    }

    // 3. Run tesseract on the cropped image (output to stdout).
    const tessRes = await asyncSpawn('tesseract', [cropPath, 'stdout', '-l', lang], {
      timeout: 30000,
    })
    // Cleanup crop.
    try { const { unlinkSync } = await import('node:fs'); unlinkSync(cropPath) } catch {}
    if (tessRes.error) {
      throw new Error(
        `tesseract not found. Install: apt install tesseract-ocr (Linux) or ` +
        `winget install Tesseract-OCR (Windows).`,
      )
    }
    if (tessRes.status !== 0 && tessRes.status !== null) {
      throw new Error(`tesseract failed: ${tessRes.stderr.trim()}`)
    }

    return {
      text: tessRes.stdout.trim(),
      region: { x, y, width, height },
    }
  },

  // ── Tier-3 wishlist tools ────────────────────────────────────────────

  operator_notify: async (args) => {
    // Show OS notification toast via Electron's Notification API.
    // Cross-platform: Linux (requires libnotify/notify-osd), macOS, Windows.
    const { Notification } = await import('electron')
    const title = String(args.title ?? '')
    const body = String(args.body ?? '')
    if (!title) throw new Error('title is required')
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const opts: Record<string, any> = { title, body }
    if (args.icon != null) opts.icon = String(args.icon)
    if (!Notification.isSupported()) {
      // On headless / CI environments notifications may be unavailable.
      fileLog('operator_notify: Notification not supported on this platform')
      return { shown: false, reason: 'not_supported' }
    }
    new Notification(opts).show()
    fileLog(`operator_notify: shown title="${title}"`)
    return { shown: true }
  },

  operator_watch_folder: async (args) => {
    // Start watching a folder using Node's fs.watch.
    // Events are buffered in a module-level map — poll with operator_watch_events.
    const watchPath = resolveOperatorPath(args.path)
    const recursive = Boolean(args.recursive ?? false)
    const debounceMs = Number(args.debounce_ms ?? 500)
    const { watch: fsWatch } = await import('node:fs')
    const { randomUUID } = await import('node:crypto')
    const { join: pathJoin } = await import('node:path')

    const watcherId = randomUUID()
    const eventBuffer: Array<{ path: string; event_type: string; timestamp: number }> = []
    const lastSeen = new Map<string, number>()

    let watcher: ReturnType<typeof fsWatch>
    try {
      watcher = fsWatch(watchPath, { recursive }, (eventType, filename) => {
        const now = Date.now()
        const key = `${eventType}:${filename ?? ''}`
        const last = lastSeen.get(key) ?? 0
        if (now - last < debounceMs) return
        lastSeen.set(key, now)
        eventBuffer.push({
          path: filename ? pathJoin(watchPath, filename) : watchPath,
          event_type: eventType,
          timestamp: now,
        })
        if (eventBuffer.length > 2000) eventBuffer.splice(0, eventBuffer.length - 2000)
      })
    } catch (e) {
      throw new Error(`fs.watch failed: ${e instanceof Error ? e.message : String(e)}`)
    }

    folderWatchers.set(watcherId, { watcher, buffer: eventBuffer })
    fileLog(`operator_watch_folder: started watcher_id=${watcherId} path=${watchPath} recursive=${recursive}`)
    return { watching: true, watcher_id: watcherId, path: watchPath }
  },

  operator_unwatch_folder: async (args) => {
    const watcherId = String(args.watcher_id ?? '')
    if (!watcherId) throw new Error('watcher_id is required')
    const entry = folderWatchers.get(watcherId)
    if (!entry) return { stopped: false, watcher_id: watcherId, reason: 'not_found' }
    try { entry.watcher.close() } catch {}
    folderWatchers.delete(watcherId)
    fileLog(`operator_unwatch_folder: stopped watcher_id=${watcherId}`)
    return { stopped: true, watcher_id: watcherId }
  },

  operator_watch_events: async (args) => {
    const watcherId = String(args.watcher_id ?? '')
    if (!watcherId) throw new Error('watcher_id is required')
    const maxEvents = Math.min(1000, Math.max(1, Number(args.max ?? 100)))
    const entry = folderWatchers.get(watcherId)
    if (!entry) return { events: [], count: 0, error: 'watcher_not_found' }
    const events = entry.buffer.splice(0, maxEvents)
    return { events, count: events.length }
  },

  operator_record_audio: async (args) => {
    // Godkendelse håndteres nu af runtime via chat-card FØR denne handler
    // kaldes. Når vi når hertil, har brugeren allerede godkendt i chatten.
    // Record audio via arecord (Linux) or ffmpeg (Windows/fallback).
    const durationS = Math.max(1, Math.min(300, Number(args.duration_s ?? 10)))
    const deviceArg = args.device != null ? String(args.device) : null
    const platform = osPlatform()

    // Determine output path
    const { mkdirSync: mkdirFS, statSync } = await import('node:fs')
    const { join: pathJoin } = await import('node:path')
    const recordingsDir = pathJoin(homedir(), '.jarvisx', 'recordings')
    mkdirFS(recordingsDir, { recursive: true })
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-')
    const defaultPath = pathJoin(recordingsDir, `recording-${timestamp}.wav`)
    const outputPath = args.output_path != null ? String(args.output_path) : defaultPath

    // Record via platform command
    let recordRes: AsyncSpawnResult
    if (platform === 'win32') {
      // Windows: ffmpeg dshow requires the EXACT device name (e.g.
      // 'Mikrofon (NOS X500)'). 'default' is not a valid dshow source —
      // it returns "Could not find device". Auto-discover the first
      // audio device if the caller didn't pass one explicitly.
      const deviceStr = deviceArg ?? findDshowAudioDevice()
      if (!deviceStr) {
        return {
          recorded: false,
          reason: 'no_audio_device',
          detail:
            'no dshow audio device found. Run `ffmpeg -list_devices true -f dshow -i dummy` ' +
            'to list installed mics, then pass the exact name as `device` arg.',
        }
      }
      recordRes = await asyncSpawn('ffmpeg', [
        '-y',
        '-f', 'dshow',
        '-i', `audio=${deviceStr}`,
        '-t', String(durationS),
        outputPath,
      ], { timeout: (durationS + 15) * 1000 })
      if (recordRes.error) {
        return { recorded: false, reason: 'tool_missing', detail: 'ffmpeg not found. Install: winget install ffmpeg' }
      }
    } else {
      // Linux: try arecord first (ALSA), fall back to parecord (PulseAudio)
      const arecordArgs = ['-d', String(durationS), '-f', 'cd', '-t', 'wav']
      if (deviceArg) arecordArgs.push('-D', deviceArg)
      arecordArgs.push(outputPath)
      recordRes = await asyncSpawn('arecord', arecordArgs, { timeout: (durationS + 15) * 1000 })
      if (recordRes.error) {
        // Try parecord fallback
        const parecordArgs = ['--file-format=wav', `--record-time=${durationS}`, outputPath]
        if (deviceArg) parecordArgs.push(`--device=${deviceArg}`)
        recordRes = await asyncSpawn('parecord', parecordArgs, { timeout: (durationS + 15) * 1000 })
        if (recordRes.error) {
          return {
            recorded: false,
            reason: 'tool_missing',
            detail: 'arecord / parecord not found. Install: apt install alsa-utils (or pulseaudio-utils)',
          }
        }
      }
    }

    if (recordRes.status !== 0 && recordRes.status !== null) {
      const errOut = typeof recordRes.stderr === 'string' ? recordRes.stderr : String(recordRes.stderr ?? '')
      throw new Error(`recording failed: ${errOut.trim()}`)
    }

    let sizeBytes = 0
    try { sizeBytes = statSync(outputPath).size } catch {}
    fileLog(`operator_record_audio: recorded ${durationS}s → ${outputPath} (${sizeBytes} bytes)`)
    return { recorded: true, path: outputPath, duration_s: durationS, size_bytes: sizeBytes }
  },

  // ── Scheduled events: reminders + wakeups ────────────────────────────
  // Two tool families that share one underlying timer registry:
  //   operator_reminder  — fire a toast at time T (Jarvis nudge to user)
  //   operator_wakeup    — same, but tagged 'wakeup' so future versions
  //                        can POST back to backend ("Jarvis, you asked
  //                        me to ping you at 8 — go check chat")
  // Persisted to userData so events survive app restart. setTimeout caps
  // at ~25 days, so super-long delays chain via reschedule on tick.

  operator_reminder: async (args) => {
    const due_at = parseEventWhen(args.when)
    const ev = createScheduledEvent({
      kind: 'reminder',
      due_at,
      title: String(args.title ?? 'Påmindelse'),
      message: String(args.message ?? ''),
    })
    return scheduledEventToReturn(ev)
  },

  operator_wakeup: async (args) => {
    const due_at = parseEventWhen(args.when)
    const ev = createScheduledEvent({
      kind: 'wakeup',
      due_at,
      title: String(args.title ?? 'Jarvis-wakeup'),
      message: String(args.message ?? 'Tid til at vågne'),
    })
    return scheduledEventToReturn(ev)
  },

  operator_scheduled_list: async (args) => {
    const kind = args.kind ? String(args.kind) : null
    const includeFired = Boolean(args.include_fired)
    const all = Array.from(_scheduledEvents.values())
    const filtered = all.filter((e) => {
      if (kind && e.kind !== kind) return false
      if (!includeFired && e.fired_at != null) return false
      return true
    })
    return {
      count: filtered.length,
      events: filtered.map((e) => ({
        id: e.id,
        kind: e.kind,
        due_at_iso: new Date(e.due_at).toISOString(),
        title: e.title,
        message: e.message,
        created_at_iso: new Date(e.created_at).toISOString(),
        fired_at_iso: e.fired_at ? new Date(e.fired_at).toISOString() : null,
      })),
    }
  },

  operator_scheduled_cancel: async (args) => {
    const id = String(args.id ?? '').trim()
    if (!id) throw new Error('id is required')
    const t = _eventTimers.get(id)
    if (t) { clearTimeout(t); _eventTimers.delete(id) }
    const existed = _scheduledEvents.delete(id)
    if (existed) saveScheduledEvents()
    return { cancelled: existed, id }
  },

  // ── Supervised processes: long-running spawn + status/output/kill ─────
  // Fills the gap between operator_bash (synchronous, blocks until done)
  // and operator_launch_app (fire-and-forget, no follow-up). spawn returns
  // a process_id; status / output / kill use it to query or terminate.

  operator_process_spawn: async (args) => {
    const cmd = String(args.cmd ?? '').trim()
    if (!cmd) throw new Error('cmd is required')
    const cwd = args.cwd ? resolveOperatorPath(args.cwd) : homedir()
    const label = String(args.label ?? cmd.slice(0, 60))
    const { randomUUID: ruuid } = await import('node:crypto')
    const id = ruuid()
    const { tmpdir: tDir } = await import('node:os')
    const logDir = join(tDir(), 'jarvisx-processes')
    mkdirSync(logDir, { recursive: true })
    const logPath = join(logDir, `${id}.log`)
    const { createWriteStream } = await import('node:fs')
    const out = createWriteStream(logPath, { flags: 'a' })
    out.write(`[jarvisx supervised process ${id}]\ncmd: ${cmd}\ncwd: ${cwd}\nstarted_at: ${new Date().toISOString()}\n──── output ────\n`)
    const child = spawn(cmd, {
      cwd,
      shell: true,
      stdio: ['ignore', 'pipe', 'pipe'],
      windowsHide: true,
      env: process.env,
    })
    if (child.stdout) child.stdout.pipe(out, { end: false })
    if (child.stderr) child.stderr.pipe(out, { end: false })
    const proc: SupervisedProcess = {
      id,
      pid: child.pid ?? null,
      label,
      cmd,
      cwd,
      started_at: Date.now(),
      log_path: logPath,
      child,
    }
    child.on('exit', (code, signal) => {
      proc.exit_code = code
      proc.finished_at = Date.now()
      try { out.end(`\n──── exited (code=${code}, signal=${signal}) at ${new Date().toISOString()} ────\n`) } catch {}
      fileLog(`operator_process: ${id} exited code=${code}`)
    })
    child.on('error', (err) => {
      try { out.write(`\n──── spawn error: ${err.message} ────\n`) } catch {}
      proc.exit_code = -1
      proc.finished_at = Date.now()
      fileLog(`operator_process: ${id} spawn error: ${err.message}`)
    })
    _processes.set(id, proc)
    fileLog(`operator_process_spawn: ${id} pid=${proc.pid} cmd=${cmd.slice(0, 80)}`)
    return { id, pid: proc.pid, label, log_path: logPath, started_at_iso: new Date(proc.started_at).toISOString() }
  },

  operator_process_status: async (args) => {
    const id = String(args.id ?? '').trim()
    const p = _processes.get(id)
    if (!p) throw new Error(`unknown process_id: ${id}`)
    const finished = p.finished_at != null
    let logSize = 0
    try { logSize = statSync(p.log_path).size } catch {}
    return {
      id: p.id,
      pid: p.pid,
      label: p.label,
      cmd: p.cmd,
      cwd: p.cwd,
      started_at_iso: new Date(p.started_at).toISOString(),
      finished_at_iso: p.finished_at ? new Date(p.finished_at).toISOString() : null,
      runtime_s: ((p.finished_at ?? Date.now()) - p.started_at) / 1000,
      running: !finished,
      exit_code: p.exit_code ?? null,
      log_path: p.log_path,
      log_size_bytes: logSize,
    }
  },

  operator_process_output: async (args) => {
    const id = String(args.id ?? '').trim()
    const p = _processes.get(id)
    if (!p) throw new Error(`unknown process_id: ${id}`)
    const since = Math.max(0, Number(args.since_offset ?? 0))
    const maxBytes = Math.min(Math.max(Number(args.max_bytes ?? 64_000), 500), 1_000_000)
    const { openSync, readSync, closeSync, statSync: stat2 } = await import('node:fs')
    let size = 0
    try { size = stat2(p.log_path).size } catch {}
    const start = Math.min(since, size)
    const end = Math.min(start + maxBytes, size)
    let data = ''
    if (end > start) {
      const fd = openSync(p.log_path, 'r')
      const buf = Buffer.alloc(end - start)
      readSync(fd, buf, 0, buf.length, start)
      closeSync(fd)
      data = buf.toString('utf8')
    }
    return {
      data,
      next_offset: end,
      total_size: size,
      has_more: end < size,
      running: p.finished_at == null,
    }
  },

  operator_process_kill: async (args) => {
    const id = String(args.id ?? '').trim()
    const p = _processes.get(id)
    if (!p) throw new Error(`unknown process_id: ${id}`)
    const sig = args.signal ? String(args.signal) : 'SIGTERM'
    try {
      const killed = p.child.kill(sig as NodeJS.Signals)
      return { killed, id, signal: sig, was_running: p.finished_at == null }
    } catch (e) {
      return { killed: false, id, error: e instanceof Error ? e.message : String(e) }
    }
  },

  operator_process_list: async (args) => {
    const includeFinished = Boolean(args.include_finished ?? true)
    const procs = Array.from(_processes.values()).filter((p) => includeFinished || p.finished_at == null)
    return {
      count: procs.length,
      processes: procs.map((p) => ({
        id: p.id,
        pid: p.pid,
        label: p.label,
        cmd: p.cmd.slice(0, 120),
        started_at_iso: new Date(p.started_at).toISOString(),
        finished_at_iso: p.finished_at ? new Date(p.finished_at).toISOString() : null,
        running: p.finished_at == null,
        exit_code: p.exit_code ?? null,
      })),
    }
  },
}

// ── Scheduled events store (reminders + wakeups) ──────────────────────

interface ScheduledEvent {
  id: string
  kind: 'reminder' | 'wakeup'
  due_at: number      // ms since epoch
  title: string
  message: string
  created_at: number
  fired_at?: number
}

const _scheduledEvents: Map<string, ScheduledEvent> = new Map()
const _eventTimers: Map<string, NodeJS.Timeout> = new Map()

function scheduledEventsPath(): string {
  return join(homedir(), '.config', 'jarvisx', 'scheduled-events.json')
}

function saveScheduledEvents(): void {
  try {
    const p = scheduledEventsPath()
    mkdirSync(dirname(p), { recursive: true })
    writeFileSync(p, JSON.stringify(Array.from(_scheduledEvents.values()), null, 2), 'utf8')
  } catch (e) {
    fileLog(`saveScheduledEvents failed: ${e instanceof Error ? e.message : e}`)
  }
}

function scheduleEventTimer(e: ScheduledEvent): void {
  const existing = _eventTimers.get(e.id)
  if (existing) clearTimeout(existing)
  const delay = Math.max(0, e.due_at - Date.now())
  // setTimeout max ~24.85 days. For longer delays, re-schedule mid-flight.
  const SAFE_MAX = 2_000_000_000
  const tickDelay = Math.min(delay, SAFE_MAX)
  const t = setTimeout(() => {
    if (Date.now() < e.due_at - 100) {
      // Long-delay reschedule: not yet due, set next chunk
      scheduleEventTimer(e)
    } else {
      void fireScheduledEvent(e.id)
    }
  }, tickDelay)
  _eventTimers.set(e.id, t)
}

async function fireScheduledEvent(id: string): Promise<void> {
  const e = _scheduledEvents.get(id)
  if (!e || e.fired_at) return
  e.fired_at = Date.now()
  saveScheduledEvents()
  _eventTimers.delete(id)
  try {
    const { Notification } = await import('electron')
    if (Notification.isSupported()) {
      new Notification({ title: e.title, body: e.message }).show()
    }
  } catch (err) {
    fileLog(`fireScheduledEvent notification failed: ${err instanceof Error ? err.message : err}`)
  }
  fileLog(`fired ${e.kind} ${id}: "${e.title}" — "${e.message.slice(0, 60)}"`)
  // Wakeups additionally try to POST back to the backend so Jarvis-side
  // can react ("user was pinged via wakeup id X, dispatch greeting").
  // Best-effort; failure doesn't matter for the local notification.
  if (e.kind === 'wakeup') {
    const cfg = _activeBridgeCfg
    if (cfg?.apiBaseUrl) {
      try {
        const headers: Record<string, string> = { 'Content-Type': 'application/json' }
        if (cfg.authToken) headers['Authorization'] = `Bearer ${cfg.authToken}`
        await fetch(`${cfg.apiBaseUrl.replace(/\/$/, '')}/api/operator/wakeup-fired`, {
          method: 'POST',
          headers,
          body: JSON.stringify({
            wakeup_id: id, title: e.title, message: e.message, fired_at: e.fired_at,
            // Bind re-engagement til den session brugeren har fremme → wakeup
            // lander i samme desk-samtale, ikke en frisk (eller Discord).
            session_id: _activeSessionId,
            // App-ID følger med så serveren kan verificere session-binding.
            app_id: cfg.appId,
          }),
        }).catch(() => undefined)
      } catch {}
    }
  }
}

// Parse a 'when' arg: ISO string, ms-epoch number, or relative like "+5m",
// "+1h30m", "+2d". Returns ms-since-epoch.
function parseEventWhen(when: unknown): number {
  if (typeof when === 'number' && Number.isFinite(when)) {
    return when > 1e12 ? when : when * 1000
  }
  const str = String(when ?? '').trim()
  if (!str) throw new Error('when is required')
  const rel = str.match(/^\+?(?:(\d+)d)?\s*(?:(\d+)h)?\s*(?:(\d+)m)?\s*(?:(\d+)s)?$/i)
  if (rel && (rel[1] || rel[2] || rel[3] || rel[4])) {
    let ms = 0
    if (rel[1]) ms += parseInt(rel[1], 10) * 86_400_000
    if (rel[2]) ms += parseInt(rel[2], 10) * 3_600_000
    if (rel[3]) ms += parseInt(rel[3], 10) * 60_000
    if (rel[4]) ms += parseInt(rel[4], 10) * 1000
    if (ms > 0) return Date.now() + ms
  }
  const d = new Date(str)
  if (isNaN(d.getTime())) throw new Error(`unparseable when: "${when}"`)
  return d.getTime()
}

function createScheduledEvent(opts: { kind: ScheduledEvent['kind']; due_at: number; title: string; message: string }): ScheduledEvent {
  const id = randomUUID()
  const e: ScheduledEvent = {
    id,
    kind: opts.kind,
    due_at: opts.due_at,
    title: opts.title,
    message: opts.message,
    created_at: Date.now(),
  }
  _scheduledEvents.set(id, e)
  saveScheduledEvents()
  scheduleEventTimer(e)
  fileLog(`scheduled ${e.kind} ${id} for ${new Date(e.due_at).toISOString()}`)
  return e
}

function scheduledEventToReturn(e: ScheduledEvent): Record<string, unknown> {
  return {
    id: e.id,
    kind: e.kind,
    due_at_iso: new Date(e.due_at).toISOString(),
    title: e.title,
    delay_ms: e.due_at - Date.now(),
  }
}

// Called once at app start to resurrect any reminders/wakeups left from
// previous runs. Past-due ones fire immediately (catch-up), future ones
// get fresh setTimeout entries.
export function loadAndScheduleEvents(): void {
  try {
    const p = scheduledEventsPath()
    if (!existsSync(p)) return
    const raw = readFileSync(p, 'utf8')
    const arr = JSON.parse(raw) as ScheduledEvent[]
    if (!Array.isArray(arr)) return
    const now = Date.now()
    const PURGE_FIRED_OLDER_THAN_MS = 7 * 86_400_000
    for (const e of arr) {
      if (e.fired_at && (now - e.fired_at) > PURGE_FIRED_OLDER_THAN_MS) continue
      _scheduledEvents.set(e.id, e)
      if (!e.fired_at) {
        if (e.due_at <= now) {
          void fireScheduledEvent(e.id)
        } else {
          scheduleEventTimer(e)
        }
      }
    }
    // Re-save with purged entries
    saveScheduledEvents()
    fileLog(`loadAndScheduleEvents: resurrected ${_scheduledEvents.size} entries`)
  } catch (e) {
    fileLog(`loadAndScheduleEvents failed: ${e instanceof Error ? e.message : e}`)
  }
}

// ── Supervised process registry ───────────────────────────────────────

interface SupervisedProcess {
  id: string
  pid: number | null
  label: string
  cmd: string
  cwd: string
  started_at: number
  finished_at?: number
  exit_code?: number | null
  log_path: string
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  child: any
}

const _processes: Map<string, SupervisedProcess> = new Map()

// ── Browser-session singleton helpers ───────────────────────────────────

interface BrowserSession {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  browser: any
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  page: any
  lastUsed: number
  idleTimer: NodeJS.Timeout | null
}

let browserSession: BrowserSession | null = null
const BROWSER_IDLE_MS = 5 * 60 * 1000  // close session after 5 min idle

// ── Folder-watcher singleton store ──────────────────────────────────────

interface FolderWatcherEntry {
  watcher: import('node:fs').FSWatcher
  buffer: Array<{ path: string; event_type: string; timestamp: number }>
}

const folderWatchers = new Map<string, FolderWatcherEntry>()

function findBrowserExecutable(): string {
  const candidates = [
    'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
    'C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe',
    join(homedir(), 'AppData', 'Local', 'Google', 'Chrome', 'Application', 'chrome.exe'),
    'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe',
    'C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe',
    // macOS / Linux fallbacks — keeps the bridge code portable
    '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    '/usr/bin/google-chrome',
    '/usr/bin/chromium',
    '/usr/bin/chromium-browser',
  ]
  for (const p of candidates) {
    try {
      if (existsSync(p)) return p
    } catch {}
  }
  throw new Error(
    'No Chrome/Edge browser found. Install Google Chrome or Microsoft Edge.',
  )
}

async function ensureBrowserSession(): Promise<BrowserSession> {
  if (browserSession) {
    browserSession.lastUsed = Date.now()
    scheduleBrowserIdleClose()
    return browserSession
  }
  const puppeteer = await import('puppeteer-core')
  const executablePath = findBrowserExecutable()
  // Dedicated profile so we don't trample on the user's main Chrome
  // session / cookies / extensions.
  const userDataDir = join(homedir(), '.config', 'jarvisx', 'browser-profile')
  mkdirSync(userDataDir, { recursive: true })
  const browser = await puppeteer.launch({
    executablePath,
    headless: false,
    userDataDir,
    defaultViewport: null, // use the window's native size
    args: [
      '--no-default-browser-check',
      '--no-first-run',
      '--disable-features=TranslateUI',
      '--start-maximized',
    ],
  })
  const pages = await browser.pages()
  const page = pages.length > 0 ? pages[0] : await browser.newPage()
  browserSession = {
    browser,
    page,
    lastUsed: Date.now(),
    idleTimer: null,
  }
  // If user closes the window manually, drop the session reference so
  // the next tool call boots a fresh one.
  browser.on('disconnected', () => {
    if (browserSession?.idleTimer) clearTimeout(browserSession.idleTimer)
    browserSession = null
    fileLog('browser session disconnected')
  })
  scheduleBrowserIdleClose()
  fileLog(`browser session opened (executable=${executablePath})`)
  return browserSession
}

function scheduleBrowserIdleClose(): void {
  if (!browserSession) return
  if (browserSession.idleTimer) clearTimeout(browserSession.idleTimer)
  browserSession.idleTimer = setTimeout(async () => {
    if (!browserSession) return
    const idleFor = Date.now() - browserSession.lastUsed
    if (idleFor >= BROWSER_IDLE_MS) {
      try {
        await browserSession.browser.close()
      } catch {}
      browserSession = null
      fileLog('browser session closed (idle)')
    } else {
      scheduleBrowserIdleClose()
    }
  }, BROWSER_IDLE_MS)
  // Don't keep the process alive solely on this timer.
  browserSession.idleTimer.unref?.()
}

const RECONNECT_BACKOFF_MS = [1000, 2000, 4000, 8000, 15000, 30000]
// No-traffic watchdog: if we don't receive ANY message (incl. ping/pong)
// within this window, the server has gone silent and our "OPEN" status
// is a TCP-level zombie. Force-close + reconnect. Server sends ping
// every 25s; we expect at least one message every ~30s.
const TRAFFIC_TIMEOUT_MS = 75_000

export class JarvisXBridge {
  private ws: WebSocket | null = null
  private reconnectAttempt = 0
  private stopped = false
  private heartbeatTimer: NodeJS.Timeout | null = null
  private trafficWatchdog: NodeJS.Timeout | null = null
  private lastMessageAt = 0

  constructor(private cfg: BridgeConfig) {
    // Publish the latest cfg at module scope so handler code (operator_speak
    // etc.) can read apiBaseUrl/authToken to call back into the backend.
    _activeBridgeCfg = cfg
  }

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
    if (this.trafficWatchdog) clearInterval(this.trafficWatchdog)
    if (this.ws) {
      try { this.ws.close(1000, 'client_stop') } catch {}
    }
  }

  private noteTraffic(): void {
    this.lastMessageAt = Date.now()
  }

  private startTrafficWatchdog(): void {
    if (this.trafficWatchdog) clearInterval(this.trafficWatchdog)
    this.lastMessageAt = Date.now()
    // Check every 10s — granularity finer than TRAFFIC_TIMEOUT_MS so we
    // catch the deadline within ~10s of breach.
    this.trafficWatchdog = setInterval(() => {
      if (!this.ws || this.ws.readyState !== WebSocket.OPEN) return
      const elapsed = Date.now() - this.lastMessageAt
      if (elapsed > TRAFFIC_TIMEOUT_MS) {
        this.log(`no traffic in ${Math.round(elapsed / 1000)}s — forcing reconnect`)
        try { this.ws.terminate?.() } catch {}  // hard-close vs close()
        try { this.ws.close(4001, 'no_traffic') } catch {}
        // 'close' handler will schedule reconnect
      }
    }, 10_000)
    this.trafficWatchdog.unref?.()
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
        os: process.platform,  // 'linux' | 'darwin' | 'win32' — used for path/shell hints
        capabilities: Object.keys(handlers),
      })
      // Start heartbeat (every 25s, server expects activity within ~30s)
      this.heartbeatTimer = setInterval(() => this.send({ type: 'ping' }), 25_000)
      // Start no-traffic watchdog — detect zombie TCP within ~75s
      this.startTrafficWatchdog()
    })

    this.ws.on('message', (raw) => {
      this.noteTraffic()
      void this.handleMessage(String(raw))
    })

    this.ws.on('close', (code, reason) => {
      this.log(`ws close code=${code} reason=${reason || '(none)'}`)
      if (this.heartbeatTimer) {
        clearInterval(this.heartbeatTimer)
        this.heartbeatTimer = null
      }
      if (this.trafficWatchdog) {
        clearInterval(this.trafficWatchdog)
        this.trafficWatchdog = null
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
      const invokeMode = String(msg.mode ?? '').toLowerCase()
      this.log(`tool_invoke tool=${tool} mode=${invokeMode || '(legacy)'} args=${JSON.stringify(args).slice(0, 120)}`)
      // §17.6.1: kun code-mode anmodninger eksekveres LOKALT. chat/cowork må ikke
      // køre operator tools på brugerens maskine. Tom mode = legacy → tillad (bagudkompat).
      if (!isLocalExecutionMode(invokeMode)) {
        this.send({
          type: 'tool_result',
          correlation_id,
          status: 'error',
          result: null,
          error: `mode_not_local: operator tools kører kun lokalt i code mode (mode=${invokeMode})`,
        })
        this.log(`  → afvist (mode=${invokeMode}, ikke code)`)
        return
      }
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
        // Per-handler timeout. Without this, a hung handler (browser
        // session stuck, bash command waiting forever) blocks the whole
        // bridge. Server-side already times out the dispatch via
        // asyncio.wait_for(fut, timeout=timeout_s); we race against a
        // slightly higher deadline so the server gives up FIRST when
        // both fire — gives cleaner error reporting.
        //
        // The server sends timeout_ms in the tool_invoke message; we
        // use that plus a 10s grace margin. Fallback to 45s if the
        // server didn't provide a value (legacy).
        const serverTimeoutMs = Number(msg.timeout_ms) || 35_000
        const HANDLER_TIMEOUT_MS = Math.min(
          serverTimeoutMs + 10_000,
          120_000,  // hard ceiling: 2 min
        )
        const result = await Promise.race([
          handler(args),
          new Promise((_, reject) =>
            setTimeout(
              () => reject(new Error(`handler_timeout: ${tool} did not respond within 40s`)),
              HANDLER_TIMEOUT_MS,
            ),
          ),
        ])
        this.send({
          type: 'tool_result',
          correlation_id,
          status: 'ok',
          result,
          error: null,
          mode: invokeMode || 'code',
          local_execution: true,
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