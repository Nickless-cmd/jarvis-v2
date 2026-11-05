/**
 * Klient til `/ws/browser` — Jarvis' server-side browser som JPEG-frames.
 *
 * Bruges af JarvisBrowserPanel når Electron-broen (`window.jarvisDesk.browser`)
 * mangler, dvs. i PWA/web. Egen fil, så den delte `api.ts` er urørt; subprotokol-
 * navnet er det samme som `WS_SUBPROTOKOL` og `core/runtime/ws_auth.SUBPROTOKOL`.
 */
import type { ApiConfig } from './tokenRenewal'

const SUBPROTOKOL = 'jarvis-bearer'

export interface StreamFane {
  id: number
  url: string
  titel: string
  aktiv: boolean
  kanTilbage: boolean
  kanFrem: boolean
  henter: boolean
}

export type StreamInput =
  | { t: 'mouse'; kind: 'move' | 'down' | 'up' | 'wheel'; x: number; y: number; button?: 'left' | 'middle' | 'right'; dx?: number; dy?: number }
  | { t: 'key'; kind: 'down' | 'up'; key: string }
  | { t: 'text'; text: string }
  | { t: 'resize'; w: number; h: number }
  | { t: 'nav'; action: 'back' | 'forward' | 'reload' | 'goto'; url?: string }
  | { t: 'tab'; action: 'new' | 'switch' | 'close'; index?: number; url?: string }

export interface BrowserStream {
  send: (msg: StreamInput) => void
  close: () => void
}

export function browserStreamUrl(config: ApiConfig): string {
  return config.apiBaseUrl.replace(/^http/, 'ws').replace(/\/$/, '') + '/ws/browser'
}

export function openBrowserStream(
  config: ApiConfig,
  handlers: {
    onFrame: (jpeg: Blob) => void
    onTabs: (faner: StreamFane[]) => void
    onStatus: (status: 'open' | 'closed' | 'error') => void
  },
): BrowserStream {
  const url = browserStreamUrl(config)
  const token = (config.authToken || '').trim()
  const ws = token ? new WebSocket(url, [SUBPROTOKOL, token]) : new WebSocket(url)
  ws.binaryType = 'blob'
  ws.onopen = () => handlers.onStatus('open')
  ws.onclose = () => handlers.onStatus('closed')
  ws.onerror = () => handlers.onStatus('error')
  ws.onmessage = (ev: MessageEvent) => {
    if (typeof ev.data === 'string') {
      try {
        const m = JSON.parse(ev.data) as { type?: string; tabs?: StreamFane[] }
        if (m.type === 'tabs' && Array.isArray(m.tabs)) handlers.onTabs(m.tabs)
      } catch { /* ignorér ukendt tekst */ }
    } else if (ev.data instanceof Blob) {
      handlers.onFrame(ev.data)
    }
  }
  return {
    send: (msg) => { if (ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify(msg)) },
    close: () => ws.close(),
  }
}

/** Musekoordinat i canvas -> koordinat i sidens viewport (frame-pixels). */
export function tilSideKoord(
  clientX: number, clientY: number, rect: { left: number; top: number; width: number; height: number },
  frameW: number, frameH: number,
): { x: number; y: number } {
  const x = rect.width > 0 ? ((clientX - rect.left) / rect.width) * frameW : 0
  const y = rect.height > 0 ? ((clientY - rect.top) / rect.height) * frameH : 0
  return { x: Math.max(0, x), y: Math.max(0, y) }
}

const MUSEKNAP: Record<number, 'left' | 'middle' | 'right'> = { 0: 'left', 1: 'middle', 2: 'right' }
export const museKnap = (b: number): 'left' | 'middle' | 'right' => MUSEKNAP[b] ?? 'left'
