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
  // Undertabs (3/11-2026): det gamle MC havde underfaner med felt-kategorier —
  // Sind → Bevidsthed / Sjæl / Kognition. Strukturen kommer FRA hub-indexet, så
  // fane-træet kun findes ét sted; ellers kan de to lister drive fra hinanden.
  // Tom subTab = sektionens default; en ukendt værdi falder tilbage på den første.
  const [subTab, setSubTab] = useState<string>('')
  const tabs = active?.tabs ?? []
  const effektivTab = tabs.some((t) => t.tab === subTab) ? subTab : (tabs[0]?.tab ?? '')

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
      {tabs.length > 0 && (
        <nav className="jm-subtabs" role="tablist" aria-label={`${active?.label ?? ''} undertabs`}>
          {tabs.map((t) => (
            <button
              key={t.tab}
              type="button"
              role="tab"
              aria-selected={effektivTab === t.tab}
              className={`jm-subtab ${effektivTab === t.tab ? 'active' : ''}`}
              onClick={() => setSubTab(t.tab)}
            >
              {t.label}
            </button>
          ))}
        </nav>
      )}
      <LivePulseLine config={config} onLive={setLive} />
      <div className="jm-body">
        <Section
          key={`${tab}:${effektivTab}`}
          config={config}
          section={tab}
          tab={effektivTab}
          ready={active?.ready ?? false}
        />
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

/** Én sektion: ren visning + AVANCERET-toggle (rå projektion). `tab` vælger en
 *  undertab — hver undertab er sin egen gruppe på serveren, så payloaden bliver
 *  2-36 KB i stedet for hele surfaces-dicten. */
function Section({ config, section, tab, ready }: {
  config?: ApiConfig
  section: string
  tab?: string
  ready: boolean
}) {
  const [advanced, setAdvanced] = useState(false)
  const { data, loading, error, refresh } = usePollWhenVisible(
    () => getMindSection(config!, section, tab), POLL_MS, !!config && ready,
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
  // Overflade-grupper (Sind → Bevidsthed/Sjæl/Kognition, plus Kroppen, Tråde,
  // Relation): de samme 72 kognitive overflader som det gamle MC's underfaner
  // viste, delt op så én hentning er 2-36 KB i stedet for 110 KB. Detektion på
  // FORMEN, ikke på sektionsnavnet — en ny gruppe virker uden at røre denne fil.
  if (data.surfaces && typeof data.surfaces === 'object') {
    return <SurfacesView data={data} />
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
  // 3/11-2026: agentur, council og skills har været fuldt projiceret hele tiden,
  // men SectionView havde ingen gren for dem — så de faldt til rå JSON. Det var
  // ikke manglende data, det var manglende visning.
  if (section === 'agency') return <AgencyView data={data} />
  if (section === 'skills') return <SkillsView data={data} />
  if (section === 'council') return <CouncilView data={data} />
  if (section === 'memory') return <MemoryView data={data} />
  if (section === 'reflection') return <ReflectionView data={data} />
  if (section === 'lab') return <LabView data={data} />
  if (section === 'hardening') return <HardeningView data={data} />
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

interface AgencyNode {
  id: string
  label: string
  kind: string
  summary?: string
  state?: string
}
interface AgencyBridge {
  source: string
  target: string
  status: string
  summary?: string
}
interface AgencyMap {
  summary?: Record<string, number>
  nodes?: AgencyNode[]
  bridges?: AgencyBridge[]
  darkEdges?: unknown[]
  questions?: unknown[]
  error?: string
}
interface AgentRosterEntry {
  model_key: string
  provider: string
  model: string
  status: string
  last_run_at?: string
  current_activity?: string
  role?: string
}

/**
 * Agentur — hvad der er forbundet med hvad, og hvem der faktisk kører.
 *
 * Kortet er Centralens eget: 9 noder og 13 broer med `state`/`status`. Det var
 * projiceret hele tiden, men faldt til rå JSON fordi SectionView ikke havde en
 * gren for det. Broerne vises som par, ikke som graf — en graf uden layout-motor
 * er en liste med ekstra skridt.
 */
function AgencyView({ data }: { data: Record<string, unknown> }) {
  const map = (data.map ?? {}) as AgencyMap
  const agents = (data.agents ?? {}) as {
    roster?: AgentRosterEntry[]
    dispatches?: { total?: number; by_status?: Record<string, number> }
    windows?: Record<string, { calls?: number; cost_usd?: number }>
    error?: string
  }
  if (map.error) return <div className="jm-error">Agentur-kortet fejlede: {map.error}</div>
  const s = map.summary ?? {}
  const noder = map.nodes ?? []
  const broer = map.bridges ?? []
  const roster = agents.roster ?? []
  const aktive = roster.filter((r) => r.status && r.status !== 'inactive')
  const iDag = agents.windows?.today
  const dispatchTotal = Number(agents.dispatches?.total ?? 0)

  return (
    <>
      <div className="jm-stat-row">
        <Stat label="noder" value={String(s.nodes ?? noder.length)} />
        <Stat label="broer" value={String(s.bridges ?? broer.length)} />
        <Stat
          label="mørke kanter"
          value={String(s.dark_edges ?? (map.darkEdges ?? []).length)}
          tone={Number(s.dark_edges ?? 0) > 0 ? 'yellow' : 'green'}
        />
        <Stat label="agenter aktive" value={`${aktive.length}/${roster.length}`} />
      </div>

      <div className="jm-section-sub">Hvad er forbundet</div>
      <div className="jm-grid">
        {noder.map((n) => (
          <div key={n.id} className={`jm-card ${n.state === 'active' ? 'on' : 'off'}`}>
            <div className="jm-card-title">
              <span className={`jm-dot ${n.state === 'active' ? 'on' : 'off'}`} />
              {n.label}
              <span className="jm-dim">{n.kind}</span>
            </div>
            {n.summary && <div className="jm-card-sub">{n.summary}</div>}
          </div>
        ))}
      </div>

      {broer.length > 0 && (
        <>
          <div className="jm-section-sub">{broer.length} broer</div>
          <div className="jm-feed">
            {broer.map((b, i) => (
              <div key={`${b.source}-${b.target}-${i}`} className="jm-feed-row">
                <span className={`jm-dot ${b.status === 'connected' ? 'on' : 'off'}`} />
                <b>{b.source}</b> <span className="jm-dim">→</span> <b>{b.target}</b>
                <span className="jm-dim">{b.status}</span>
              </div>
            ))}
          </div>
        </>
      )}

      <div className="jm-section-sub">
        Agenter · {dispatchTotal} dispatches{iDag ? ` · ${iDag.calls ?? 0} kald i dag` : ''}
      </div>
      {roster.length === 0
        ? <div className="jm-dim">Ingen agenter i rosteret.</div>
        : (
          <div className="jm-feed">
            {roster.slice(0, 20).map((r) => (
              <div key={r.model_key} className="jm-feed-row">
                <span className={`jm-dot ${r.status && r.status !== 'inactive' ? 'on' : 'off'}`} />
                <b>{r.model}</b>
                <span className="jm-dim">{r.provider}</span>
                <span className="jm-dim">{r.status}</span>
                {r.current_activity && <span className="jm-dim">{r.current_activity}</span>}
              </div>
            ))}
          </div>
        )}
    </>
  )
}

interface SkillEntry {
  name: string
  description?: string
  use_when?: string
  tags?: string[]
  readonly?: boolean
  has_scripts?: boolean
  has_templates?: boolean
  has_references?: boolean
}

/**
 * Skills — hvad han kan, søgbart.
 *
 * 70 skills med tags. Uden et filter er listen ubrugelig som oversigt, så
 * søgefeltet er ikke pynt: det er den eneste måde at finde én skill blandt 70
 * på en telefon. Filteret matcher navn, beskrivelse og tags.
 */
function SkillsView({ data }: { data: Record<string, unknown> }) {
  const [q, setQ] = useState('')
  const alle = (Array.isArray(data.skills) ? data.skills : []) as SkillEntry[]
  const soeg = q.trim().toLowerCase()
  const vist = soeg
    ? alle.filter((s) =>
      s.name.toLowerCase().includes(soeg)
      || (s.description ?? '').toLowerCase().includes(soeg)
      || (s.tags ?? []).some((t) => t.toLowerCase().includes(soeg)))
    : alle
  const medScripts = alle.filter((s) => s.has_scripts).length

  return (
    <>
      <div className="jm-stat-row">
        <Stat label="skills" value={String(data.skill_count ?? alle.length)} />
        <Stat label="med scripts" value={String(medScripts)} />
        <Stat label="tags" value={String((data.all_tags as string[] | undefined)?.length ?? 0)} />
      </div>
      <input
        className="jm-search"
        type="search"
        value={q}
        placeholder="søg i skills…"
        onChange={(e) => setQ(e.target.value)}
        aria-label="Søg i skills"
      />
      <div className="jm-section-sub">
        {soeg ? `${vist.length} af ${alle.length} matcher «${q.trim()}»` : `${alle.length} skills`}
      </div>
      <div className="jm-grid">
        {vist.slice(0, 60).map((s) => (
          <div key={s.name} className="jm-card">
            <div className="jm-card-title">
              <span className={`jm-dot ${s.has_scripts ? 'on' : 'off'}`} />
              {s.name}
            </div>
            {s.description && <div className="jm-card-sub">{s.description.slice(0, 180)}</div>}
            {(s.tags ?? []).length > 0 && (
              <div className="jm-card-sub jm-dim">{(s.tags ?? []).slice(0, 6).join(' · ')}</div>
            )}
          </div>
        ))}
      </div>
      {vist.length > 60 && (
        <div className="jm-dim">Viser 60 af {vist.length} — indsnævr søgningen.</div>
      )}
    </>
  )
}

interface CouncilData {
  convocations?: number
  deadlocks?: number
  escalations?: number
  roles?: Record<string, number>
  split?: Record<string, number>
  recent?: { topic?: string; outcome?: string; at?: string }[]
  window?: string
  note?: string
}

/**
 * Council — hvad der blev rådført om, og hvor det gik i hårdknude.
 *
 * Empty-safe med vilje: `council_convene` kan være tom indtil WS-C, og en tom
 * fane skal sige det højt i stedet for at se ud som en fejl.
 */
function CouncilView({ data }: { data: Record<string, unknown> }) {
  const c = data as CouncilData
  const roller = Object.entries(c.roles ?? {})
  const recent = c.recent ?? []
  const tom = !c.convocations && !c.deadlocks && !c.escalations && recent.length === 0
  if (tom) {
    return (
      <div className="jm-section-sub">
        Ingen councils i vinduet «{c.window ?? 'i dag'}».
        {c.note && <div className="jm-dim">{c.note}</div>}
      </div>
    )
  }
  return (
    <>
      <div className="jm-stat-row">
        <Stat label="indkaldelser" value={String(c.convocations ?? 0)} />
        <Stat label="hårdknuder" value={String(c.deadlocks ?? 0)} tone={Number(c.deadlocks ?? 0) > 0 ? 'yellow' : undefined} />
        <Stat label="eskaleringer" value={String(c.escalations ?? 0)} />
      </div>
      {roller.length > 0 && (
        <>
          <div className="jm-section-sub">Roller</div>
          <div className="jm-feed">
            {roller.map(([navn, antal]) => (
              <div key={navn} className="jm-feed-row">
                <b>{navn}</b><span className="jm-dim">{antal}</span>
              </div>
            ))}
          </div>
        </>
      )}
      {recent.length > 0 && (
        <>
          <div className="jm-section-sub">Seneste</div>
          <div className="jm-feed">
            {recent.slice(0, 12).map((r, i) => (
              <div key={i} className="jm-feed-row">
                <b>{r.topic ?? '—'}</b>
                <span className="jm-dim">{r.outcome ?? ''}</span>
              </div>
            ))}
          </div>
        </>
      )}
    </>
  )
}

interface BodyMemory {
  snapshot_count?: number
  latest?: { context?: string; sensation?: string; intensity?: number; state?: string; strain_level?: string; timestamp?: string }
  summary?: string
  error?: string
}
interface Density {
  total_notes?: number
  promotable_count?: number
  promoted_count?: number
  promotion_threshold?: number
  summary?: string
  error?: string
}
interface Recall {
  summary?: string
  stats?: { total?: number; window_hours?: number; by_tool?: Record<string, number> }
  error?: string
}
interface Experiential {
  active?: boolean
  status?: string
  total_count?: number
  summary?: string
  error?: string
}

/**
 * Hukommelse — hvad han husker, og hvad der er på vej til at blive glemt.
 *
 * Fire kilder, hver med sin egen ærlighed: krops-hukommelsen har 200 snapshots,
 * density kan være tom uden at det er en fejl, og experiential kræver en
 * bruger-scope den ikke har her. En tom kilde skal SIGE det — ikke se ud som
 * en fejl, og ikke skjule de tre andre.
 */
function MemoryView({ data }: { data: Record<string, unknown> }) {
  const body = (data.body ?? {}) as BodyMemory
  const density = (data.density ?? {}) as Density
  const recall = (data.recall ?? {}) as Recall
  const exp = (data.experiential ?? {}) as Experiential
  const latest = body.latest

  return (
    <>
      <div className="jm-stat-row">
        <Stat label="krops-minder" value={String(body.snapshot_count ?? 0)} />
        <Stat label="density-noter" value={String(density.total_notes ?? 0)} />
        <Stat
          label="modne til forfremmelse"
          value={String(density.promotable_count ?? 0)}
          tone={Number(density.promotable_count ?? 0) > 0 ? 'green' : undefined}
        />
        <Stat label="recall-huller" value={String(recall.stats?.total ?? 0)} />
      </div>

      {latest && (
        <>
          <div className="jm-section-sub">Seneste fornemmelse</div>
          <div className="jm-card">
            <div className="jm-card-title">
              <span className={`jm-dot ${latest.state === 'steady' ? 'on' : 'off'}`} />
              {latest.context ?? 'krop'}
              <span className="jm-dim">{latest.state}</span>
            </div>
            <div className="jm-card-sub">
              {latest.sensation}
              {typeof latest.intensity === 'number' && ` · intensitet ${latest.intensity}`}
              {latest.strain_level && ` · belastning ${latest.strain_level}`}
            </div>
          </div>
        </>
      )}

      <div className="jm-section-sub">Huller i søgningen · {recall.stats?.window_hours ?? 24} t</div>
      <div className="jm-dim">{recall.summary ?? 'ingen telemetri'}</div>

      {density.summary && (
        <>
          <div className="jm-section-sub">Density</div>
          <div className="jm-dim">
            {density.summary}
            {Number(density.promoted_count ?? 0) > 0 && ` · ${density.promoted_count} forfremmet`}
          </div>
        </>
      )}

      {exp.active === false && (
        <div className="jm-dim">
          Erfarings-hukommelse: {exp.summary ?? exp.status ?? 'ikke tilgængelig'}
        </div>
      )}
    </>
  )
}

interface ReflectionData {
  mode?: string
  summary?: { active_today?: boolean; current_state?: string; chronicle_summary_available?: boolean }
  items?: { kind?: string; chronicle_summary?: string; nudge_after_count?: number }[]
  allowed_effects?: string[]
}

/**
 * Refleksion — dagens slot og hvad den må røre.
 *
 * `allowed_effects` er det vigtigste felt: det siger hvad refleksionen HAR lov
 * til. Uden det ser en refleksion ud som om den kan skrive i hukommelsen, og
 * det er præcis den slags tavs magt §8 findes for at forhindre.
 */
function ReflectionView({ data }: { data: Record<string, unknown> }) {
  const r = data as ReflectionData
  const s = r.summary ?? {}
  const items = r.items ?? []
  return (
    <>
      <div className="jm-stat-row">
        <Stat label="aktiv i dag" value={s.active_today ? 'ja' : 'nej'} tone={s.active_today ? 'green' : undefined} />
        <Stat label="tilstand" value={String(s.current_state ?? '—').replace(/_/g, ' ')} />
        <Stat label="chronicle" value={s.chronicle_summary_available ? 'tilgængelig' : 'fri hånd'} />
      </div>
      {items.map((it, i) => (
        <div key={i} className="jm-card">
          <div className="jm-card-title">{it.kind ?? 'refleksion'}</div>
          {it.chronicle_summary && <div className="jm-card-sub">{it.chronicle_summary}</div>}
        </div>
      ))}
      {(r.allowed_effects ?? []).length > 0 && (
        <>
          <div className="jm-section-sub">Må røre</div>
          <div className="jm-feed">
            {(r.allowed_effects ?? []).map((e) => (
              <div key={e} className="jm-feed-row"><span className="jm-dot on" />{e.replace(/_/g, ' ')}</div>
            ))}
          </div>
        </>
      )}
    </>
  )
}

interface CostWindow {
  calls?: number
  input_tokens?: number
  output_tokens?: number
  cache_hit_pct?: number
  cost_usd?: number
}

/**
 * Lab — hvad det koster, og hvad der er tilbage.
 *
 * Saldoen staar foerst: et forbrugstal uden en saldo siger ikke om der er
 * raad. `deepseek_balance_usd` er den eneste maalte saldo i systemet.
 */
function LabView({ data }: { data: Record<string, unknown> }) {
  const windows = (data.windows ?? {}) as Record<string, CostWindow>
  const iDag = windows.today ?? {}
  const syv = windows['7d'] ?? {}
  const saldo = data.deepseek_balance_usd
  const breakdown = (Array.isArray(data.breakdown) ? data.breakdown : []) as
    { provider?: string; calls?: number; cost_usd?: number }[]
  return (
    <>
      <div className="jm-stat-row">
        <Stat
          label="saldo (USD)"
          value={typeof saldo === 'number' ? `$${saldo.toFixed(2)}` : '—'}
          tone={typeof saldo === 'number' && saldo < 5 ? 'red' : undefined}
        />
        <Stat label="kald i dag" value={String(iDag.calls ?? 0)} />
        <Stat label="i dag (USD)" value={`$${Number(iDag.cost_usd ?? 0).toFixed(2)}`} />
        <Stat label="7 dage (USD)" value={`$${Number(syv.cost_usd ?? 0).toFixed(2)}`} />
      </div>
      <div className="jm-section-sub">
        Cache-hit {iDag.cache_hit_pct ?? 0}% · {(iDag.input_tokens ?? 0).toLocaleString('da-DK')} ind /{' '}
        {(iDag.output_tokens ?? 0).toLocaleString('da-DK')} ud
      </div>
      {breakdown.length > 0 && (
        <>
          <div className="jm-section-sub">Pr. provider</div>
          <div className="jm-feed">
            {breakdown.slice(0, 12).map((b, i) => (
              <div key={`${b.provider}-${i}`} className="jm-feed-row">
                <b>{b.provider ?? '—'}</b>
                <span className="jm-dim">{b.calls ?? 0} kald</span>
                <span className="jm-dim">${Number(b.cost_usd ?? 0).toFixed(2)}</span>
              </div>
            ))}
          </div>
        </>
      )}
    </>
  )
}

interface GovernanceFlag {
  key: string
  label: string
  kind: string
  dangerous?: boolean
  value?: unknown
}

/**
 * Hærdning — governance-flag og hvad de værner.
 *
 * `dangerous` staar frem med vilje: et flag der kan slaa lag-4-adaptation til
 * er ikke en indstilling som alle andre, og det skal ikke se saadan ud.
 */
function HardeningView({ data }: { data: Record<string, unknown> }) {
  const flags = (Array.isArray(data.flags) ? data.flags : []) as GovernanceFlag[]
  return (
    <>
      <div className="jm-stat-row">
        <Stat label="flag" value={String(data.count ?? flags.length)} />
        <Stat
          label="farlige"
          value={String(data.dangerous_count ?? 0)}
          tone={Number(data.dangerous_count ?? 0) > 0 ? 'yellow' : 'green'}
        />
      </div>
      <div className="jm-feed">
        {flags.map((f) => (
          <div key={f.key} className="jm-feed-row">
            <span className={`jm-dot ${f.value ? 'on' : 'off'}`} />
            <b>{f.label}</b>
            <span className="jm-dim">{f.kind}</span>
            {f.dangerous && <span className="jm-dim">⚠ farlig</span>}
          </div>
        ))}
      </div>
    </>
  )
}

interface SurfaceData {
  active?: boolean
  summary?: string
  [k: string]: unknown
}

/** Én gruppe kognitive overflader — det gamle MC's Sjæl/Kognition-kort genopstået.
 *
 *  Hver overflade er et fladt dict med `active` + `summary` + en håndfuld tal.
 *  Det gamle UI viste dem som `Section` med `KV`-rækker; her er den samme form,
 *  fordi det er den der gør 20 kategorier læsbare uden at folde rå-laget ud.
 *
 *  `mangler` vises frem: forsvinder en overflade fra kilden, skal det kunne ses
 *  som et navn — ikke bare blive et hul der ser ud som om der aldrig var noget.
 */
function SurfacesView({ data }: { data: Record<string, unknown> }) {
  const surfaces = (data.surfaces ?? {}) as Record<string, SurfaceData>
  const mangler = (Array.isArray(data.mangler) ? data.mangler : []) as string[]
  const navne = Object.keys(surfaces)
  if (navne.length === 0) {
    return <div className="jm-section-sub">Ingen overflader i denne gruppe.</div>
  }
  return (
    <>
      <div className="jm-section-sub">
        {navne.length} overflader
        {mangler.length > 0 && (
          <span className="jm-dim"> · mangler: {mangler.join(', ')}</span>
        )}
      </div>
      <div className="jm-grid">
        {navne.map((navn) => {
          const s = surfaces[navn] ?? {}
          const aktiv = s.active !== false
          const felter = Object.entries(s)
            .filter(([k, v]) => k !== 'summary' && k !== 'active'
              && v !== null && v !== undefined && v !== '')
            .slice(0, 12)
          return (
            <div key={navn} className={`jm-card ${aktiv ? 'on' : 'off'}`}>
              <div className="jm-card-title">
                <span className={`jm-dot ${aktiv ? 'on' : 'off'}`} />
                {navn.replace(/_/g, ' ')}
                {!aktiv && <span className="jm-dim">idle</span>}
              </div>
              {s.summary && <div className="jm-card-sub">{String(s.summary)}</div>}
              {felter.length > 0 && (
                <div className="jm-kv">
                  {felter.map(([k, v]) => (
                    <div key={k} className="jm-kv-row">
                      <span className="jm-dim">{k.replace(/_/g, ' ')}</span>
                      <b>{formatVaerdi(v)}</b>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )
        })}
      </div>
    </>
  )
}

/** Kort, ærlig formatering: tal uden unødig præcision, og samlinger som ANTAL
 *  i stedet for en udskrift der ville sprænge kortet. */
function formatVaerdi(v: unknown): string {
  if (typeof v === 'number') return Number.isInteger(v) ? String(v) : v.toFixed(3)
  if (typeof v === 'boolean') return v ? 'ja' : 'nej'
  if (typeof v === 'string') return v.length > 160 ? `${v.slice(0, 160)}…` : v
  if (Array.isArray(v)) return `${v.length} elementer`
  if (v && typeof v === 'object') return `{${Object.keys(v as object).length} felter}`
  return String(v)
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
  {
    section: 'mind',
    label: 'Sind',
    ready: true,
    tabs: [
      { tab: 'bevidsthed', label: 'Bevidsthed' },
      { tab: 'sjael', label: 'Sjæl' },
      { tab: 'kognition', label: 'Kognition' },
    ],
  },
  { section: 'observability', label: 'Observabilitet', ready: true },
]
