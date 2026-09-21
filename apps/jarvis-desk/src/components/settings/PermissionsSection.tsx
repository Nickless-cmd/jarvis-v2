import { useSettingsResource } from '../../hooks/useSettingsResource'
import { SettingsState, SettingsActionError } from './SettingsState'
import { useState } from 'react'
import type { ApiConfig } from '../../lib/api'
import { getAccountPermissions, setComputerUse } from '../../lib/coworkApi'

// Etiketten er «Work»; identifikatoren er fortsat `cowork` — den er et
// tool-scope i 22 backend-filer og i API-ruter, og et ord er ikke nok
// grund til at røre styringssystemet (6/9-2026).
const MODE_LABEL: Record<string, string> = { chat: 'Chat', code: 'Code', cowork: 'Arbejde' }

/** Permissions-sektion (§4.7). Viser tool-adgangs-matrix pr. mode (read-only) +
 *  håndhævet computer-use-toggle. */
export function PermissionsSection({ config }: { config: ApiConfig | undefined }) {
  const resource = useSettingsResource(config, getAccountPermissions)
  const data = resource.data
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const toggleCu = async () => {
    if (!config || !data || busy) return
    setBusy(true); setError('')
    try {
      await setComputerUse(config, !data.computer_use_enabled)
      resource.setData({ ...data, computer_use_enabled: !data.computer_use_enabled })
    } catch { setError('Tilladelsen kunne ikke ændres. Prøv igen.') }
    finally { setBusy(false) }
  }
  if (!data) return <SettingsState status={resource.status} label="tilladelser" onRetry={resource.retry} />

  return (
    <div className="settings-section permissions-section">
      <h3>Tilladelser <span className="badge badge-ok">{data.role}</span></h3>

      <SettingsActionError message={error} />
      <label className="cu-toggle">
        <input type="checkbox" aria-label="Computer-use" disabled={busy} checked={data.computer_use_enabled} onChange={() => void toggleCu()} />
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
