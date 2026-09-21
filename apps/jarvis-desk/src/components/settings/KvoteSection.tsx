import { useSettingsResource } from '../../hooks/useSettingsResource'
import { SettingsState } from './SettingsState'
import type { ApiConfig } from '../../lib/api'
import { getAccountQuota, type QuotaItem } from '../../lib/coworkApi'

const LABELS: Record<QuotaItem['kind'], string> = {
  chat: 'Chat-beskeder',
  code: 'Code-minutter',
  cowork: 'Godkendelser i Arbejde',
  agent: 'Agentopgaver',
}

export function KvoteSection({ config }: { config: ApiConfig | undefined }) {
  const resource = useSettingsResource(config, getAccountQuota)
  const data = resource.data

  if (!data) return <SettingsState status={resource.status} label="kvoten" onRetry={resource.retry} />

  return (
    <div className="settings-section kvote-section">
      <h3>Kvote <span className="badge badge-ok">{data.tier}</span></h3>
      <div className="quota-list">
        {data.items.map((it) => {
          const unlimited = it.limit == null
          const pct = unlimited || !it.limit ? 0 : Math.min(100, Math.round((it.used / it.limit) * 100))
          return (
            <div key={it.kind} className={`quota-row${it.warn ? ' warn' : ''}`}>
              <div className="quota-head">
                <span>{LABELS[it.kind]}</span>
                <span className="quota-num">{unlimited ? 'ubegrænset' : `${it.used} / ${it.limit}`}</span>
              </div>
              {!unlimited && (
                <div className="quota-bar"><div className="quota-fill" style={{ width: `${pct}%` }} /></div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
