import { useEffect, useState } from 'react'
import type { ApiConfig } from '../../lib/api'
import { getAccountMe, type AccountProfile } from '../../lib/coworkApi'

/** Account-sektion (cowork command center §4.1). Viser den aktuelle brugers
 *  egen profil — henter via /account/me (self-scope, ikke owner-only). */
export function AccountSection({ config }: { config: ApiConfig | undefined }) {
  const [profile, setProfile] = useState<AccountProfile | null>(null)
  const [error, setError] = useState(false)

  useEffect(() => {
    if (!config) return
    let alive = true
    getAccountMe(config)
      .then((p) => { if (alive) setProfile(p) })
      .catch(() => { if (alive) setError(true) })
    return () => { alive = false }
  }, [config?.apiBaseUrl, config?.authToken])

  if (error) return <div className="settings-section">Kunne ikke hente kontoen.</div>
  if (!profile) return <div className="settings-section">Indlæser konto…</div>

  return (
    <div className="settings-section account-section">
      <h3>Konto</h3>
      <dl className="account-fields">
        <dt>Email</dt>
        <dd>
          {profile.email || '–'}{' '}
          {profile.email
            ? (profile.email_verified
                ? <span className="badge badge-ok">verificeret ✓</span>
                : <span className="badge badge-warn">ikke verificeret</span>)
            : null}
        </dd>
        <dt>Sprog</dt><dd>{profile.language}</dd>
        <dt>Rolle</dt><dd>{profile.role}</dd>
        <dt>Tier</dt><dd>{profile.tier}</dd>
      </dl>
    </div>
  )
}
