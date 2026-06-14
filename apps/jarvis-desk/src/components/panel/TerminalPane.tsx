import { useEffect, useRef } from 'react'
import { Terminal } from '@xterm/xterm'
import { FitAddon } from '@xterm/addon-fit'
import '@xterm/xterm/css/xterm.css'
import { handleKey, emptyLine, type LineState } from '../../lib/terminalLine'

/** Renderer-side type for terminal-broen (udsat via preload). */
interface TerminalBridge {
  run: (id: string, command: string, cwd?: string) => Promise<{ ok: boolean; error?: string }>
  signal: (id: string, signal?: string) => Promise<{ ok: boolean }>
  onData: (cb: (e: { id: string; stream: 'stdout' | 'stderr'; chunk: string }) => void) => () => void
  onExit: (cb: (e: { id: string; code: number }) => void) => () => void
}
function terminalBridge(): TerminalBridge | null {
  const b = (window as unknown as { jarvisDesk?: { terminal?: TerminalBridge } }).jarvisDesk
  return b?.terminal ?? null
}

let paneSeq = 0

/** Code-mode terminal-rude (§17): lokal kommando-runner på brugerens egen maskine.
 *  Kører KUN i workstation-workspace — kommandoer går via operator-modellen, output
 *  bliver på maskinen. Interaktive TTY-programmer (vim/top) understøttes ikke i v1. */
export function TerminalPane({ cwd }: { cwd: string }) {
  const hostRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const host = hostRef.current
    const bridge = terminalBridge()
    if (!host) return
    if (!bridge) {
      host.textContent = 'Terminal er kun tilgængelig i den installerede app.'
      return
    }

    const id = `term-${++paneSeq}-${cwd.length}`
    const term = new Terminal({
      fontSize: 13,
      fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, monospace',
      cursorBlink: true,
      theme: { background: '#0d0d0f', foreground: '#e6e6e6' },
      convertEol: true,
    })
    const fit = new FitAddon()
    term.loadAddon(fit)
    term.open(host)
    try { fit.fit() } catch { /* host endnu ikke målt */ }

    let line: LineState = emptyLine
    let running = false
    const prompt = () => term.write(`\r\n\x1b[36m${cwd}\x1b[0m $ `)

    term.writeln('\x1b[90mLokal terminal — kører kommandoer i den valgte mappe på din computer.\x1b[0m')
    term.writeln('\x1b[90m(v1: én kommando ad gangen; ingen interaktive TTY-programmer.)\x1b[0m')
    prompt()

    const offData = bridge.onData((e) => {
      if (e.id !== id) return
      // stderr i blødt rødt, stdout normalt.
      if (e.stream === 'stderr') term.write(`\x1b[31m${e.chunk}\x1b[0m`)
      else term.write(e.chunk)
    })
    const offExit = bridge.onExit((e) => {
      if (e.id !== id) return
      running = false
      if (e.code !== 0) term.write(`\r\n\x1b[90m[afsluttet med kode ${e.code}]\x1b[0m`)
      prompt()
    })

    const keyDisp = term.onData((key) => {
      if (running) {
        // Mens en kommando kører: kun Ctrl-C videresendes (afbryd).
        if (key === String.fromCharCode(3)) void bridge.signal(id, 'SIGINT')
        return
      }
      const { state, action } = handleKey(line, key)
      line = state
      switch (action.type) {
        case 'echo':
          term.write(action.text)
          break
        case 'backspace':
          term.write('\b \b')
          break
        case 'interrupt':
          term.write('^C')
          prompt()
          break
        case 'submit': {
          const cmd = action.command.trim()
          term.write('\r\n')
          if (!cmd) { prompt(); break }
          if (cmd === 'clear' || cmd === 'cls') { term.clear(); prompt(); break }
          running = true
          void bridge.run(id, cmd, cwd).then((r) => {
            if (!r.ok) { term.write(`\x1b[31m${r.error || 'kunne ikke starte kommando'}\x1b[0m`); running = false; prompt() }
          })
          break
        }
        default:
          break
      }
    })

    const onResize = () => { try { fit.fit() } catch { /* noop */ } }
    window.addEventListener('resize', onResize)

    return () => {
      window.removeEventListener('resize', onResize)
      offData()
      offExit()
      keyDisp.dispose()
      void bridge.signal(id, 'SIGTERM')
      term.dispose()
    }
  }, [cwd])

  return <div className="terminalpane" ref={hostRef} />
}
