import { useEffect, useRef, useState } from 'react'
import { Code2 } from 'lucide-react'
import type { ApiConfig, MindIndexEntry, CentralFeedItem } from '../../lib/api'
import { getMindIndex, getMindSection, streamCentral } from '../../lib/api'
import { usePollWhenVisible } from '../../hooks/usePollWhenVisible'

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

  return (
    <div className="jarvis-mind">
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
      <LivePulse config={config} />
      <div className="jm-body">
        <Section key={tab} config={config} section={tab} ready={active?.ready ?? false} />
      </div>
    </div>
  )
}

/** Levende puls fra Centralens SSE-stream: pulserende prik + rullende seneste nerve-fyringer. */
function LivePulse({ config }: { config?: ApiConfig }) {
  const [items, setItems] = useState<CentralFeedItem[]>([])
  const [live, setLive] = useState(false)
  const ref = useRef<{ abort: () => void } | null>(null)
  useEffect(() => {
    if (!config) return
    setLive(true)
    ref.current = streamCentral(
      config,
      (it) => setItems((prev) => [it, ...prev].slice(0, 6)),
      () => setLive(false),
    )
    return () => { ref.current?.abort(); setLive(false) }
  }, [config])
  const latest = items[0]
  return (
    <div className="jm-pulse" aria-live="polite">
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
  const { data, loading, error } = usePollWhenVisible(
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
        : <SectionView section={section} data={data} />}
    </div>
  )
}

/** Ren, menneskelig visning pr. sektion. Ukendte former falder til rå (men toggle findes). */
function SectionView({ section, data }: { section: string; data: Record<string, unknown> }) {
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
