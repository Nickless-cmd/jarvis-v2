import { useSettingsResource } from '../../hooks/useSettingsResource'
import { SettingsState } from './SettingsState'
import { useEffect, useRef, useState } from 'react'
import type { ApiConfig } from '../../lib/api'
import { googleLinkStart, googleLoginResult } from '../../lib/api'
import { EnhederSection } from './EnhederSection'
import { getAccountMe } from '../../lib/coworkApi'

function openBrowser(url: string): void {
  const b = (window as unknown as { jarvisDesk?: { openExternal?: (u: string) => Promise<void> } }).jarvisDesk
  void b?.openExternal?.(url)
}

/** Account-sektion (cowork command center §4.1). Viser den aktuelle brugers
 *  egen profil — henter via /account/me (self-scope, ikke owner-only). */
export function AccountSection({ config }: { config: ApiConfig | undefined }) {
  const resource = useSettingsResource(config, getAccountMe)
  const profile = resource.data

  const [gBusy, setGBusy] = useState(false)
  const [gMsg, setGMsg] = useState('')
  const [linked, setLinked] = useState(false)
  const cancelRef = useRef(false)
  // Vedvarende indikator: server-sandheden (/account/me → google_linked).
  // Uden denne nulstilles knappen til "Forbind Google" ved hver genstart,
  // selvom kontoen ER linket — det fik det til at ligne et glemt login.
  useEffect(() => { if (profile) setLinked(!!profile.google_linked) }, [profile])
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
        if (res.status === 'ok') { setGMsg('Google-konto forbundet ✓'); setLinked(true); setGBusy(false); return }
        if (res.status === 'error') { setGMsg('Kunne ikke forbinde.'); setGBusy(false); return }
      }
      setGMsg('Timeout — prøv igen.'); setGBusy(false)
    } catch { setGMsg('Kunne ikke nå serveren.'); setGBusy(false) }
  }

  if (!profile) return <SettingsState status={resource.status} label="kontoen" onRetry={resource.retry} />

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
        <dt>Sprog</dt><dd>{{ da: 'Dansk', en: 'Engelsk' }[profile.language] ?? profile.language}</dd>
        <dt>Rolle</dt><dd>{{ owner: 'Ejer', member: 'Medlem', guest: 'Gæst' }[profile.role] ?? profile.role}</dd>
        <dt>Kontotype</dt><dd>{profile.tier}</dd>
      </dl>
      <div className="account-google">
        {linked ? (
          <>
            <p className="account-google-msg"><span className="badge badge-ok">Google forbundet ✓</span></p>
            <p className="account-google-hint">Du kan logge ind med Google. (Maks. én konto pr. bruger.)</p>
          </>
        ) : (
          <>
            <button type="button" className="account-google-btn" onClick={linkGoogle} disabled={gBusy}>
              {gBusy ? 'Forbinder…' : 'Forbind Google-konto'}
            </button>
            <p className="account-google-hint">Så kan du logge ind med Google fremover.</p>
          </>
        )}
        {gMsg && <p className="account-google-msg">{gMsg}</p>}
      </div>

      {/* Enheder: parring (tillad + totrinskode FØR QR), listen med «Fjern»,
          og reglen «code mode kræver en tilføjet enhed» (19/9-2026). */}
      {config ? <EnhederSection config={config} ejer={profile.role === 'owner'} /> : null}
    </div>
  )
}
