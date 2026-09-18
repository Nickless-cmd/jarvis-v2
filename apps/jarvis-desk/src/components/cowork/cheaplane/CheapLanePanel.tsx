import { useCallback, useEffect, useState } from 'react'
import type { ApiConfig } from '../../../lib/api'
import {
  getBalancerState, getHistorik, getFejl, getTidsserie, getRegistret,
  slotHandling, refreshPool, saetModel,
  type BalancerState, type Historik, type FejlSvar, type TidsserieSpand, type Registret,
} from '../../../lib/cheapLaneApi'
import { useCheapLaneStore } from '../../../lib/cheapLaneStore'
import { CheapLaneOverview } from './CheapLaneOverview'
import { CheapLaneCapacity } from './CheapLaneCapacity'

/**
 * Cheap Lane — hele lanen på én flade.
 *
 * Bjørn 16/9-2026: «cheap lane er især vigtigt for jeg ander intet om hvordan
 * cheap lane eller load_balanceren klarer sig».
 *
 * De to kilder svarer på hvert sit spørgsmål, og det er derfor de har hver sin
 * fane frem for at blive blandet til ét tal:
 *
 *   Puljen     NU — hvilke slots kan vælges i dette øjeblik, hvem er i køling
 *   Historik   FORLØBET — 90.000 kald med udfald, latens og pris
 *
 * Handlingerne rammer også to forskellige steder, og forskellen står på
 * knapperne: et slot «pauses» i balancerens egen tilstand, mens en model
 * slås fra i registret og derfor bliver væk efter en genstart.
 */
type Fane = 'oversigt' | 'kapacitet' | 'pulje' | 'udbydere' | 'fejl' | 'historik'

const FANER: { id: Fane; label: string }[] = [
  { id: 'oversigt', label: 'Oversigt' },
  { id: 'kapacitet', label: 'Kapacitet' },
  { id: 'pulje', label: 'Puljen nu' },
  { id: 'udbydere', label: 'Udbydere' },
  { id: 'fejl', label: 'Fejl' },
  { id: 'historik', label: 'Historik' },
]

const VINDUER = [1, 6, 24, 72, 168]

function pct(v: number | null | undefined): string {
  // «Ingen data» og «nul procent» er to forskellige beskeder.
  if (v === null || v === undefined) return '–'
  // Dansk komma. Foerste udgave skrev «46.7 %» — engelsk punktum midt i en
  // dansk flade; fanget af render-testen.
  return `${(Math.round(v * 1000) / 10).toLocaleString('da-DK')} %`
}

function tid(s?: string | null): string {
  if (!s) return '–'
  const d = new Date(s)
  return Number.isNaN(d.getTime()) ? String(s).slice(0, 16) : d.toLocaleString('da-DK', {
    day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit',
  })
}

export function CheapLanePanel({ config }: { config?: ApiConfig }) {
  const [fane, setFane] = useState<Fane>('oversigt')
  const [timer, setTimer] = useState(24)
  const [state, setState] = useState<BalancerState | null>(null)
  const [historik, setHistorik] = useState<Historik | null>(null)
  const [fejl, setFejl] = useState<FejlSvar | null>(null)
  const [serie, setSerie] = useState<TidsserieSpand[]>([])
  const [registret, setRegistret] = useState<Registret | null>(null)
  const [henter, setHenter] = useState(false)
  const [besked, setBesked] = useState('')
  // Oversigt og kapacitet kommer fra ÉT snapshot med Centrals strøm som puls.
  // De øvrige faner henter stadig hver for sig indtil opgave 11-12 flytter dem.
  const butik = useCheapLaneStore(config, timer)

  const hent = useCallback(async () => {
    if (!config) return
    setHenter(true)
    // Hver kilde for sig: én der fejler må ikke tømme fladen for de andre.
    const [s, h, f, t, r] = await Promise.allSettled([
      getBalancerState(config), getHistorik(config, timer),
      getFejl(config, timer, 100), getTidsserie(config, timer, timer <= 6 ? 15 : 60),
      getRegistret(config),
    ])
    if (s.status === 'fulfilled') setState(s.value)
    if (h.status === 'fulfilled') setHistorik(h.value)
    if (f.status === 'fulfilled') setFejl(f.value)
    if (t.status === 'fulfilled') setSerie(t.value.spand ?? [])
    if (r.status === 'fulfilled') setRegistret(r.value)
    const døde = [s, h, f, t, r].filter((x) => x.status === 'rejected').length
    setBesked(døde ? `${døde} af 5 kilder svarede ikke` : '')
    setHenter(false)
  }, [config, timer])

  useEffect(() => { void hent() }, [hent])

  const handling = async (fn: () => Promise<unknown>, hvad: string) => {
    try {
      await fn()
      setBesked(hvad)
      await hent()
    } catch (e) {
      setBesked(e instanceof Error ? e.message : 'handlingen fejlede')
    }
  }

  if (!config) return <div className="mc-tom">Ingen forbindelse til serveren.</div>


  return (
    <div className="mc cheaplane">
      <div className="mc-top">
        <h2>Cheap Lane</h2>
        <div className="mc-top-right">
          <select value={timer} onChange={(e) => setTimer(Number(e.target.value))}
                  aria-label="Tidsvindue">
            {VINDUER.map((v) => (
              <option key={v} value={v}>{v < 24 ? `${v} t` : `${v / 24} døgn`}</option>
            ))}
          </select>
          <span className={`cl-live cl-live-${butik.liveState}`} title={`Datastrøm: ${butik.liveState}`}>
            {butik.liveState === 'live' ? 'live' : butik.liveState === 'polling' ? 'poller' : butik.liveState}
          </span>
          <button type="button" onClick={() => { void hent(); butik.refresh() }} disabled={henter}>
            {henter ? 'Henter…' : 'Opdatér'}
          </button>
        </div>
      </div>

      {besked && <div className="mc-besked">{besked}</div>}

      <div className="mc-tabs">
        {FANER.map((f) => (
          <button key={f.id} type="button"
                  className={f.id === fane ? 'aktiv' : ''}
                  aria-pressed={f.id === fane}
                  onClick={() => setFane(f.id)}>
            {f.label}
            {f.id === 'fejl' && fejl?.antal_i_vinduet ? ` (${fejl.antal_i_vinduet})` : ''}
          </button>
        ))}
      </div>

      {fane === 'oversigt' && (
        butik.snapshot
          ? <CheapLaneOverview snapshot={butik.snapshot} serie={serie.map((x) => ({
              start: x.tid, kald: x.kald, fejl: x.fejl, tokens: 0,
            }))} />
          : <p className="cl-tom">{butik.error || 'Henter overblik…'}</p>
      )}

      {fane === 'kapacitet' && (
        <CheapLaneCapacity vinduer={butik.snapshot?.sections?.capacity?.data?.windows ?? []} />
      )}

      {fane === 'pulje' && (
        <div className="cl-pulje">
          <div className="cl-handlinger">
            <button type="button"
                    onClick={() => void handling(() => refreshPool(config), 'Puljen er bygget op igen')}>
              Genopbyg puljen
            </button>
            <span className="cl-note">
              Bygger slots op fra registret. Slots slået fra i hånden bliver liggende.
            </span>
          </div>
          <table className="mc-tabel">
            <thead>
              <tr>
                <th>Slot</th><th>Status</th><th>Vægt</th><th>RPM</th><th>I dag</th>
                <th>Succes</th><th>Breaker</th><th>Køling til</th><th></th>
              </tr>
            </thead>
            <tbody>
              {(state?.slots ?? []).map((s) => (
                <tr key={s.slot_id} className={`cl-status-${s.status ?? 'ukendt'}`}>
                  <td title={s.slot_id}>
                    <strong>{s.provider}</strong>
                    <span className="cl-model"> {s.model}</span>
                    {s.auth_profile && s.auth_profile !== 'default' && (
                      <span className="cl-profil"> · {s.auth_profile}</span>
                    )}
                  </td>
                  <td>{s.status}</td>
                  <td>{typeof s.weight === 'number' ? s.weight.toFixed(2) : '–'}</td>
                  <td>{s.rpm_used ?? 0}{s.rpm_limit ? ` / ${s.rpm_limit}` : ''}</td>
                  <td>{s.daily_used ?? 0}{s.daily_limit ? ` / ${s.daily_limit}` : ''}</td>
                  <td>{pct(s.success_rate)}</td>
                  <td>{s.breaker_level ? `niveau ${s.breaker_level}` : '–'}</td>
                  <td title={s.cooldown_reason ?? ''}>{tid(s.cooldown_until)}</td>
                  <td className="cl-knapper">
                    <button type="button" onClick={() => void handling(
                      () => slotHandling(config, s.slot_id, s.manually_disabled ? 'enable' : 'disable'),
                      s.manually_disabled ? 'Slot slået til' : 'Slot sat på pause')}>
                      {s.manually_disabled ? 'Slå til' : 'Pause'}
                    </button>
                    <button type="button" onClick={() => void handling(
                      () => slotHandling(config, s.slot_id, 'reset'), 'Slot nulstillet')}>
                      Nulstil
                    </button>
                  </td>
                </tr>
              ))}
              {!(state?.slots ?? []).length && <tr><td colSpan={9}>Puljen er tom.</td></tr>}
            </tbody>
          </table>
        </div>
      )}

      {fane === 'udbydere' && (
        <div className="cl-udbydere">
          <p className="cl-note">
            Her ændres <strong>registret</strong>. En model slået fra bliver væk af puljen
            ved næste opbygning — også efter en genstart. Hver ændring tager backup først.
          </p>
          <table className="mc-tabel">
            <thead>
              <tr><th>Udbyder</th><th>Model</th><th>Lane</th><th>Kald ({timer} t)</th>
                <th>Succes</th><th>p50</th><th>Status</th><th></th></tr>
            </thead>
            <tbody>
              {(registret?.modeller ?? [])
                .filter((m) => (m.lane ?? '') === 'cheap')
                .map((m) => {
                  const brug = (historik?.udbydere ?? []).filter(
                    (u) => u.provider === m.provider && u.model === m.model)
                  const kald = brug.reduce((n, u) => n + u.kald, 0)
                  const ok = brug.reduce((n, u) => n + u.ok, 0)
                  return (
                    <tr key={`${m.provider}/${m.model}`} className={m.enabled ? '' : 'cl-inaktiv'}>
                      <td>{m.provider}</td>
                      <td className="cl-model">{m.model}</td>
                      <td>{m.lane}</td>
                      <td>{kald}</td>
                      <td>{kald ? pct(ok / kald) : '–'}</td>
                      <td>{brug[0]?.latens_p50_ms ? `${brug[0].latens_p50_ms} ms` : '–'}</td>
                      <td title={m.disabled_reason ?? ''}>
                        {m.enabled ? 'aktiv' : `slået fra${m.disabled_reason ? ` — ${m.disabled_reason}` : ''}`}
                      </td>
                      <td className="cl-knapper">
                        <button type="button" onClick={() => void handling(
                          () => saetModel(config, String(m.provider), String(m.model), !m.enabled,
                            m.enabled ? 'slået fra fra desk' : ''),
                          m.enabled ? 'Model slået fra' : 'Model slået til')}>
                          {m.enabled ? 'Slå fra' : 'Slå til'}
                        </button>
                      </td>
                    </tr>
                  )
                })}
            </tbody>
          </table>
        </div>
      )}

      {fane === 'fejl' && (
        <div className="cl-fejl">
          <p className="cl-note">
            {fejl?.antal_i_vinduet ?? 0} fejl i vinduet. Viser de {fejl?.vist ?? 0} nyeste.
          </p>
          <table className="mc-tabel">
            <thead><tr><th>Tid</th><th>Udbyder</th><th>Model</th><th>Kode</th><th>Besked</th></tr></thead>
            <tbody>
              {(fejl?.raekker ?? []).map((r, i) => (
                <tr key={`${r.created_at}-${i}`}>
                  <td>{tid(r.created_at)}</td>
                  <td>{r.provider}</td>
                  <td className="cl-model">{r.model}</td>
                  <td>{r.error_code || '–'}</td>
                  <td className="cl-besked">{r.error_message || '–'}</td>
                </tr>
              ))}
              {!(fejl?.raekker ?? []).length && <tr><td colSpan={5}>Ingen fejl i vinduet.</td></tr>}
            </tbody>
          </table>
        </div>
      )}

      {fane === 'historik' && (
        <div className="cl-historik">
          <table className="mc-tabel">
            <thead>
              <tr><th>Udbyder</th><th>Model</th><th>Profil</th><th>Kald</th><th>Fejl</th>
                <th>Succes</th><th>p50</th><th>p95</th><th>Pris</th><th>Sidst OK</th></tr>
            </thead>
            <tbody>
              {(historik?.udbydere ?? []).map((u) => (
                <tr key={`${u.provider}/${u.model}/${u.auth_profile ?? ''}`}>
                  <td>{u.provider}</td>
                  <td className="cl-model">{u.model}</td>
                  <td>{u.auth_profile || 'default'}</td>
                  <td>{u.kald}</td>
                  <td>{u.fejl}</td>
                  <td className={(u.succesrate ?? 1) < 0.5 ? 'cl-daarlig' : ''}>{pct(u.succesrate)}</td>
                  <td>{u.latens_p50_ms || '–'}</td>
                  <td>{u.latens_p95_ms || '–'}</td>
                  <td>{u.pris_usd ? `$${u.pris_usd.toFixed(4)}` : '–'}</td>
                  <td>{tid(u.sidste_ok)}</td>
                </tr>
              ))}
              {!(historik?.udbydere ?? []).length && (
                <tr><td colSpan={10}>Ingen kald i vinduet.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
