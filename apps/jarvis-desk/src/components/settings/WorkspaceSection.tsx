import { useEffect, useState } from 'react'
import type { ApiConfig } from '../../lib/api'
import { getAccountWorkspace, type WorkspaceOverview } from '../../lib/coworkApi'

function humanBytes(n: number): string {
  if (n < 1024) return `${n} B`
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`
  if (n < 1024 * 1024 * 1024) return `${(n / (1024 * 1024)).toFixed(1)} MB`
  return `${(n / (1024 * 1024 * 1024)).toFixed(1)} GB`
}

/** Workspace-sektion (§4.8). Self-scope: brugerens eget workspace. */
export function WorkspaceSection({ config }: { config: ApiConfig | undefined }) {
  const [data, setData] = useState<WorkspaceOverview | null>(null)
  const [error, setError] = useState(false)

  useEffect(() => {
    if (!config) return
    let alive = true
    getAccountWorkspace(config)
      .then((d) => { if (alive) setData(d) })
      .catch(() => { if (alive) setError(true) })
    return () => { alive = false }
  }, [config?.apiBaseUrl, config?.authToken])

  if (error) return <div className="settings-section">Kunne ikke hente workspace.</div>
  if (!data) return <div className="settings-section">Indlæser workspace…</div>

  return (
    <div className="settings-section workspace-section">
      <h3>Workspace</h3>
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
