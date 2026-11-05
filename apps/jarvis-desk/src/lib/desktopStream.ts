/**
 * Klient til `/ws/desktop` — Jarvis' Linux-desktop som JPEG-frames.
 *
 * Spejler browserStream.ts. Subprotokol-navnet er det samme som
 * `core/runtime/ws_auth.SUBPROTOKOL`.
 */
import type { ApiConfig } from './tokenRenewal'

const SUBPROTOKOL = 'jarvis-bearer'

export type DesktopInput =
  | { t: 'mouse'; kind: 'move' | 'down' | 'up' | 'wheel'; x: number; y: number; button?: 'left' | 'middle' | 'right'; dx?: number; dy?: number }
  | { t: 'key'; kind: 'down' | 'up'; key: string }
  | { t: 'text'; text: string }

export type DesktopStatus = 'open' | 'closed' | 'error' | 'unavailable'

export interface DesktopStream {
  send: (msg: DesktopInput) => void
  close: () => void
}

export function desktopStreamUrl(config: ApiConfig): string {
  return config.apiBaseUrl.replace(/^http/, 'ws').replace(/\/$/, '') + '/ws/desktop'
}

export function openDesktopStream(
  config: ApiConfig,
  handlers: {
    onFrame: (jpeg: Blob) => void
    onStatus: (status: DesktopStatus, detalje?: string) => void
    /** Markørens position i skærm-pixels. Den er ikke i JPEG-framen. */
    onCursor?: (x: number, y: number) => void
  },
): DesktopStream {
  const url = desktopStreamUrl(config)
  const token = (config.authToken || '').trim()
  const ws = token ? new WebSocket(url, [SUBPROTOKOL, token]) : new WebSocket(url)
  ws.binaryType = 'blob'
  ws.onopen = () => handlers.onStatus('open')
  ws.onclose = (ev: CloseEvent) => {
    if (ev.reason === 'desktop_unavailable') handlers.onStatus('unavailable')
    else handlers.onStatus('closed', ev.reason || undefined)
  }
  ws.onerror = () => handlers.onStatus('error')
  ws.onmessage = (ev: MessageEvent) => {
    if (typeof ev.data === 'string') {
      try {
        const m = JSON.parse(ev.data) as { type?: string; code?: string; error?: string; x?: number; y?: number }
        if (m.type === 'error') {
          handlers.onStatus(m.code === 'DESKTOP_UNAVAILABLE' ? 'unavailable' : 'error', m.error)
        } else if (m.type === 'cursor' && typeof m.x === 'number' && typeof m.y === 'number') {
          handlers.onCursor?.(m.x, m.y)
        }
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

/** Musekoordinat i canvas -> koordinat i desktoppens frame-pixels. */
export function tilSkaermKoord(
  clientX: number, clientY: number, rect: { left: number; top: number; width: number; height: number },
  frameW: number, frameH: number,
): { x: number; y: number } {
  const x = rect.width > 0 ? ((clientX - rect.left) / rect.width) * frameW : 0
  const y = rect.height > 0 ? ((clientY - rect.top) / rect.height) * frameH : 0
  return { x: Math.max(0, x), y: Math.max(0, y) }
}

const MUSEKNAP: Record<number, 'left' | 'middle' | 'right'> = { 0: 'left', 1: 'middle', 2: 'right' }
export const museKnap = (b: number): 'left' | 'middle' | 'right' => MUSEKNAP[b] ?? 'left'
