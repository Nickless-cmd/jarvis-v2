import { useEffect, useState } from 'react'
import { createPortal } from 'react-dom'
import { Monitor, AppWindow, X, Camera, AlertCircle } from 'lucide-react'
import {
  captureSourceAsBlob,
  listSources,
  type ScreenSource,
} from '../lib/screenCapture'

interface Props {
  apiBaseUrl: string
  onCaptured: (attachment: { url: string; filename: string }) => void
  onClose: () => void
}

/**
 * Modal that shows all screens + windows with their thumbnails.
 * Click → grabs a single frame → uploads to /attachments/upload →
 * fires onCaptured with the resulting attachment ref.
 *
 * The caller is responsible for inserting the attachment into the
 * composer — we don't reach into composer state from here.
 */
export function ScreenCaptureModal({ apiBaseUrl, onCaptured, onClose }: Props) {
  const [sources, setSources] = useState<ScreenSource[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busyId, setBusyId] = useState<string | null>(null)

  useEffect(() => {
    listSources()
      .then(setSources)
      .catch((e) => setError(e instanceof Error ? e.message : String(e)))
  }, [])

  const handlePick = async (s: ScreenSource) => {
    setBusyId(s.id)
    setError(null)
    try {
      const blob = await captureSourceAsBlob(s.id)
      const filename = `screen-${s.name.replace(/[^\w-]+/g, '_').slice(0, 40)}-${Date.now()}.png`
      const form = new FormData()
      form.append('file', blob, filename)
      const res = await fetch(`${apiBaseUrl.replace(/\/$/, '')}/attachments/upload`, {
        method: 'POST',
        body: form,
      })
      if (!res.ok) throw new Error(`upload failed: HTTP ${res.status}`)
      const j = await res.json()
      const url = j.url || j.attachment?.url
      if (!url) throw new Error('upload response missing url')
      onCaptured({ url, filename })
      onClose()
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setBusyId(null)
    }
  }

  const screens = (sources ?? []).filter((s) => s.id.startsWith('screen:'))
  const windows = (sources ?? []).filter((s) => !s.id.startsWith('screen:'))

  return createPortal(
    <div
      style={{
        position: 'fixed',
        inset: 0,
        background: 'rgba(0,0,0,.7)',
        zIndex: 10000,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
      }}
      onClick={onClose}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className="flex max-h-[85vh] w-[820px] max-w-[95vw] flex-col rounded-lg border border-line2 bg-bg1 shadow-2xl"
      >
        <header className="flex flex-shrink-0 items-center justify-between border-b border-line px-4 py-3">
          <div className="flex items-center gap-2">
            <Camera size={14} className="text-accent" />
            <h2 className="text-sm font-semibold">Capture screen or window</h2>
          </div>
          <button
            onClick={onClose}
            className="flex h-7 w-7 items-center justify-center rounded text-fg3 hover:bg-bg2 hover:text-fg"
          >
            <X size={14} />
          </button>
        </header>

        <div className="min-h-0 flex-1 overflow-y-auto px-4 py-3">
          {error && (
            <div className="mb-3 flex items-center gap-2 rounded-md border border-danger/30 bg-danger/10 px-3 py-2 text-[11px] text-danger">
              <AlertCircle size={12} />
              {error}
            </div>
          )}
          {!sources && !error && (
            <div className="text-xs text-fg3">loading sources…</div>
          )}
          {sources && sources.length === 0 && !error && (
            <div className="text-xs text-fg3">No screens or windows found.</div>
          )}

          {screens.length > 0 && (
            <Section
              title="Screens"
              Icon={Monitor}
              items={screens}
              busyId={busyId}
              onPick={handlePick}
            />
          )}
          {windows.length > 0 && (
            <Section
              title="Windows"
              Icon={AppWindow}
              items={windows}
              busyId={busyId}
              onPick={handlePick}
            />
          )}
        </div>

        <footer className="flex-shrink-0 border-t border-line/60 bg-bg1/40 px-4 py-2 text-[10px] text-fg3">
          Captured frame attaches as an image to your next message.
        </footer>
      </div>
    </div>,
    document.body,
  )
}

function Section({
  title,
  Icon,
  items,
  busyId,
  onPick,
}: {
  title: string
  Icon: typeof Monitor
  items: ScreenSource[]
  busyId: string | null
  onPick: (s: ScreenSource) => void
}) {
  return (
    <div className="mb-4">
      <div className="mb-2 flex items-center gap-2">
        <Icon size={11} className="text-fg3" />
        <span className="text-[10px] font-semibold uppercase tracking-wider text-fg3">
          {title} · {items.length}
        </span>
      </div>
      <div className="grid grid-cols-2 gap-2 md:grid-cols-3">
        {items.map((s) => (
          <button
            key={s.id}
            disabled={busyId !== null}
            onClick={() => onPick(s)}
            className={[
              'group flex flex-col overflow-hidden rounded border border-line bg-bg2 transition-all',
              busyId === s.id
                ? 'animate-pulse ring-2 ring-accent'
                : 'hover:border-accent/40 hover:ring-1 hover:ring-accent/30',
              busyId !== null && busyId !== s.id ? 'opacity-40' : '',
            ].join(' ')}
          >
            <img
              src={s.thumbnail}
              alt={s.name}
              className="h-32 w-full object-contain bg-bg0"
            />
            <div className="truncate border-t border-line/60 px-2 py-1.5 text-left text-[11px] text-fg2 group-hover:text-fg">
              {s.name}
            </div>
          </button>
        ))}
      </div>
    </div>
  )
}
