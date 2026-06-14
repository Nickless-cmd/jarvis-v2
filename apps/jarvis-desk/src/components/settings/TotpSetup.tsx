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
  const [configured, setConfigured] = useState<boolean | null>(null)
  const [account, setAccount] = useState<string | null>(null)
  const [setup, setSetup] = useState<TotpSetupResult | null>(null)
  const [qrDataUrl, setQrDataUrl] = useState('')
  const [busy, setBusy] = useState(false)

  const loadStatus = async () => {
    if (!config) return
    try {
      const s = await getTotpStatus(config)
      setConfigured(s.configured)
      setAccount(s.account)
    } catch { setConfigured(null) }
  }

  useEffect(() => { void loadStatus() }, [config?.apiBaseUrl, config?.authToken])

  // Render QR lokalt når et nyt setup-resultat kommer.
  useEffect(() => {
    if (!setup) { setQrDataUrl(''); return }
    void QRCode.toDataURL(setup.provisioning_uri, { width: 220, margin: 1 })
      .then(setQrDataUrl)
      .catch(() => setQrDataUrl(''))
  }, [setup])

  const doSetup = async () => {
    if (!config) return
    setBusy(true)
    try {
      const res = await setupTotp(config)
      setSetup(res)
      setConfigured(true)
    } finally { setBusy(false) }
  }

  const doRevoke = async () => {
    if (!config) return
    setBusy(true)
    try {
      await revokeTotp(config)
      setSetup(null)
      setConfigured(false)
    } finally { setBusy(false) }
  }

  return (
    <div className="totp-setup">
      <h3>Owner-override (2FA)</h3>
      <p className="totp-note">
        Din kryptografiske bagdør: hvis du sidder i en fremmed session (Mikkels Discord,
        din mors maskine) og skal bruge fuld kontrol, skriver du <code>!override &lt;kode&gt;</code>.
        Koden kommer fra din authenticator. Det er den ENESTE måde nogen kan bevise det er dig.
      </p>

      <div className="totp-status">
        Status: {configured === null ? '…' : configured
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
        <button type="button" disabled={busy} onClick={() => void doSetup()}>
          {configured ? 'Generér ny nøgle' : 'Opsæt 2FA'}
        </button>
        {configured && (
          <button type="button" className="totp-revoke" disabled={busy} onClick={() => void doRevoke()}>
            Fjern
          </button>
        )}
      </div>
    </div>
  )
}
