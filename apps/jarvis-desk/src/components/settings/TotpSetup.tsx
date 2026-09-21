import { useSettingsResource } from '../../hooks/useSettingsResource'
import { SettingsState, SettingsActionError } from './SettingsState'
import { useEffect, useState } from 'react'
import QRCode from 'qrcode'
import type { ApiConfig } from '../../lib/api'
import {
  getTotpStatus, setupTotp, revokeTotp,
  type TotpSetupResult,
} from '../../lib/totpApi'

/**
 * Owner-override 2FA-opsætning (spec §6.2). Genererer en TOTP-nøgle, viser QR
 * (renderet LOKALT — secret forlader aldrig maskinen) + secret til manuel
 * indtastning. Owner scanner ind i sin authenticator; derefter virker
 * `!override <kode>` fra fremmede sessioner. Bagdøren = kill-switch (§6.0).
 */
export function TotpSetup({ config }: { config: ApiConfig | undefined }) {
  const resource = useSettingsResource(config, getTotpStatus)
  const configured = resource.data?.configured
  const account = resource.data?.account
  const [error, setError] = useState('')
  const [setup, setSetup] = useState<TotpSetupResult | null>(null)
  const [qrDataUrl, setQrDataUrl] = useState('')
  const [busy, setBusy] = useState(false)

  // Render QR lokalt når et nyt setup-resultat kommer.
  useEffect(() => {
    if (!setup) { setQrDataUrl(''); return }
    void QRCode.toDataURL(setup.provisioning_uri, { width: 220, margin: 1 })
      .then(setQrDataUrl)
      .catch(() => setQrDataUrl(''))
  }, [setup])

  const doSetup = async () => {
    if (!config) return
    setBusy(true); setError('')
    try {
      const res = await setupTotp(config)
      setSetup(res)
      resource.retry()
    } catch { setError('Totrinsbekræftelsen kunne ikke ændres. Prøv igen.') } finally { setBusy(false) }
  }

  const doRevoke = async () => {
    if (!config) return
    setBusy(true); setError('')
    try {
      await revokeTotp(config)
      setSetup(null)
      resource.retry()
    } catch { setError('Totrinsbekræftelsen kunne ikke ændres. Prøv igen.') } finally { setBusy(false) }
  }

  return (
    <div className="totp-setup">
      <h3>Totrinsbekræftelse for ejeren</h3>
      <SettingsState status={resource.status} label="totrinsbekræftelse" onRetry={resource.retry} />
      <SettingsActionError message={error} />
      <p className="totp-note">
        Brug en engangskode fra din godkendelsesapp, når du skal bekræfte
        ejeradgang fra en anden session. Skriv <code>!override &lt;kode&gt;</code> i den session.
        Behandl opsætningsnøglen som en adgangskode.
      </p>

      <div className="totp-status">
        Status: {configured === undefined ? '…' : configured
          ? <strong className="totp-on">aktiveret{account ? ` (${account})` : ''} ✓</strong>
          : <strong className="totp-off">ikke opsat</strong>}
      </div>

      {setup && (
        <div className="totp-provision">
          {qrDataUrl && <img src={qrDataUrl} alt="TOTP QR-kode" className="totp-qr" />}
          <p>Scan med Google Authenticator / Authy / 2FAS — eller indtast nøglen manuelt:</p>
          <code className="totp-secret">{setup.secret}</code>
          <p className="totp-warn">⚠ Vises kun nu. Scan/gem den før du lukker.</p>
        </div>
      )}

      <div className="totp-actions">
        <button type="button" disabled={busy || resource.status !== 'ready'} onClick={() => void doSetup()}>
          {configured ? 'Generér ny nøgle' : 'Opsæt 2FA'}
        </button>
        {configured && (
          <button type="button" className="totp-revoke" disabled={busy || resource.status !== 'ready'} onClick={() => void doRevoke()}>
            Fjern
          </button>
        )}
      </div>
    </div>
  )
}
