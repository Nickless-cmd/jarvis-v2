import { useState } from 'react'
import type { ApiConfig } from '../../lib/api'
import { getCentralRealtime } from '../../lib/api'
import { usePollWhenVisible } from '../../hooks/usePollWhenVisible'

/** Kompakt Central-status-mærke: farvet prik + "Central" + evt. incident-tæller.
 *  Synligt for ALLE roller (erstatter de tunge owner-only Central-paneler).
 *  Hover: minimal status for members, detaljerede metrics for owner.
 *  Klik (kun owner): åbner `central`-CLI'en i et rigtigt OS-terminalvindue. */
export function CentralBadge({ config, isOwner }: { config?: ApiConfig; isOwner?: boolean }) {
  // usePollWhenVisible sluger fejl (403 for ikke-ejere / offline) → data forbliver null.
  const { data: snap, error } = usePollWhenVisible(() => getCentralRealtime(config!), 8000, !!config)
  const [hover, setHover] = useState(false)
  const [opening, setOpening] = useState(false)

  // Neutral grå tilstand når vi ikke har data (ukendt / offline / ingen adgang).
  const known = !!snap
  const status = snap?.status ?? 'unknown'
  const tone = status === 'green' ? 'green' : status === 'yellow' ? 'yellow' : status === 'red' ? 'red' : 'unknown'
  const incidents = snap?.incidents ?? []
  const cov = snap?.coverage ?? {}
  const breakers = snap?.open_breakers ?? []

  const statusWord = !known
    ? (error ? 'offline' : 'ukendt')
    : status === 'green' ? 'alt vel'
    : status === 'yellow' ? 'opmærksomhed'
    : 'incidents'

  const onClick = async () => {
    if (!isOwner || opening) return
    const bridge = (window as unknown as { jarvisDesk?: { central?: { openCli?: () => Promise<{ ok: boolean; error?: string }> } } }).jarvisDesk
    const open = bridge?.central?.openCli
    if (!open) return  // ikke i Electron / bro utilgængelig → no-op
    setOpening(true)
    try { await open() } catch { /* stille — brugeren ser blot at intet skete */ }
    finally { setTimeout(() => setOpening(false), 1200) }
  }

  const top = incidents[0]
  const detail = isOwner
    ? `nerver ${cov.nerves ?? 0} · clusters ${cov.clusters ?? 0} · incidents ${incidents.length} · breakers ${breakers.length}`
      + (top ? ` — ${top.cluster}/${top.nerve}` : '')
    : `Central: ${statusWord}`

  const titleAttr = isOwner ? `Central — ${detail} (klik: åbn CLI)` : `Central: ${statusWord}`

  return (
    <div
      className={`central-badge tone-${tone}${isOwner ? ' owner' : ''}`}
      title={titleAttr}
      role={isOwner ? 'button' : undefined}
      tabIndex={isOwner ? 0 : undefined}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      onClick={onClick}
      onKeyDown={isOwner ? (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); void onClick() } } : undefined}
      data-testid="central-badge"
    >
      <span className="cb-dot" />
      <span className="cb-label">Central</span>
      {incidents.length > 0 && <span className="cb-count">{incidents.length}</span>}
      {opening && <span className="cb-opening">åbner…</span>}
      {hover && (
        <div className="cb-pop" role="tooltip">{detail}</div>
      )}
    </div>
  )
}
