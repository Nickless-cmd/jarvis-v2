import { useEffect, useMemo, useRef, useState } from 'react'
import type { ApiConfig } from '../../lib/tokenRenewal'
import {
  openDesktopStream, tilSkaermKoord, museKnap,
  type DesktopStream, type DesktopStatus,
} from '../../lib/desktopStream'
import { Monitor, X, Maximize2, Minimize2 } from 'lucide-react'

/**
 * Jarvis' egen Linux-desktop i en fane. Tegner JPEG-frames fra `/ws/desktop`
 * på et canvas og sender mus og tastatur tilbage. Viser en tydelig fejl-
 * tilstand når desktoppen ikke er tilgængelig (fx X-pakker mangler).
 */
export function DesktopPanel({ aaben, config, fuld = false, onFuld, onClose }: {
  aaben: boolean
  config?: ApiConfig | null
  fuld?: boolean
  onFuld?: (fuld: boolean) => void
  onClose?: () => void
}) {
  const apiBase = config?.apiBaseUrl
  const apiToken = config?.authToken ?? null
  // Primitiver, ikke objektet: ellers genåbnes streamen ved hver render.
  const cfg = useMemo<ApiConfig | null>(
    () => (apiBase ? { apiBaseUrl: apiBase, authToken: apiToken } : null),
    [apiBase, apiToken],
  )
  const canvas = useRef<HTMLCanvasElement | null>(null)
  const strom = useRef<DesktopStream | null>(null)
  const markor = useRef<HTMLDivElement | null>(null)
  const ramme = useRef({ w: 1280, h: 800 })
  const sidsteMus = useRef(0)
  const [status, setStatus] = useState<DesktopStatus | 'forbinder'>('forbinder')
  const [detalje, setDetalje] = useState('')

  useEffect(() => {
    if (!aaben || !cfg) return
    setStatus('forbinder')
    setDetalje('')
    let aktiv = true
    const s = openDesktopStream(cfg, {
      onFrame: (blob) => {
        void createImageBitmap(blob).then((bmp) => {
          const c = canvas.current
          if (!aktiv || !c) { bmp.close(); return }
          ramme.current = { w: bmp.width, h: bmp.height }
          if (c.width !== bmp.width) c.width = bmp.width
          if (c.height !== bmp.height) c.height = bmp.height
          c.getContext('2d')?.drawImage(bmp, 0, 0)
          bmp.close()
          setStatus((x) => (x === 'open' ? x : 'open'))
        }).catch(() => { /* ødelagt frame: spring over, næste kommer straks */ })
      },
      onStatus: (st, d) => { if (aktiv) { setStatus(st); setDetalje(d ?? '') } },
      onCursor: (x, y) => {
        const el = markor.current
        const { w, h } = ramme.current
        if (!aktiv || !el || !w || !h) return
        el.style.display = 'block'
        el.style.left = `${(x / w) * 100}%`
        el.style.top = `${(y / h) * 100}%`
      },
    })
    strom.current = s
    return () => { aktiv = false; s.close(); strom.current = null }
  }, [aaben, cfg])

  if (!aaben) return null

  const koord = (e: { clientX: number; clientY: number }) => {
    const c = canvas.current
    if (!c) return { x: 0, y: 0 }
    return tilSkaermKoord(e.clientX, e.clientY, c.getBoundingClientRect(), ramme.current.w, ramme.current.h)
  }

  const fejlTekst = status === 'unavailable'
    ? 'Desktop er ikke tilgængelig på serveren (X-pakker mangler eller kunne ikke starte).'
    : status === 'error' ? 'Forbindelsen til desktoppen fejlede.'
    : status === 'closed' ? 'Forbindelsen til desktoppen blev lukket.' : ''

  return (
    <div className={`code-panel desktop-panel${fuld ? ' er-fuld' : ''}`} data-testid="desktop-panel">
      <div className="code-panel-head">
        <Monitor size={14} />
        <span>Desktop</span>
        <span style={{ flex: 1 }} />
        {onFuld && (
          <button type="button" className="icon-btn" aria-label={fuld ? 'Gendan størrelse' : 'Fuld visning'}
            onClick={() => onFuld(!fuld)}>
            {fuld ? <Minimize2 size={14} /> : <Maximize2 size={14} />}
          </button>
        )}
        {onClose && (
          <button type="button" className="icon-btn" aria-label="Luk desktop" onClick={onClose}>
            <X size={14} />
          </button>
        )}
      </div>
      {!cfg && <div role="alert" className="desktop-fejl">Ingen API-forbindelse — kan ikke åbne desktop.</div>}
      {cfg && fejlTekst && (
        <div role="alert" className="desktop-fejl">
          {fejlTekst}{detalje ? ` (${detalje})` : ''}
        </div>
      )}
      {cfg && status === 'forbinder' && <div className="desktop-info">Forbinder til desktop…</div>}
      <div style={{ position: 'relative', display: fejlTekst ? 'none' : 'block' }}>
        <canvas
          ref={canvas}
          tabIndex={0}
          aria-label="Jarvis' desktop"
          style={{ width: '100%', display: 'block', outline: 'none', background: '#000' }}
          onContextMenu={(e) => e.preventDefault()}
          onMouseMove={(e) => {
            const nu = Date.now()
            if (nu - sidsteMus.current < 50) return
            sidsteMus.current = nu
            strom.current?.send({ t: 'mouse', kind: 'move', ...koord(e) })
          }}
          onMouseDown={(e) => {
            e.currentTarget.focus()
            strom.current?.send({ t: 'mouse', kind: 'down', button: museKnap(e.button), ...koord(e) })
          }}
          onMouseUp={(e) => strom.current?.send({ t: 'mouse', kind: 'up', button: museKnap(e.button), ...koord(e) })}
          onWheel={(e) => strom.current?.send({ t: 'mouse', kind: 'wheel', dx: e.deltaX, dy: e.deltaY, ...koord(e) })}
          onKeyDown={(e) => {
            e.preventDefault()
            // Et TEGN sendes som tekst, ikke som tastetryk: så virker shift,
            // store bogstaver og symboler, fordi browseren allerede har dannet
            // det rigtige tegn. Kun styretasterne går den anden vej.
            if (e.key.length === 1 && !e.ctrlKey && !e.metaKey && !e.altKey) {
              strom.current?.send({ t: 'text', text: e.key })
              return
            }
            strom.current?.send({ t: 'key', kind: 'down', key: e.key })
          }}
          onKeyUp={(e) => {
            e.preventDefault()
            if (e.key.length === 1 && !e.ctrlKey && !e.metaKey && !e.altKey) return
            strom.current?.send({ t: 'key', kind: 'up', key: e.key })
          }}
        />
        {/* Markøren ligger ikke i JPEG-framen — den tegnes her, så man kan se
            hvor man peger. */}
        <div
          ref={markor}
          aria-hidden="true"
          style={{ position: 'absolute', left: 0, top: 0, transform: 'translate(-2px,-1px)', pointerEvents: 'none', display: 'none' }}
        >
          <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
            <path d="M2 2 L2 14.5 L5.6 10.9 L8.1 16 L10.6 15 L8.1 9.9 L13.2 9.9 Z"
              fill="#fff" stroke="#000" strokeWidth="1.2" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
    </div>
  )
}
