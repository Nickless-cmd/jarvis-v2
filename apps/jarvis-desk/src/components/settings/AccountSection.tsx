import { useEffect, useRef, useState } from 'react'
import QRCode from 'qrcode'
import type { ApiConfig } from '../../lib/api'
import { createPairing, getPairStatus, googleLinkStart, googleLoginResult } from '../../lib/api'
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

  // ── Mobil-pairing (QR) ────────────────────────────────────────────────
  const [qrImg, setQrImg] = useState('')
  const [qrCode, setQrCode] = useState('')
  const [qrLeft, setQrLeft] = useState(0)
  const [qrBusy, setQrBusy] = useState(false)
  const [qrMsg, setQrMsg] = useState('')
  const [qrPaired, setQrPaired] = useState(false)
  useEffect(() => {
    if (qrLeft <= 0) return
    const t = setTimeout(() => setQrLeft((s) => s - 1), 1000)
    return () => clearTimeout(t)
  }, [qrLeft])
  useEffect(() => { if (qrLeft === 0 && qrImg) { setQrImg(''); setQrMsg('Koden udløb — lav en ny.') } }, [qrLeft, qrImg])
  // Poll status mens QR vises → vis "Mobil tilsluttet ✓" når den scannes.
  useEffect(() => {
    if (!config || !qrCode || !qrImg) return
    let alive = true
    const iv = setInterval(async () => {
      const s = await getPairStatus(config, qrCode).catch(() => ({ state: undefined as undefined }))
      if (!alive) return
      if (s.state === 'redeemed') {
        setQrPaired(true); setQrImg(''); setQrLeft(0); setQrMsg('')
        clearInterval(iv)
      }
    }, 2000)
    return () => { alive = false; clearInterval(iv) }
  }, [config, qrCode, qrImg])
  const makePairing = async () => {
    if (!config || qrBusy) return
    setQrBusy(true); setQrMsg('Laver kode…'); setQrPaired(false)
    try {
      const res = await createPairing(config)
      if (!res.code) { setQrMsg(res.error === 'not_authenticated' ? 'Log ind først.' : 'Kunne ikke lave kode.'); return }
      const payload = JSON.stringify({ url: config.apiBaseUrl, code: res.code })
      const img = await QRCode.toDataURL(payload, { margin: 1, width: 220 })
      setQrCode(res.code); setQrImg(img); setQrLeft(res.expires_in ?? 120); setQrMsg('')
    } catch { setQrMsg('Kunne ikke nå serveren.') }
    finally { setQrBusy(false) }
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
        {linked ? (
          <>
            <p className="account-google-msg"><span className="badge badge-ok">Google forbundet ✓</span></p>
            <p className="account-google-hint">Du kan logge ind med Google. Vil du forbinde en anden konto?</p>
            <button type="button" className="account-google-btn" onClick={linkGoogle} disabled={gBusy}>
              {gBusy ? 'Forbinder…' : 'Forbind en anden Google-konto'}
            </button>
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

      <div className="account-google">
        <p className="account-google-hint">Forbind Jarvis-mobil: scan koden i companion-appen.</p>
        {qrPaired ? (
          <p className="account-google-msg"><span className="badge badge-ok">Mobil tilsluttet ✓</span></p>
        ) : null}
        {qrImg ? (
          <div style={{ textAlign: 'center' }}>
            <img src={qrImg} alt="QR-pairing-kode" width={220} height={220} style={{ borderRadius: 8, background: '#fff', padding: 8 }} />
            <p className="account-google-hint">Udløber om {qrLeft}s — scan nu i appen. Venter på scanning…</p>
          </div>
        ) : null}
        <button type="button" className="account-google-btn" onClick={makePairing} disabled={qrBusy}>
          {qrBusy ? 'Laver kode…' : qrImg ? 'Ny kode' : qrPaired ? 'Forbind en til' : 'Forbind mobil-app'}
        </button>
        {qrMsg && <p className="account-google-msg">{qrMsg}</p>}
      </div>
    </div>
  )
}
