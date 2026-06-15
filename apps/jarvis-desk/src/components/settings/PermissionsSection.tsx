import { useEffect, useState } from 'react'
import type { ApiConfig } from '../../lib/api'
import { getAccountPermissions, setComputerUse, type PermissionsOverview } from '../../lib/coworkApi'

const MODE_LABEL: Record<string, string> = { chat: 'Chat', code: 'Code', cowork: 'Cowork' }

/** Permissions-sektion (§4.7). Viser tool-adgangs-matrix pr. mode (read-only) +
 *  håndhævet computer-use-toggle. */
export function PermissionsSection({ config }: { config: ApiConfig | undefined }) {
  const [data, setData] = useState<PermissionsOverview | null>(null)
  const [error, setError] = useState(false)

  useEffect(() => {
    if (!config) return
    let alive = true
    getAccountPermissions(config)
      .then((d) => { if (alive) setData(d) })
      .catch(() => { if (alive) setError(true) })
    return () => { alive = false }
  }, [config?.apiBaseUrl, config?.authToken])

  const toggleCu = async () => {
    if (!config || !data) return
    const next = !data.computer_use_enabled
    setData({ ...data, computer_use_enabled: next })
    await setComputerUse(config, next)
  }

  if (error) return <div className="settings-section">Kunne ikke hente tilladelser.</div>
  if (!data) return <div className="settings-section">Indlæser tilladelser…</div>

  return (
    <div className="settings-section permissions-section">
      <h3>Tilladelser <span className="badge badge-ok">{data.role}</span></h3>

      <label className="cu-toggle">
        <input type="checkbox" aria-label="Computer-use" checked={data.computer_use_enabled} onChange={() => void toggleCu()} />
        <span>Computer-use (operator/skærm/bash på maskinen)</span>
      </label>

      <div className="perm-modes">
        {data.modes.map((m) => (
          <div key={m.mode} className="perm-mode">
            <div className="perm-mode-head">{MODE_LABEL[m.mode] ?? m.mode}</div>
            {m.all
              ? <div className="perm-all">Alle værktøjer</div>
              : <div className="perm-tools">{m.tools.map((t) => <span key={t} className="perm-tool">{t}</span>)}</div>}
          </div>
        ))}
      </div>
    </div>
  )
}
