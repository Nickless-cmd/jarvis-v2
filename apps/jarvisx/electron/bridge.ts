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
import { dialog, desktopCapturer, screen, shell as electronShell } from 'electron'
import { spawn } from 'node:child_process'
import WebSocket from 'ws'

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

    const skipApproval = Boolean(args.skip_approval)

    if (!skipApproval) {
      // Approval dialog — operator must explicitly approve every command.
      // Auto-rejects after 20s if no response.
      const APPROVAL_DEADLINE_MS = 20_000
      const choice = await Promise.race<{ response: number }>([
        dialog.showMessageBox({
          type: 'warning',
          title: 'Jarvis vil køre en kommando',
          message: 'Jarvis beder om at køre en shell-kommando på din maskine.',
          detail: `Kommando:\n  ${command}\n\nMappe:\n  ${cwd}\n\nTimeout: ${timeoutS}s\n\nAuto-afviser efter 20 sek hvis du ikke svarer.`,
          buttons: ['Afvis', 'Godkend og kør'],
          defaultId: 0,
          cancelId: 0,
          noLink: true,
        }),
        new Promise<{ response: number }>((resolve) =>
          setTimeout(() => resolve({ response: 0 }), APPROVAL_DEADLINE_MS),
        ),
      ])

      if (choice.response !== 1) {
        return {
          approved: false,
          stdout: '',
          stderr: '',
          exit_code: null,
          timed_out: false,
        }
      }
    }
    // else: trust-all mode — no dialog, command runs directly.

    // Platform-aware shell selection: bash on Linux/macOS, PowerShell
    // on Windows. Same surface for the LLM — shell-features (pipes,
    // redirects, env-vars) work in both.
    const shell = selectShell()
    const result = spawnSync(shell.cmd, shell.args(command), {
      cwd,
      timeout: timeoutS * 1000,
      encoding: 'utf8',
      maxBuffer: 5 * 1024 * 1024, // 5 MB stdout cap
    })

    return {
      approved: true,
      platform: osPlatform(),
      shell: shell.cmd,
      stdout: (result.stdout ?? '').slice(0, 100_000),
      stderr: (result.stderr ?? '').slice(0, 50_000),
      exit_code: result.status,
      timed_out: result.signal === 'SIGTERM' && result.error?.message?.includes('timed out'),
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
    // Open a URL in the operator's default browser. Asks for approval
    // unless skip_approval=true (Trust All).
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

    const skipApproval = Boolean(args.skip_approval)
    if (!skipApproval) {
      const choice = await Promise.race<{ response: number }>([
        dialog.showMessageBox({
          type: 'question',
          title: 'Jarvis vil åbne en URL',
          message: 'Jarvis beder om at åbne en URL i din browser.',
          detail: `URL:\n  ${url}\n\nAuto-afviser efter 20 sek hvis du ikke svarer.`,
          buttons: ['Afvis', 'Åbn'],
          defaultId: 1,
          cancelId: 0,
          noLink: true,
        }),
        new Promise<{ response: number }>((resolve) =>
          setTimeout(() => resolve({ response: 0 }), 20_000),
        ),
      ])
      if (choice.response !== 1) {
        return { approved: false, opened: false, url }
      }
    }

    // electronShell.openExternal is the OS-native "open" — defers to
    // the default handler (browser for http/https, mail client for mailto).
    await electronShell.openExternal(url)
    return { approved: true, opened: true, url }
  },

  operator_launch_app: async (args) => {
    // Launch an installed application. Accepts either a full path or a
    // name resolvable on PATH (e.g. 'notepad', 'code', 'chrome').
    // For UWP apps, pass the AppId like 'shell:appsFolder\\<AppId>' as `path`.
    const target = String(args.path ?? args.app ?? '').trim()
    if (!target) throw new Error('path (or app) is required')

    const cliArgs: string[] = Array.isArray(args.args)
      ? args.args.map((a) => String(a))
      : []
    const cwd = args.cwd ? resolveOperatorPath(args.cwd) : homedir()

    const skipApproval = Boolean(args.skip_approval)
    if (!skipApproval) {
      const argsPreview = cliArgs.length > 0 ? `\n\nArgumenter:\n  ${cliArgs.join(' ')}` : ''
      const choice = await Promise.race<{ response: number }>([
        dialog.showMessageBox({
          type: 'warning',
          title: 'Jarvis vil starte en app',
          message: 'Jarvis beder om at starte et program på din maskine.',
          detail: `App:\n  ${target}${argsPreview}\n\nMappe:\n  ${cwd}\n\nAuto-afviser efter 20 sek hvis du ikke svarer.`,
          buttons: ['Afvis', 'Start'],
          defaultId: 0,
          cancelId: 0,
          noLink: true,
        }),
        new Promise<{ response: number }>((resolve) =>
          setTimeout(() => resolve({ response: 0 }), 20_000),
        ),
      ])
      if (choice.response !== 1) {
        return { approved: false, started: false, path: target }
      }
    }

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
        approved: true,
        started: true,
        path: target,
        pid: child.pid ?? null,
      }
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e)
      return { approved: true, started: false, path: target, error: msg }
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
    // Run arbitrary JS in the page context. Powerful — requires approval
    // unless skip_approval=true. Returns whatever the script returns
    // (must be JSON-serializable).
    const script = String(args.script ?? '')
    if (!script) throw new Error('script is required')

    const skipApproval = Boolean(args.skip_approval)
    if (!skipApproval) {
      const choice = await Promise.race<{ response: number }>([
        dialog.showMessageBox({
          type: 'warning',
          title: 'Jarvis vil køre JavaScript i din browser',
          message: 'Jarvis beder om at evaluere JavaScript i den aktive side.',
          detail: `Side:\n  (browser-session)\n\nScript:\n  ${script.slice(0, 400)}${script.length > 400 ? '…' : ''}\n\nAuto-afviser efter 20 sek.`,
          buttons: ['Afvis', 'Kør'],
          defaultId: 0,
          cancelId: 0,
          noLink: true,
        }),
        new Promise<{ response: number }>((resolve) =>
          setTimeout(() => resolve({ response: 0 }), 20_000),
        ),
      ])
      if (choice.response !== 1) {
        return { approved: false, executed: false }
      }
    }

    const sess = await ensureBrowserSession()
    // Wrap script in a function so we can return arbitrary expressions.
    // The model can use either `return X;` syntax or just an expression.
    const wrapped = `(async () => { ${script} })()`
    const result = await sess.page.evaluate(wrapped)
    return { approved: true, executed: true, result }
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
}

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
        // Per-handler timeout. Without this, a hung handler (browser
        // session stuck, bash command waiting forever) blocks the whole
        // bridge. Server-side already times out the dispatch at 30s; we
        // race against a slightly higher deadline (40s) so the server
        // gives up first when both fire — gives cleaner error reporting.
        const HANDLER_TIMEOUT_MS = 40_000
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
