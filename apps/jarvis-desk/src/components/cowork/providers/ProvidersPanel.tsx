import { useCallback, useEffect, useState } from 'react'
import type { ApiConfig } from '../../../lib/api'
import {
  getRegistret, getUdbyderHelbred, getBackups, getHistorik,
  saetModel, saetUdbyder, fjernModel, fjernUdbyder, saetLane, tilfoejUdbyder, gendanBackup,
  type Registret, type UdbyderHelbred, type Historik,
} from '../../../lib/cheapLaneApi'

/**
 * Udbydere — hele registret, ikke de første otte.
 *
 * Bjørn 16/9-2026: «providers fulde control og mulighed for til at tilføje og
 * fjerne og deaktivere og se fejl».
 *
 * Tre ting adskiller sig fra Cheap Lane-fladen, og de er bevidste:
 *
 *  - Her står ALLE lanes (cheap, local, coding, visible, inner_enrichment),
 *    ikke kun den billige. En model kan flyttes mellem dem; flytning er ikke
 *    en slukning.
 *  - «Fjern» og «Slå fra» er to forskellige knapper. Den første tager posten
 *    ud af registret, den anden lader den blive med sin historie.
 *  - Nøglen skrives ét sted (auth-profilen) og vises aldrig igen. Feltet er
 *    et password-felt, og svaret fra serveren bærer aldrig nøglen tilbage.
 */
type Fane = 'udbydere' | 'modeller' | 'tilfoej' | 'helbred' | 'backups'

const FANER: { id: Fane; label: string }[] = [
  { id: 'udbydere', label: 'Udbydere' },
  { id: 'modeller', label: 'Modeller' },
  { id: 'tilfoej', label: 'Tilføj' },
  { id: 'helbred', label: 'Helbred' },
  { id: 'backups', label: 'Sikkerhedskopier' },
]

const LANES = ['cheap', 'local', 'coding', 'visible', 'inner_enrichment']

function tid(s?: string | null): string {
  if (!s) return '–'
  const d = new Date(s)
  return Number.isNaN(d.getTime()) ? String(s).slice(0, 16)
    : d.toLocaleString('da-DK', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })
}

export function ProvidersPanel({ config }: { config?: ApiConfig }) {
  const [fane, setFane] = useState<Fane>('udbydere')
  const [reg, setReg] = useState<Registret | null>(null)
  const [helbred, setHelbred] = useState<UdbyderHelbred[]>([])
  const [historik, setHistorik] = useState<Historik | null>(null)
  const [backups, setBackups] = useState<{ navn: string; tid: string; bytes: number }[]>([])
  const [laneFilter, setLaneFilter] = useState('')
  const [besked, setBesked] = useState('')
  const [henter, setHenter] = useState(false)
  const [bekraeft, setBekraeft] = useState<{ hvad: string; kald: () => Promise<unknown> } | null>(null)

  const hent = useCallback(async () => {
    if (!config) return
    setHenter(true)
    const [r, h, b, hi] = await Promise.allSettled([
      getRegistret(config), getUdbyderHelbred(config), getBackups(config), getHistorik(config, 168),
    ])
    if (r.status === 'fulfilled') setReg(r.value)
    if (h.status === 'fulfilled') setHelbred(h.value.providers ?? [])
    if (b.status === 'fulfilled') setBackups(b.value.backups ?? [])
    if (hi.status === 'fulfilled') setHistorik(hi.value)
    const døde = [r, h, b, hi].filter((x) => x.status === 'rejected').length
    setBesked(døde ? `${døde} af 4 kilder svarede ikke` : '')
    setHenter(false)
  }, [config])

  useEffect(() => { void hent() }, [hent])

  const handling = async (fn: () => Promise<unknown>, hvad: string) => {
    try {
      const svar = await fn() as { status?: string; fejl?: string }
      setBesked(svar?.fejl ? svar.fejl : hvad)
      await hent()
    } catch (e) {
      setBesked(e instanceof Error ? e.message : 'handlingen fejlede')
    }
  }

  if (!config) return <div className="mc-tom">Ingen forbindelse til serveren.</div>

  // Brug pr. udbyder fra den seneste uge — så «slå fra» ikke er et blindt valg.
  const brug = new Map<string, { kald: number; fejl: number }>()
  for (const u of historik?.udbydere ?? []) {
    const b = brug.get(u.provider) ?? { kald: 0, fejl: 0 }
    b.kald += u.kald; b.fejl += u.fejl
    brug.set(u.provider, b)
  }

  return (
    <div className="mc providers">
      <div className="mc-top">
        <h2>Udbydere</h2>
        <div className="mc-top-right">
          <button type="button" onClick={() => void hent()} disabled={henter}>
            {henter ? 'Henter…' : 'Opdatér'}
          </button>
        </div>
      </div>

      {besked && <div className="mc-besked">{besked}</div>}

      <div className="mc-tabs">
        {FANER.map((f) => (
          <button key={f.id} type="button" className={f.id === fane ? 'aktiv' : ''}
                  aria-pressed={f.id === fane} onClick={() => setFane(f.id)}>
            {f.label}
            {f.id === 'udbydere' && reg?.opsummering ? ` (${reg.opsummering.udbydere})` : ''}
            {f.id === 'modeller' && reg?.opsummering ? ` (${reg.opsummering.modeller})` : ''}
          </button>
        ))}
      </div>

      {fane === 'udbydere' && (
        <div>
          <div className="cl-kort-raekke">
            <Kort navn="Udbydere" vaerdi={reg?.opsummering?.udbydere ?? 0} />
            <Kort navn="Modeller" vaerdi={reg?.opsummering?.modeller ?? 0}
                  under={`${reg?.opsummering?.aktive_modeller ?? 0} aktive`} />
            {Object.entries(reg?.lanes ?? {}).slice(0, 3).map(([lane, t]) => (
              <Kort key={lane} navn={lane} vaerdi={t.aktive} under={`af ${t.i_alt}`} />
            ))}
          </div>

          <table className="mc-tabel">
            <thead>
              <tr><th>Udbyder</th><th>Adresse</th><th>Nøgle</th><th>Modeller</th>
                <th>Kald (7 d)</th><th>Status</th><th></th></tr>
            </thead>
            <tbody>
              {(reg?.udbydere ?? []).map((u) => {
                const b = brug.get(u.provider)
                return (
                  <tr key={u.provider} className={u.enabled === false ? 'cl-inaktiv' : ''}>
                    <td><strong>{u.provider}</strong>
                      <div className="cl-profil">{u.auth_mode} · {u.auth_profile}</div></td>
                    <td className="cl-besked">{u.base_url || '–'}</td>
                    <td>{u.credentials_ready
                      ? 'klar'
                      : <span className="cl-daarlig">mangler</span>}</td>
                    <td>{u.enabled_model_count}/{u.model_count}</td>
                    <td>{b ? `${b.kald}${b.fejl ? ` (${b.fejl} fejl)` : ''}` : '–'}</td>
                    <td>{u.enabled === false ? 'slået fra' : 'aktiv'}</td>
                    <td className="cl-knapper">
                      <button type="button" onClick={() => void handling(
                        () => saetUdbyder(config, u.provider, u.enabled === false),
                        u.enabled === false ? 'Udbyder slået til' : 'Udbyder slået fra')}>
                        {u.enabled === false ? 'Slå til' : 'Slå fra'}
                      </button>
                      <button type="button" className="cl-fare" onClick={() => setBekraeft({
                        hvad: `Fjern ${u.provider} og dens ${u.model_count} model(ler) fra registret? `
                          + 'Nøglen bliver liggende, så det kan fortrydes.',
                        kald: () => fjernUdbyder(config, u.provider),
                      })}>Fjern</button>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}

      {fane === 'modeller' && (
        <div>
          <div className="ap-filtre">
            <button type="button" className={laneFilter === '' ? 'aktiv' : ''}
                    aria-pressed={laneFilter === ''}
                    onClick={() => setLaneFilter('')}>Alle</button>
            {Object.keys(reg?.lanes ?? {}).map((l) => (
              <button key={l} type="button" className={laneFilter === l ? 'aktiv' : ''}
                      aria-pressed={laneFilter === l}
                      onClick={() => setLaneFilter(l)}>{l}</button>
            ))}
          </div>
          <table className="mc-tabel">
            <thead>
              <tr><th>Udbyder</th><th>Model</th><th>Lane</th><th>Prøve</th>
                <th>Status</th><th></th></tr>
            </thead>
            <tbody>
              {(reg?.modeller ?? [])
                .filter((m) => !laneFilter || m.lane === laneFilter)
                .map((m) => (
                  <tr key={`${m.provider}/${m.model}`} className={m.enabled ? '' : 'cl-inaktiv'}>
                    <td>{m.provider}</td>
                    <td className="cl-model">{m.model}</td>
                    <td>
                      <select value={m.lane ?? ''} aria-label={`Lane for ${m.model}`}
                              onChange={(e) => void handling(
                                () => saetLane(config, String(m.provider), String(m.model), e.target.value),
                                `Flyttet til ${e.target.value}`)}>
                        {LANES.concat(m.lane && !LANES.includes(m.lane) ? [m.lane] : [])
                          .map((l) => <option key={l} value={l}>{l}</option>)}
                      </select>
                    </td>
                    <td>{m.probe_score ?? '–'}</td>
                    <td title={m.disabled_reason ?? ''}>
                      {m.enabled ? 'aktiv' : `fra${m.disabled_reason ? ` — ${m.disabled_reason}` : ''}`}
                    </td>
                    <td className="cl-knapper">
                      <button type="button" onClick={() => void handling(
                        () => saetModel(config, String(m.provider), String(m.model), !m.enabled,
                          m.enabled ? 'slået fra fra desk' : ''),
                        m.enabled ? 'Model slået fra' : 'Model slået til')}>
                        {m.enabled ? 'Slå fra' : 'Slå til'}
                      </button>
                      <button type="button" className="cl-fare" onClick={() => setBekraeft({
                        hvad: `Fjern ${m.provider}/${m.model} fra registret?`,
                        kald: () => fjernModel(config, String(m.provider), String(m.model)),
                      })}>Fjern</button>
                    </td>
                  </tr>
                ))}
            </tbody>
          </table>
        </div>
      )}

      {fane === 'tilfoej' && <TilfoejForm config={config} onFaerdig={(t) => void handling(async () => t, t)} />}

      {fane === 'helbred' && (
        <div>
          <p className="cl-note">
            Gemt ping-måling, ikke en live-test. Den kører på egen kadence.
          </p>
          <table className="mc-tabel">
            <thead><tr><th>Udbyder</th><th>Svar</th><th>Latens</th></tr></thead>
            <tbody>
              {helbred.map((h) => (
                <tr key={h.provider}>
                  <td>{h.provider}</td>
                  <td className={h.ok ? '' : 'cl-daarlig'}>
                    {h.ok ? (h.degraded ? 'træg' : 'ok') : 'svarer ikke'}
                  </td>
                  <td>{h.latency_ms ? `${h.latency_ms} ms` : '–'}</td>
                </tr>
              ))}
              {!helbred.length && <tr><td colSpan={3}>Ingen måling endnu.</td></tr>}
            </tbody>
          </table>
        </div>
      )}

      {fane === 'backups' && (
        <div>
          <p className="cl-note">
            Hver ændring i registret tager en kopi først. De ti nyeste beholdes.
          </p>
          <table className="mc-tabel">
            <thead><tr><th>Tidspunkt</th><th>Fil</th><th></th></tr></thead>
            <tbody>
              {backups.map((b) => (
                <tr key={b.navn}>
                  <td>{tid(b.tid)}</td>
                  <td className="cl-besked">{b.navn}</td>
                  <td className="cl-knapper">
                    <button type="button" onClick={() => setBekraeft({
                      hvad: `Rul registret tilbage til ${tid(b.tid)}? Den nuværende tilstand gemmes som en ny kopi først.`,
                      kald: () => gendanBackup(config, b.navn),
                    })}>Gendan</button>
                  </td>
                </tr>
              ))}
              {!backups.length && <tr><td colSpan={3}>Ingen kopier endnu.</td></tr>}
            </tbody>
          </table>
        </div>
      )}

      {bekraeft && (
        <div className="pv-bekraeft" role="dialog" aria-label="Bekræft">
          <p>{bekraeft.hvad}</p>
          <div className="cl-knapper">
            <button type="button" onClick={() => {
              const k = bekraeft.kald
              setBekraeft(null)
              void handling(k, 'Gennemført')
            }}>Ja, gør det</button>
            <button type="button" onClick={() => setBekraeft(null)}>Fortryd</button>
          </div>
        </div>
      )}
    </div>
  )
}

function TilfoejForm({ config, onFaerdig }: { config: ApiConfig; onFaerdig: (t: string) => void }) {
  const [f, setF] = useState({
    provider: '', model: '', lane: 'cheap', auth_mode: 'api_key',
    auth_profile: 'default', base_url: '', api_key: '',
  })
  const [travl, setTravl] = useState(false)
  const kan = f.provider.trim() && f.model.trim()

  const send = async () => {
    setTravl(true)
    try {
      const svar = await tilfoejUdbyder(config, f)
      onFaerdig(svar.fejl
        ? svar.fejl
        : `${f.provider}/${f.model} er tilføjet${svar.noegle_gemt ? ' med nøgle' : ''}`)
      // Nøglen ryddes med det samme — den skal ikke blive stående i en formular.
      setF({ ...f, model: '', api_key: '' })
    } catch (e) {
      onFaerdig(e instanceof Error ? e.message : 'kunne ikke tilføje')
    }
    setTravl(false)
  }

  return (
    <div className="pv-form">
      <p className="cl-note">
        Tilføjer en udbyder og en model i registret. Nøglen er valgfri — er den tom,
        røres den eksisterende ikke. Den gemmes i auth-profilen, aldrig i registret,
        og vises aldrig igen.
      </p>
      <label>Udbyder
        <input value={f.provider} onChange={(e) => setF({ ...f, provider: e.target.value })}
               placeholder="fx groq" />
      </label>
      <label>Model
        <input value={f.model} onChange={(e) => setF({ ...f, model: e.target.value })}
               placeholder="fx llama-3.3-70b" />
      </label>
      <label>Lane
        <select value={f.lane} onChange={(e) => setF({ ...f, lane: e.target.value })}>
          {LANES.map((l) => <option key={l} value={l}>{l}</option>)}
        </select>
      </label>
      <label>Adresse
        <input value={f.base_url} onChange={(e) => setF({ ...f, base_url: e.target.value })}
               placeholder="https://…/v1" />
      </label>
      <label>Auth-profil
        <input value={f.auth_profile} onChange={(e) => setF({ ...f, auth_profile: e.target.value })} />
      </label>
      <label>Nøgle (valgfri)
        <input type="password" autoComplete="off" value={f.api_key}
               onChange={(e) => setF({ ...f, api_key: e.target.value })}
               placeholder="lades tom hvis udbyderen allerede har en" />
      </label>
      <button type="button" disabled={!kan || travl} onClick={() => void send()}>
        {travl ? 'Tilføjer…' : 'Tilføj udbyder'}
      </button>
    </div>
  )
}

function Kort({ navn, vaerdi, under }: { navn: string; vaerdi: number | string; under?: string }) {
  return (
    <div className="cl-kort">
      <div className="cl-kort-navn">{navn}</div>
      <div className="cl-kort-vaerdi">{vaerdi}</div>
      {under && <div className="cl-kort-under">{under}</div>}
    </div>
  )
}
