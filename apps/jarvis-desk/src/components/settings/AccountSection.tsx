import { useEffect, useRef, useState } from 'react'
import type { ApiConfig } from '../../lib/api'
import { googleLinkStart, googleLoginResult } from '../../lib/api'
import { getAccountMe, type AccountProfile } from '../../lib/coworkApi'

function openBrowser(url: string): void {
  const b = (window as unknown as { jarvisDesk?: { openExternal?: (u: string) => Promise<void> } }).jarvisDesk
  void b?.openExternal?.(url)
}

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

  const [gBusy, setGBusy] = useState(false)
  const [gMsg, setGMsg] = useState('')
  const cancelRef = useRef(false)
  const linkGoogle = async () => {
    if (!config || gBusy) return
    setGBusy(true); setGMsg('Åbner Google…'); cancelRef.current = false
    try {
      const start = await googleLinkStart(config)
      if (!start.authorize_url || !start.nonce) { setGMsg('Ikke konfigureret.'); setGBusy(false); return }
      openBrowser(start.authorize_url)
      setGMsg('Godkend i browseren — venter…')
      for (let i = 0; i < 75 && !cancelRef.current; i++) {
        await new Promise((r) => setTimeout(r, 2000))
        const res = await googleLoginResult(config.apiBaseUrl, start.nonce)
          .catch((): Awaited<ReturnType<typeof googleLoginResult>> => ({ status: 'pending' }))
        if (res.status === 'ok') { setGMsg('Google-konto forbundet ✓'); setGBusy(false); return }
        if (res.status === 'error') { setGMsg('Kunne ikke forbinde.'); setGBusy(false); return }
      }
      setGMsg('Timeout — prøv igen.'); setGBusy(false)
    } catch { setGMsg('Kunne ikke nå serveren.'); setGBusy(false) }
  }

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
      <div className="account-google">
        <button type="button" className="account-google-btn" onClick={linkGoogle} disabled={gBusy}>
          {gBusy ? 'Forbinder…' : 'Forbind Google-konto'}
        </button>
        <p className="account-google-hint">Så kan du logge ind med Google fremover.</p>
        {gMsg && <p className="account-google-msg">{gMsg}</p>}
      </div>
    </div>
  )
}
