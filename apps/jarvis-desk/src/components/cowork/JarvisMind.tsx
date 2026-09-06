import { useEffect, useState } from 'react'
import { Code2 } from 'lucide-react'
import type { ApiConfig, MindIndexEntry, CentralFeedItem } from '../../lib/api'
import { actOnDecision, getMindIndex, getMindSection } from '../../lib/api'
import { subscribeCentralStream } from '../../lib/centralStream'
import { usePollWhenVisible } from '../../hooks/usePollWhenVisible'
import { PresenceDot } from '../shell/PresenceDot'
import { ConnectionPill } from '../shell/ConnectionPill'

/** Jarvis Mind — ÉT live-vindue mod Centralen (ét ground truth), ikke 190 MC-polls.
 *
 *  Filosofien (Bjørn 2026-06-23): MC var over-teknisk og rodet. Jarvis Mind er levende +
 *  grafisk + realtime (føles som Central-feltet) med "magi tilladt så længe vi kan se det":
 *  ren menneskelig visning som default, en AVANCERET-toggle folder rå-laget ud.
 *
 *  Data: sub-navbar-fanerne kommer fra Centralens hub-index (/central/mind). Den aktive fane
 *  hentes fra hub'en (stream-when-visible). En SSE-stream (/central/stream) giver den LEVENDE
 *  puls — nerve-fyringer der ruller + en pulserende prik — så det føles realtime. Alt poller/
 *  streamer KUN mens panelet er åbent (komponenten unmountes når du forlader zonen). */

const POLL_MS = 20_000

export function JarvisMind({ config }: { config?: ApiConfig }) {
  const { data: idx } = usePollWhenVisible(
    () => getMindIndex(config!), 60_000, !!config,
  )
  const sections: MindIndexEntry[] = idx?.index ?? FALLBACK_TABS
  const [tab, setTab] = useState<string>('mind')
  const active = sections.find((s) => s.section === tab) ?? sections[0]

  // `live` ændrer sig SJÆLDENT (connect/disconnect) → drives op fra pulse-linjen, så de KONSTANTE
  // nerve-fyringer (items) bliver isoleret i LivePulseLine og IKKE re-renderer sektionerne.
  const [live, setLive] = useState(false)

  return (
    <div className="jarvis-mind">
      {/* Samme app-header som chat/code mode (Bjørn 2026-06-23) — sub-navbar UNDER den. */}
      <div className="chatview-head">
        <div className="chatview-head-left">
          <PresenceDot status={live ? 'working' : 'idle'} /> <span className="chat-title">Jarvis Mind</span>
        </div>
        <div className="chatview-head-right">
          {config && <ConnectionPill config={{ apiBaseUrl: config.apiBaseUrl, authToken: config.authToken ?? null }} />}
        </div>
      </div>
      <nav className="jm-tabs" role="tablist" aria-label="Jarvis Mind">
        {sections.map((s) => (
          <button
            key={s.section}
            type="button"
            role="tab"
            aria-selected={tab === s.section}
            className={`jm-tab ${tab === s.section ? 'active' : ''} ${s.ready ? '' : 'pending'}`}
            onClick={() => setTab(s.section)}
          >
            {s.label}
          </button>
        ))}
      </nav>
      <LivePulseLine config={config} onLive={setLive} />
      <div className="jm-body">
        <Section key={tab} config={config} section={tab} ready={active?.ready ?? false} />
      </div>
    </div>
  )
}

/** Den levende puls fra den DELTE Central-stream. Ejer sin EGEN items-state (konstant
 *  opdateret) så de hyppige fyringer kun re-renderer DENNE linje — ikke sektionerne. Løfter
 *  kun `live` op (connect/disconnect = sjældent). */
function LivePulseLine({ config, onLive }: { config?: ApiConfig; onLive: (v: boolean) => void }) {
  const [items, setItems] = useState<CentralFeedItem[]>([])
  const [live, setLive] = useState(false)
  useEffect(() => {
    if (!config) return
    setLive(true); onLive(true)
    const unsub = subscribeCentralStream(
      config,
      (it) => setItems((prev) => [it, ...prev].slice(0, 6)),
      () => { setLive(false); onLive(false) },
    )
    return () => { unsub(); setLive(false); onLive(false) }
  }, [config, onLive])
  const latest = items[0]
  return (
    <div className="jm-pulse" aria-live="off">
      <span className={`jm-pulse-dot ${live ? 'live' : ''}`} />
      <span className="jm-pulse-text">
        {latest
          ? <><b>{latest.cluster}</b>/{latest.nerve} <span className="jm-dim">{latest.decision || latest.kind}</span></>
          : <span className="jm-dim">{live ? 'lytter på nervesystemet…' : 'forbinder…'}</span>}
      </span>
    </div>
  )
}

/** Én sektion: ren visning + AVANCERET-toggle (rå projektion). */
function Section({ config, section, ready }: { config?: ApiConfig; section: string; ready: boolean }) {
  const [advanced, setAdvanced] = useState(false)
  const { data, loading, error, refresh } = usePollWhenVisible(
    () => getMindSection(config!, section), POLL_MS, !!config && ready,
  )
  if (!ready) return <Placeholder section={section} />
  if (error) return <div className="jm-section jm-error">Kunne ikke hente: {error}</div>
  if (!data) return <div className="jm-section jm-dim">{loading ? 'Henter…' : 'Ingen data.'}</div>
  return (
    <div className="jm-section">
      <div className="jm-section-head">
        <span>{loading ? <span className="jm-dim">opdaterer…</span> : ''}</span>
        <button type="button" className={`jm-adv ${advanced ? 'on' : ''}`}
          onClick={() => setAdvanced((a) => !a)} title="Avanceret: rå projektion">
          <Code2 size={13} /> avanceret
        </button>
      </div>
      {advanced
        ? <pre className="jm-raw">{JSON.stringify(data, null, 2)}</pre>
        : <SectionView section={section} data={data} config={config} onActed={refresh} />}
    </div>
  )
}

interface Beslutning {
  kind: string
  id: string
  text: string
  why?: string
  actions?: string[]
}

const HANDLING_TEKST: Record<string, string> = {
  approve: 'Godkend',
  reject: 'Afvis',
  // Et livsprojekt beder ikke om lov — det er noget han HAR sat sig for. Derfor
  // «det er i orden», ikke «godkend»: man siger god for det, man tillader det ikke.
  endorse: 'Det er i orden',
  abandon: 'Læg den fra dig',
}

/**
 * Beslutninger — den ENESTE sektion der ikke bare informerer.
 *
 * De øvrige faner viser hvad han tænker; denne venter på et svar. Ruterne har
 * ligget der hele tiden, men uden knap udløb 31 initiativer ubesvarede. Kortet
 * fjernes med det samme ved tryk (serveren er stadig sandheden — pollen henter
 * listen igen), for et kort der bliver stående føles som om trykket ikke landede.
 */
function DecisionsView({ data, config, onActed }: {
  data: Record<string, unknown>
  config?: ApiConfig
  onActed?: () => void
}) {
  const [svaret, setSvaret] = useState<string[]>([])
  const [fejl, setFejl] = useState<string | null>(null)
  const [travl, setTravl] = useState<string | null>(null)

  const alle = (Array.isArray(data.items) ? data.items : []) as Beslutning[]
  const items = alle.filter((d) => d?.id && d?.text && !svaret.includes(d.id))
  const initiativer = items.filter((d) => d.kind === 'initiative')
  const projekter = items.filter((d) => d.kind === 'life_project')
  const ubesvarede = Number(
    (data.queue as { expired_unanswered?: unknown } | undefined)?.expired_unanswered ?? 0,
  )

  async function svar(d: Beslutning, action: string) {
    if (!config) return
    setTravl(d.id); setFejl(null)
    setSvaret((prev) => [...prev, d.id])
    try {
      const res = await actOnDecision(config, d.kind, d.id, action)
      if (!res.ok) setFejl(res.error || 'Kunne ikke svare på forslaget')
    } catch (e) {
      setFejl(e instanceof Error ? e.message : 'Kunne ikke svare på forslaget')
    } finally {
      setTravl(null); onActed?.()
    }
  }

  function kort(d: Beslutning) {
    return (
      <div key={d.id} className="jm-card jm-decision">
        <div className="jm-card-title">{d.text}</div>
        {d.why && <div className="jm-card-sub">{d.why}</div>}
        <div className="jm-decide">
          {(d.actions ?? []).map((a) => (
            <button key={a} type="button" className="jm-decide-btn"
              disabled={travl === d.id} onClick={() => void svar(d, a)}>
              {HANDLING_TEKST[a] ?? a}
            </button>
          ))}
        </div>
      </div>
    )
  }

  if (items.length === 0) {
    return <div className="jm-section-sub">Intet venter på dig lige nu.</div>
  }

  return (
    <>
      {fejl && <div className="jm-error">{fejl}</div>}
      {initiativer.length > 0 && (
        <>
          <div className="jm-section-sub">Han foreslår</div>
          <div className="jm-grid">{initiativer.map(kort)}</div>
        </>
      )}
      {projekter.length > 0 && (
        <>
          <div className="jm-section-sub">Det han arbejder hen imod</div>
          <div className="jm-grid">{projekter.map(kort)}</div>
        </>
      )}
      {ubesvarede > 0 && (
        <div className="jm-dim jm-unanswered">
          {ubesvarede} tidligere forslag udløb uden svar.
        </div>
      )}
    </>
  )
}

/** Ren, menneskelig visning pr. sektion. Ukendte former falder til rå (men toggle findes). */
function SectionView({ section, data, config, onActed }: {
  section: string
  data: Record<string, unknown>
  config?: ApiConfig
  onActed?: () => void
}) {
  if (section === 'decisions') {
    return <DecisionsView data={data} config={config} onActed={onActed} />
  }
  if (section === 'mind') {
    const systems = (data.systems as { system: string; active: boolean; summary?: string }[]) ?? []
    return (
      <>
        <div className="jm-section-sub">{String(data.summary ?? `${systems.length} systemer`)}</div>
        <div className="jm-grid">
          {systems.map((s) => (
            <div key={s.system} className={`jm-card ${s.active ? 'on' : 'off'}`}>
              <div className="jm-card-title"><span className={`jm-dot ${s.active ? 'on' : 'off'}`} />{s.system.replace(/_/g, ' ')}</div>
              {s.summary && <div className="jm-card-sub">{s.summary}</div>}
            </div>
          ))}
        </div>
      </>
    )
  }
  if (section === 'overview') {
    const cov = (data.coverage as Record<string, number>) ?? {}
    return (
      <div className="jm-stat-row">
        <Stat label="Status" value={String(data.status ?? '—')} tone={String(data.status ?? '')} />
        <Stat label="Nerver" value={String(cov.nerves ?? '—')} />
        <Stat label="Clusters" value={String(cov.clusters ?? '—')} />
        <Stat label="Sikkerhed" value={String(cov.security_clusters ?? '—')} />
      </div>
    )
  }
  if (section === 'observability') {
    const feed = (data.feed as CentralFeedItem[]) ?? []
    const inc = (data.incidents as { severity: string; nerve: string; message: string }[]) ?? []
    return (
      <>
        <HollowPromises data={data.hollow_promises as HollowCensus | undefined} />
        <div className="jm-section-sub">{inc.length} uløste flag · seneste fyringer:</div>
        <div className="jm-feed">
          {feed.slice(0, 24).map((f, i) => (
            <div key={i} className="jm-feed-row">
              <span className={`jm-dot ${f.decision === 'red' ? 'off' : 'on'}`} />
              <b>{f.cluster}</b>/{f.nerve} <span className="jm-dim">{f.decision || f.kind}</span>
            </div>
          ))}
        </div>
      </>
    )
  }
  return <pre className="jm-raw">{JSON.stringify(data, null, 2)}</pre>
}

interface HollowCensus {
  available?: boolean
  window_hours?: number
  models?: { model: string; turns: number; hollow: number; hollow_pct: number }[]
  hollow_total?: number
  guard_detected?: number
  escaped?: number
}

/**
 * Tomme løfter — svar der annoncerer et skridt og ikke tager det.
 *
 * Bjørn 5/9-2026: «Centralen skal kunne tælle de tomme løfter.» Backenden
 * talte dem samme dag, men denne fane renderede kun feed + flag-antal, så
 * tallet var usynligt uden at folde rå-laget ud. Data uden visning er samme
 * sygdom som ingen data.
 *
 * SLAP FORBI står først og alene. Værnet fanger en del af dem, og et værn der
 * fanger 12 af 31 ser perfekt ud hvis man kun tæller sine egne fangster — så
 * differencen er det ene tal der er værd at kigge på.
 */
function HollowPromises({ data }: { data?: HollowCensus }) {
  if (!data?.available) return null
  const modeller = (data.models ?? []).filter((m) => m.turns >= 3)
  const slap = Number(data.escaped ?? 0)
  return (
    <div className="jm-hollow">
      <div className="jm-section-sub">
        Tomme løfter · {data.window_hours ?? 24} t
      </div>
      <div className="jm-stats">
        <Stat label="slap forbi værnet" value={String(slap)} tone={slap > 0 ? 'warn' : 'ok'} />
        <Stat label="i alt" value={String(data.hollow_total ?? 0)} />
        <Stat label="grebet" value={String(data.guard_detected ?? 0)} />
      </div>
      {modeller.length > 0 && (
        <div className="jm-hollow-models">
          {modeller.map((m) => (
            <div key={m.model} className="jm-hollow-row">
              <span className="jm-hollow-name">{m.model}</span>
              <span className="jm-hollow-bar">
                <span className="jm-hollow-fill" style={{ width: `${Math.min(m.hollow_pct, 100)}%` }} />
              </span>
              <span className="jm-hollow-pct">{m.hollow_pct}%</span>
              <span className="jm-dim jm-hollow-abs">{m.hollow}/{m.turns}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function Stat({ label, value, tone }: { label: string; value: string; tone?: string }) {
  return (
    <div className={`jm-stat ${tone ? `tone-${tone}` : ''}`}>
      <div className="jm-stat-value">{value}</div>
      <div className="jm-stat-label">{label}</div>
    </div>
  )
}

function Placeholder({ section }: { section: string }) {
  return (
    <div className="jm-section jm-placeholder">
      <p>Denne fane er endnu ikke flyttet fra Mission Control.</p>
      <p className="jm-dim">Følger dæknings-kontrakten — projiceres via Centralen og verificeres mod gammel MC "{section}" inden MC udfases.</p>
    </div>
  )
}

const FALLBACK_TABS: MindIndexEntry[] = [
  { section: 'overview', label: 'Oversigt', ready: true },
  { section: 'mind', label: 'Sind', ready: true },
  { section: 'observability', label: 'Observabilitet', ready: true },
]
