import { useCallback, useEffect, useState } from 'react'
import { ChevronRight, EyeOff, Eye, LogOut, Settings, RefreshCw } from 'lucide-react'
import { getAccountQuota, type QuotaOverview } from '../../lib/coworkApi'
import type { ApiConfig } from '../../lib/api'
import { useFigurVist } from '../../lib/figurVist'

const KVOTE_NAVN: Record<string, string> = {
  chat: 'Chat', code: 'Code · min', cowork: 'Cowork', agent: 'Agenter',
}
const TIER_NAVN: Record<string, string> = {
  owner: 'Owner', free: 'Free', plus: 'Plus', pro: 'Pro',
}

export function KontoMenu({ userName, role, config, onSettings, onLogout, onClose }: {
  userName: string
  role: 'owner' | 'member' | 'guest'
  config: ApiConfig | null
  onSettings: () => void
  onLogout: () => void
  onClose: () => void
}) {
  const [quota, setQuota] = useState<QuotaOverview | null>(null)
  const [fejl, setFejl] = useState(false)
  const [figurVist, saetFigur] = useFigurVist()

  const hent = useCallback(() => {
    if (!config) return
    void getAccountQuota(config)
      .then((data) => { setQuota(data); setFejl(false) })
      .catch(() => setFejl(true))
  }, [config])
  useEffect(() => { hent() }, [hent])

  const tier = quota?.tier || role
  return (
    <div className="sidebar-account-menu" role="menu" aria-label="Konto">
      <div className="sidebar-account-identity">
        <span className="sidebar-account-avatar">{userName.charAt(0).toUpperCase()}</span>
        <span><strong>{userName}</strong><small>{TIER_NAVN[tier] || tier}</small></span>
      </div>
      <div className="sidebar-account-divider" />
      <div className="sidebar-usage-head">
        <span>Usage <small>· i dag</small></span>
        <button type="button" className="sidebar-usage-refresh" aria-label="Opdater usage" onClick={hent}>
          <RefreshCw size={13} />
        </button>
      </div>
      {fejl ? (
        <div className="sidebar-usage-state" role="alert">Forbrug kunne ikke hentes.</div>
      ) : quota === null ? (
        <div className="sidebar-usage-state">Henter forbrug…</div>
      ) : (
        <div className="sidebar-usage-list">
          {quota.items.map((item) => {
            const unlimited = item.limit === null
            const percent = item.limit && item.limit > 0 ? Math.min(100, Math.round(item.used / item.limit * 100)) : 0
            return (
              <div className="sidebar-usage-item" key={item.kind}>
                <div className="sidebar-usage-line">
                  <span>{KVOTE_NAVN[item.kind] || item.kind}</span>
                  <span>{unlimited ? 'Ubegrænset' : `${item.used} / ${item.limit}`}</span>
                </div>
                {!unlimited && <div className="sidebar-usage-track"><span style={{ width: `${percent}%` }} /></div>}
              </div>
            )
          })}
        </div>
      )}
      <div className="sidebar-account-divider" />
      {figurVist !== null && (
        <button type="button" className="sidebar-account-action" onClick={() => saetFigur(!figurVist)}>
          {figurVist ? <EyeOff size={15} /> : <Eye size={15} />}
          {figurVist ? 'Skjul figur' : 'Vis figur'}
        </button>
      )}
      <button type="button" className="sidebar-account-action" onClick={() => { onSettings(); onClose() }}>
        <Settings size={15} /> Indstillinger <ChevronRight size={13} className="sidebar-account-chevron" />
      </button>
      <button type="button" className="sidebar-account-action sidebar-logout" onClick={() => { onLogout(); onClose() }}>
        <LogOut size={15} /> Log ud
      </button>
    </div>
  )
}
