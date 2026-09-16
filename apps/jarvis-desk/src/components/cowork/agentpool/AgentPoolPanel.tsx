import { useCallback, useEffect, useState } from 'react'
import type { ApiConfig } from '../../../lib/api'
import {
  getPoolListe, getPoolOpsummering, getPoolArbejde,
  type PoolAgent, type PoolListe, type PoolOpsummering,
  type AgentKoersel,
} from '../../../lib/agentPoolApi'
import { AgentInspector } from '../../panel/AgentInspector'

/**
 * Agent pool — hvem findes, hvad laver de, hvad kostede de.
 *
 * Bjørn 16/9-2026: «hans agent pool hvor jeg kan se og følge agenterne arbejde
 * totalt overview og interaktion og control».
 *
 * To ting er bevidst holdt fra hinanden:
 *
 *  - LISTEN er let (ét opslag, filtrerbar). DETALJEN hentes først når man
 *    åbner en agent. Den gamle flade berigede hver agent med fire ekstra
 *    opslag på forhånd — 306 agenter blev til over tolvhundrede forespørgsler.
 *  - «Værktøjer» har INGEN fane, fordi `agent_tool_calls` står tom i drift.
 *    En fane der altid er tom er et løfte man ikke kan holde; kørslerne med
 *    deres resuméer er det nærmeste sande.
 */
type Fane = 'oversigt' | 'agenter' | 'arbejde'

const FANER: { id: Fane; label: string }[] = [
  { id: 'oversigt', label: 'Oversigt' },
  { id: 'agenter', label: 'Agenter' },
  { id: 'arbejde', label: 'Seneste arbejde' },
]

const STATUSFILTRE = [
  { v: '', label: 'Alle' },
  { v: 'aktive', label: 'Aktive' },
  { v: 'completed', label: 'Gennemført' },
  { v: 'failed', label: 'Fejlet' },
  { v: 'cancelled', label: 'Annulleret' },
  { v: 'expired', label: 'Udløbet' },
]

function pct(v: number | null | undefined): string {
  if (v === null || v === undefined) return '–'
  return `${(Math.round(v * 1000) / 10).toLocaleString('da-DK')} %`
}

function varighed(s?: number): string {
  if (!s) return '–'
  if (s < 60) return `${s} s`
  if (s < 3600) return `${Math.round(s / 60)} min`
  return `${(s / 3600).toFixed(1)} t`
}

function tid(s?: string | null): string {
  if (!s) return '–'
  const d = new Date(s)
  return Number.isNaN(d.getTime()) ? String(s).slice(0, 16)
    : d.toLocaleString('da-DK', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })
}

export function AgentPoolPanel({ config }: { config?: ApiConfig }) {
  const [fane, setFane] = useState<Fane>('oversigt')
  const [status, setStatus] = useState('')
  const [soeg, setSoeg] = useState('')
  const [side, setSide] = useState(0)
  const [liste, setListe] = useState<PoolListe | null>(null)
  const [opsum, setOpsum] = useState<PoolOpsummering | null>(null)
  const [arbejde, setArbejde] = useState<AgentKoersel[]>([])
  const [aaben, setAaben] = useState<PoolAgent | null>(null)
  const [besked, setBesked] = useState('')
  const [henter, setHenter] = useState(false)

  const LOFT = 50

  const hent = useCallback(async () => {
    if (!config) return
    setHenter(true)
    const [l, o, a] = await Promise.allSettled([
      getPoolListe(config, { status, soeg, limit: LOFT, offset: side * LOFT }),
      getPoolOpsummering(config, 24),
      getPoolArbejde(config, 30),
    ])
    if (l.status === 'fulfilled') setListe(l.value)
    if (o.status === 'fulfilled') setOpsum(o.value)
    if (a.status === 'fulfilled') setArbejde(a.value.koersler ?? [])
    const døde = [l, o, a].filter((x) => x.status === 'rejected').length
    setBesked(døde ? `${døde} af 3 kilder svarede ikke` : '')
    setHenter(false)
  }, [config, status, soeg, side])

  useEffect(() => { void hent() }, [hent])

  if (!config) return <div className="mc-tom">Ingen forbindelse til serveren.</div>

  const v = opsum?.vindue

  return (
    <div className="mc agentpool">
      <div className="mc-top">
        <h2>Agent pool</h2>
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
            {f.id === 'agenter' && opsum?.agenter_i_alt ? ` (${opsum.agenter_i_alt})` : ''}
          </button>
        ))}
      </div>

      {fane === 'oversigt' && (
        <div className="ap-oversigt">
          <div className="cl-kort-raekke">
            <Kort navn="Agenter" vaerdi={opsum?.agenter_i_alt ?? 0}
                  under={`${opsum?.aktive_nu ?? 0} aktive nu`} />
            <Kort navn="Kørsler (24 t)" vaerdi={v?.koersler ?? 0}
                  under={`${v?.fejlede ?? 0} fejlede`} />
            <Kort navn="Fejlrate" vaerdi={pct(v?.fejlrate)} under="sidste døgn" />
            <Kort navn="Pris (24 t)" vaerdi={`$${(v?.pris_usd ?? 0).toFixed(4)}`}
                  under={`${(v?.tokens ?? 0).toLocaleString('da-DK')} tokens`} />
            <Kort navn="Grænser" vaerdi={opsum?.graenser?.samtidige ?? '–'}
                  under={`samtidige · dybde ${opsum?.graenser?.dybde ?? '–'}`} />
          </div>

          <h3>Fordeling</h3>
          <div className="ap-fordeling">
            <div>
              <h4>Status</h4>
              <ul>
                {Object.entries(opsum?.pr_status ?? {})
                  .sort((a, b) => b[1] - a[1])
                  .map(([s, n]) => <li key={s}><span>{s}</span><strong>{n}</strong></li>)}
              </ul>
            </div>
            <div>
              <h4>Roller</h4>
              <ul>
                {(opsum?.pr_rolle ?? []).map((r) => (
                  <li key={r.rolle}><span>{r.rolle}</span><strong>{r.antal}</strong></li>
                ))}
              </ul>
            </div>
            <div>
              <h4>Råd</h4>
              <ul>
                {Object.entries(opsum?.raad ?? {}).map(([s, n]) => (
                  <li key={s}><span>{s}</span><strong>{n}</strong></li>
                ))}
                {!Object.keys(opsum?.raad ?? {}).length && <li><span>ingen</span></li>}
              </ul>
            </div>
          </div>
        </div>
      )}

      {fane === 'agenter' && (
        <div className="ap-agenter">
          <div className="ap-filtre">
            {STATUSFILTRE.map((f) => (
              <button key={f.v} type="button" className={status === f.v ? 'aktiv' : ''}
                      aria-pressed={status === f.v}
                      onClick={() => { setStatus(f.v); setSide(0) }}>{f.label}</button>
            ))}
            <input type="search" placeholder="Søg i mål, rolle eller id" value={soeg}
                   aria-label="Søg"
                   onChange={(e) => { setSoeg(e.target.value); setSide(0) }} />
          </div>

          <p className="cl-note">
            Viser {liste?.vist ?? 0} af {liste?.i_alt ?? 0}.
          </p>

          <table className="mc-tabel">
            <thead>
              <tr><th>Rolle</th><th>Mål</th><th>Status</th><th>Kørsler</th>
                <th>Tokens</th><th>Pris</th><th>Varighed</th><th>Oprettet</th></tr>
            </thead>
            <tbody>
              {(liste?.agenter ?? []).map((a) => (
                <tr key={a.agent_id} onClick={() => setAaben(a)} className="ap-raekke"
                    title={a.agent_id}>
                  <td>{a.role || a.kind}</td>
                  <td className="ap-maal">{a.goal || '–'}</td>
                  <td className={a.status === 'failed' ? 'cl-daarlig' : ''}>{a.status}</td>
                  <td>{a.koersler}</td>
                  <td>{a.tokens.toLocaleString('da-DK')}</td>
                  <td>{a.pris_usd ? `$${a.pris_usd.toFixed(4)}` : '–'}</td>
                  <td>{varighed(a.varighed_s)}</td>
                  <td>{tid(a.created_at)}</td>
                </tr>
              ))}
              {!(liste?.agenter ?? []).length && <tr><td colSpan={8}>Ingen agenter i filteret.</td></tr>}
            </tbody>
          </table>

          {(liste?.i_alt ?? 0) > LOFT && (
            <div className="ap-sider">
              <button type="button" disabled={side === 0}
                      onClick={() => setSide((s) => Math.max(0, s - 1))}>Forrige</button>
              <span>Side {side + 1} af {Math.ceil((liste?.i_alt ?? 0) / LOFT)}</span>
              <button type="button"
                      disabled={(side + 1) * LOFT >= (liste?.i_alt ?? 0)}
                      onClick={() => setSide((s) => s + 1)}>Næste</button>
            </div>
          )}
        </div>
      )}

      {fane === 'arbejde' && (
        <div className="ap-arbejde">
          <p className="cl-note">
            Kørslerne er den eneste fyldte kilde: værktøjskald bogføres ikke i drift.
          </p>
          <table className="mc-tabel">
            <thead>
              <tr><th>Tid</th><th>Rolle</th><th>Model</th><th>Udfald</th>
                <th>Varighed</th><th>Resultat</th></tr>
            </thead>
            <tbody>
              {arbejde.map((k) => (
                <tr key={k.run_id}>
                  <td>{tid(k.started_at)}</td>
                  <td>{k.role || '–'}</td>
                  <td className="cl-model">{k.model || '–'}</td>
                  <td className={k.status === 'failed' ? 'cl-daarlig' : ''}>{k.status}</td>
                  <td>{varighed(k.varighed_s)}</td>
                  <td className="cl-besked" title={k.output_summary || k.failure_reason || ''}>
                    {k.output_summary || k.failure_reason || '–'}
                  </td>
                </tr>
              ))}
              {!arbejde.length && <tr><td colSpan={6}>Ingen kørsler endnu.</td></tr>}
            </tbody>
          </table>
        </div>
      )}

      {aaben && (
        <div className="ap-detalje" role="dialog" aria-label={`Agent ${aaben.role || aaben.kind || aaben.agent_id}`}>
          <div className="ap-detalje-top">
            <h3>Agentdetaljer</h3>
            <button type="button" onClick={() => setAaben(null)} aria-label="Luk">✕</button>
          </div>
          <AgentInspector
            config={config}
            agent={{
              agentId: aaben.agent_id,
              role: aaben.role || aaben.kind,
              goal: aaben.goal,
              status: aaben.status,
              dispatchToolUseId: `agent-pool:${aaben.agent_id}`,
            }}
            canMessage
            onChanged={hent}
          />
        </div>
      )}
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
