import { useEffect, useState } from 'react'
import { Download, X, RotateCw, AlertCircle, CheckCircle2 } from 'lucide-react'
import type { UpdaterStatus } from '../types'

/**
 * Top banner that surfaces auto-updater state. Hidden when nothing's
 * happening; appears when:
 *
 *   - update is available     → "Download X.Y.Z" button
 *   - downloading             → progress bar
 *   - downloaded, ready to go → "Install and restart" button
 *   - error                   → error message + "Try again"
 *
 * "not-available" / "checking" / "idle" produce no banner — those
 * states are normal and don't warrant the user's attention.
 *
 * Why a banner vs a notification: an Electron-native notification
 * fires once and the user can miss it. A banner that sits above the
 * chat persists until acknowledged or until the install fires. It
 * also gives us a place to put the progress bar during download.
 *
 * Skip-state is per-version: dismissing means "not this version".
 * If a newer version arrives, the banner returns. We persist via
 * localStorage so reload doesn't undo dismissal.
 */
export function UpdateBanner() {
  const [status, setStatus] = useState<UpdaterStatus>({ kind: 'idle' })
  const [dismissedVersion, setDismissedVersion] = useState<string | null>(() =>
    localStorage.getItem('jarvisx:dismissed-update-version'),
  )

  useEffect(() => {
    if (!window.jarvisx) return
    // Initial state pull + subscribe to updates
    window.jarvisx.updaterStatus().then(setStatus).catch(() => undefined)
    const off = window.jarvisx.onUpdaterStatus(setStatus)
    return off
  }, [])

  if (!window.jarvisx) return null

  const dismiss = () => {
    if (status.kind === 'available' || status.kind === 'downloaded') {
      const v = status.info.version
      localStorage.setItem('jarvisx:dismissed-update-version', v)
      setDismissedVersion(v)
    }
  }

  const isDismissed =
    (status.kind === 'available' || status.kind === 'downloaded') &&
    dismissedVersion === status.info.version

  if (
    status.kind === 'idle' ||
    status.kind === 'checking' ||
    status.kind === 'not-available' ||
    isDismissed
  ) {
    return null
  }

  if (status.kind === 'available') {
    return (
      <Banner
        tone="info"
        icon={<Download size={12} />}
        message={`Ny version ${status.info.version} tilgængelig`}
        actions={
          <>
            <button
              onClick={() => window.jarvisx?.updaterDownload()}
              className="rounded bg-accent px-3 py-1 text-[11px] font-semibold text-bg0 hover:bg-accent/90"
            >
              Download
            </button>
            <button
              onClick={dismiss}
              className="flex h-5 w-5 items-center justify-center rounded text-fg3 hover:text-fg"
              title="Skjul indtil næste version"
            >
              <X size={11} />
            </button>
          </>
        }
      />
    )
  }

  if (status.kind === 'downloading') {
    return (
      <Banner
        tone="info"
        icon={<Download size={12} className="animate-pulse" />}
        message={`Henter opdatering · ${status.percent}%`}
        progress={status.percent}
      />
    )
  }

  if (status.kind === 'downloaded') {
    return (
      <Banner
        tone="success"
        icon={<CheckCircle2 size={12} />}
        message={`${status.info.version} klar — genstart for at installere`}
        actions={
          <>
            <button
              onClick={() => window.jarvisx?.updaterInstall()}
              className="rounded bg-ok px-3 py-1 text-[11px] font-semibold text-bg0 hover:bg-ok/90"
            >
              Install og genstart
            </button>
            <button
              onClick={dismiss}
              className="flex h-5 w-5 items-center justify-center rounded text-fg3 hover:text-fg"
              title="Vent — installér ved næste app-quit"
            >
              <X size={11} />
            </button>
          </>
        }
      />
    )
  }

  if (status.kind === 'error') {
    return (
      <Banner
        tone="danger"
        icon={<AlertCircle size={12} />}
        message={`Update-fejl: ${status.error}`}
        actions={
          <button
            onClick={() => window.jarvisx?.updaterCheck()}
            className="flex items-center gap-1 rounded border border-line2 bg-bg2 px-2 py-1 text-[10px] text-fg2 hover:text-fg"
          >
            <RotateCw size={10} /> Prøv igen
          </button>
        }
      />
    )
  }

  return null
}

function Banner({
  tone,
  icon,
  message,
  actions,
  progress,
}: {
  tone: 'info' | 'success' | 'danger'
  icon: React.ReactNode
  message: string
  actions?: React.ReactNode
  progress?: number
}) {
  const palette = {
    info: 'border-accent/30 bg-accent/10 text-accent',
    success: 'border-ok/30 bg-ok/10 text-ok',
    danger: 'border-danger/30 bg-danger/10 text-danger',
  }[tone]
  return (
    <div
      className={[
        'relative flex flex-shrink-0 items-center gap-3 border-b px-4 py-1.5 text-[11px]',
        palette,
      ].join(' ')}
    >
      <span className="flex flex-shrink-0 items-center gap-1.5 font-semibold">
        {icon}
        {message}
      </span>
      <div className="flex-1" />
      {actions && <div className="flex flex-shrink-0 items-center gap-2">{actions}</div>}
      {typeof progress === 'number' && (
        <div className="absolute bottom-0 left-0 h-0.5 bg-accent transition-all" style={{ width: `${progress}%` }} />
      )}
    </div>
  )
}
