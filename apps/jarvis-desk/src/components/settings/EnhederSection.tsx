import { useEffect, useState } from 'react'
import QRCode from 'qrcode'
import type { ApiConfig } from '../../lib/api'
import { getPairStatus } from '../../lib/api'
import { fjernEnhed, hentEnheder, opretParring, saetEnhedsKrav, tilfoejDenneComputer, type EnhedsOverblik } from '../../lib/enheder'
import { formatRelativeTime } from '../../lib/formatTime'

/**
 * Enheder — hvem må styre denne computer, og hvem må bruge code mode.
 *
 * Bygget efter Codex' fjernstyring (Jarvis' kortlægning codex-remote-control.md,
 * Bjørn 19/9-2026):
 * - **Sikkerhedsmeddelelsen FØRST** — hvad adgangen betyder, før den bedes om.
 * - **Tillad på computeren, så par** (`PairingAfterAllow`): «Tillad» + din
 *   totrinskode, først DEREFTER vises QR-koden.
 * - **Fjern pr. enhed** — en fjernet telefon er ude med det samme.
 * - **Reglen** «code mode kræver en tilføjet enhed» — kun ejeren, med kode.
 */
export function EnhederSection({ config, ejer }: { config: ApiConfig; ejer: boolean }) {
  const [overblik, setOverblik] = useState<EnhedsOverblik | null>(null)
  const [fejl, setFejl] = useState('')
  const [trin, setTrin] = useState<'hvile' | 'tillad' | 'qr' | 'parret'>('hvile')
  const [totp, setTotp] = useState('')
  const [travl, setTravl] = useState(false)
  const [qr, setQr] = useState<{ img: string; kode: string; tilbage: number } | null>(null)
  const [parretNavn, setParretNavn] = useState('')
  const [fjerner, setFjerner] = useState<string | null>(null)
  const [kravTotp, setKravTotp] = useState('')
  const [kravAaben, setKravAaben] = useState(false)
  const [computerTotp, setComputerTotp] = useState('')

  const hent = async () => {
    const r = await hentEnheder(config)
    if (r.ok) { setOverblik(r.data); setFejl('') } else setFejl(r.fejl)
  }
  useEffect(() => { void hent() }, [config.apiBaseUrl, config.authToken]) // eslint-disable-line react-hooks/exhaustive-deps

  // QR: nedtælling og status-poll, som før.
  useEffect(() => {
    if (!qr || qr.tilbage <= 0) return
    const t = setTimeout(() => setQr((q) => (q ? { ...q, tilbage: q.tilbage - 1 } : q)), 1000)
    return () => clearTimeout(t)
  }, [qr])
  useEffect(() => {
    if (!qr) return
    if (qr.tilbage <= 0) { setQr(null); setTrin('hvile'); setFejl('Koden udløb — prøv igen.'); return }
  }, [qr?.tilbage]) // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => {
    if (trin !== 'qr' || !qr) return
    let aktiv = true
    const iv = setInterval(async () => {
      const s = await getPairStatus(config, qr.kode).catch(() => ({ state: undefined, navn: '' }))
      if (!aktiv || s.state !== 'redeemed') return
      clearInterval(iv)
      setParretNavn((s as { navn?: string }).navn || 'Telefonen')
      setQr(null); setTrin('parret'); void hent()
    }, 2000)
    return () => { aktiv = false; clearInterval(iv) }
  }, [trin, qr?.kode]) // eslint-disable-line react-hooks/exhaustive-deps

  const tillad = async () => {
    setTravl(true); setFejl('')
    const r = await opretParring(config, totp.trim())
    setTravl(false); setTotp('')
    if (!r.ok) { setFejl(r.fejl); return }
    const img = await QRCode.toDataURL(JSON.stringify({ url: config.apiBaseUrl, code: r.data.code }), { margin: 1, width: 220 })
    setQr({ img, kode: r.data.code, tilbage: r.data.expires_in ?? 120 })
    setTrin('qr')
  }

  const fjern = async (id: string) => {
    const r = await fjernEnhed(config, id)
    setFjerner(null)
    if (!r.ok) setFejl(r.fejl)
    void hent()
  }

  const tilfoejComputer = async () => {
    setTravl(true)
    const r = await tilfoejDenneComputer(config, computerTotp.trim(), 'Denne computer')
    setTravl(false); setComputerTotp('')
    if (!r.ok) setFejl(r.fejl); else void hent()
  }

  const skiftKrav = async () => {
    if (!overblik) return
    setTravl(true)
    const r = await saetEnhedsKrav(config, !overblik.kraev_aktivt, kravTotp.trim(), 'Denne computer')
    setTravl(false); setKravTotp(''); setKravAaben(false)
    if (!r.ok) setFejl(r.fejl); else void hent()
  }

  return (
    <div className="account-google enheder" data-testid="enheder">
      <h4 className="enheder-titel">Enheder</h4>

      {overblik && overblik.enheder.length > 0 ? (
        <ul className="enheder-liste">
          {overblik.enheder.map((e) => (
            <li key={e.id} className="enheder-raekke">
              <span className="enheder-navn">{e.navn}</span>
              <span className="enheder-meta">
                {e.type === 'telefon' ? 'Telefon' : 'Computer'}{e.platform && e.type === 'telefon' ? ` · ${e.platform}` : ''}
                {e.sidst_set ? ` · set ${formatRelativeTime(new Date(e.sidst_set * 1000).toISOString())}` : ''}
              </span>
              {fjerner === e.id ? (
                <span className="enheder-bekraeft">
                  {e.type === 'telefon' ? 'Den mister al adgang med det samme. ' : 'Den mister code mode. '}
                  <button type="button" className="enheder-fjern-ja" onClick={() => void fjern(e.id)}>Fjern</button>
                  <button type="button" className="enheder-fortryd" onClick={() => setFjerner(null)}>Behold</button>
                </span>
              ) : (
                <button type="button" className="enheder-fjern" onClick={() => setFjerner(e.id)} aria-label={`Fjern ${e.navn}`}>Fjern</button>
              )}
            </li>
          ))}
        </ul>
      ) : overblik ? (
        <p className="account-google-hint">Ingen enheder er tilføjet endnu.</p>
      ) : null}

      {overblik && overblik.denne.type === 'computer' && !overblik.denne.tilfoejet ? (
        <div className="enheder-denne">
          <p className="account-google-hint">Denne computer er ikke tilføjet{overblik.kraev_aktivt ? ' — code mode er lukket her, til den er.' : '.'}</p>
          <input className="enheder-totp" inputMode="numeric" maxLength={6} placeholder="Totrinskode" value={computerTotp} onChange={(e) => setComputerTotp(e.target.value)} aria-label="Totrinskode til at tilføje denne computer" />
          <button type="button" className="account-google-btn" disabled={travl || computerTotp.trim().length !== 6} onClick={() => void tilfoejComputer()}>Tilføj denne computer</button>
        </div>
      ) : null}

      {trin === 'hvile' ? (
        <button type="button" className="account-google-btn" onClick={() => { setTrin('tillad'); setFejl('') }}>Tilføj telefon</button>
      ) : null}

      {trin === 'tillad' ? (
        <div className="enheder-tillad" role="group" aria-label="Tillad en ny telefon">
          {/* Codex' sikkerhedsmeddelelse — FØR der bedes om noget. */}
          <p className="enheder-advarsel">
            En tilføjet telefon kan styre Jarvis på dine vegne — også code mode: kommandoer, filer og, via broen, denne computer. Tilføj kun telefoner du selv ejer og har tillid til.
          </p>
          <p className="account-google-hint"><strong>Tillad en ny telefon at styre denne computer?</strong> Skriv din totrinskode for at tillade det. Derefter vises koden, telefonen skal scanne.</p>
          <input className="enheder-totp" inputMode="numeric" maxLength={6} placeholder="Totrinskode" value={totp} onChange={(e) => setTotp(e.target.value)} aria-label="Totrinskode" autoFocus />
          <div className="enheder-knapper">
            <button type="button" className="account-google-btn" disabled={travl || totp.trim().length !== 6} onClick={() => void tillad()}>Tillad og vis kode</button>
            <button type="button" className="enheder-fortryd" onClick={() => { setTrin('hvile'); setTotp('') }}>Senere</button>
          </div>
        </div>
      ) : null}

      {trin === 'qr' && qr ? (
        <div style={{ textAlign: 'center' }}>
          <img src={qr.img} alt="QR-kode til parring" width={220} height={220} style={{ borderRadius: 8, background: '#fff', padding: 8 }} />
          <p className="account-google-hint">Scan i Jarvis-appen på telefonen. Udløber om {qr.tilbage}s — venter på scanning…</p>
        </div>
      ) : null}

      {trin === 'parret' ? (
        <p className="account-google-msg"><span className="badge badge-ok">{parretNavn} er tilføjet ✓</span></p>
      ) : null}

      {ejer && overblik ? (
        <div className="enheder-krav">
          <p className="account-google-hint">
            <strong>Code mode kræver en tilføjet enhed:</strong> {overblik.kraev_aktivt ? 'slået til' : 'slået fra'}.{' '}
            {overblik.kraev_aktivt
              ? 'Kun tilføjede telefoner og computere kan bruge code mode.'
              : 'Slår du den til, kan kun tilføjede enheder bruge code mode — denne computer tilføjes automatisk, andre telefoner skal tilføjes her.'}
          </p>
          {kravAaben ? (
            <div className="enheder-knapper">
              <input className="enheder-totp" inputMode="numeric" maxLength={6} placeholder="Totrinskode" value={kravTotp} onChange={(e) => setKravTotp(e.target.value)} aria-label="Totrinskode til reglen" autoFocus />
              <button type="button" className="account-google-btn" disabled={travl || kravTotp.trim().length !== 6} onClick={() => void skiftKrav()}>
                {overblik.kraev_aktivt ? 'Slå fra' : 'Slå til'}
              </button>
              <button type="button" className="enheder-fortryd" onClick={() => { setKravAaben(false); setKravTotp('') }}>Fortryd</button>
            </div>
          ) : (
            <button type="button" className="enheder-fortryd" onClick={() => setKravAaben(true)}>{overblik.kraev_aktivt ? 'Slå reglen fra…' : 'Slå reglen til…'}</button>
          )}
        </div>
      ) : null}

      {fejl ? <p className="account-google-msg enheder-fejl" role="alert">{fejl}</p> : null}
    </div>
  )
}
