import { useSettingsResource } from '../../hooks/useSettingsResource'
import { SettingsState } from './SettingsState'
import type { ApiConfig } from '../../lib/api'
import { getAccountWorkspace } from '../../lib/coworkApi'

function humanBytes(n: number): string {
  if (n < 1024) return `${n} B`
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`
  if (n < 1024 * 1024 * 1024) return `${(n / (1024 * 1024)).toFixed(1)} MB`
  return `${(n / (1024 * 1024 * 1024)).toFixed(1)} GB`
}

/** Workspace-sektion (§4.8). Self-scope: brugerens eget workspace. */
export function WorkspaceSection({ config }: { config: ApiConfig | undefined }) {
  const resource = useSettingsResource(config, getAccountWorkspace)
  const data = resource.data

  if (!data) return <SettingsState status={resource.status} label="arbejdsområdet" onRetry={resource.retry} />

  return (
    <div className="settings-section workspace-section">
      <h3>Dit arbejdsområde</h3>
      <dl className="account-fields">
        <dt>Mappe</dt><dd>{data.path_name}</dd>
        <dt>Filer</dt><dd>{data.files}</dd>
        <dt>Disk-forbrug</dt><dd>{humanBytes(data.disk_bytes)}</dd>
        <dt>Kryptering</dt>
        <dd>{data.encrypted
          ? <span className="badge badge-ok">krypteret</span>
          : <span className="badge badge-warn">ukrypteret</span>}</dd>
        <dt>Tillid</dt>
        <dd>{data.trusted
          ? <span className="badge badge-ok">betroet</span>
          : <span className="badge badge-warn">ikke betroet</span>}</dd>
      </dl>
    </div>
  )
}
