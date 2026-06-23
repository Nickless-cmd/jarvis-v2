import { useState } from 'react'
import type { ApiConfig } from '../../lib/api'
import { getCognitiveArchitecture, getMcOverview } from '../../lib/api'
import { usePollWhenVisible } from '../../hooks/usePollWhenVisible'

/** Jarvis Mind — owner-vinduet ind i alt det gamle MC viste, men overskueligt.
 *  Lever som cowork-zone (venstre-menu); HER en SUB-NAVBAR under app-headeren til
 *  fanerne — ingen ekstra menu (Bjørn 2026-06-23). Poller KUN den aktive fane, og kun
 *  mens vinduet er synligt (usePollWhenVisible) → ingen konstant backend-load som MC.
 *
 *  Migration: fanerne følger MC-dæknings-kontrakten (docs/specs/2026-06-23-jarvis-mind-
 *  migration-map.md). Sektioner fyldes én ad gangen + verificeres mod gammel MC-tab. */

type TabId =
  | 'overview' | 'mind' | 'observability' | 'agency' | 'memory'
  | 'council' | 'skills' | 'reflection' | 'lab' | 'hardening'

const TABS: ReadonlyArray<{ id: TabId; label: string }> = [
  { id: 'overview', label: 'Oversigt' },
  { id: 'mind', label: 'Sind' },
  { id: 'observability', label: 'Observabilitet' },
  { id: 'agency', label: 'Agentur' },
  { id: 'memory', label: 'Hukommelse' },
  { id: 'council', label: 'Council' },
  { id: 'skills', label: 'Skills' },
  { id: 'reflection', label: 'Refleksion' },
  { id: 'lab', label: 'Lab' },
  { id: 'hardening', label: 'Hærdning' },
]

const POLL_MS = 30_000

export function JarvisMind({ config }: { config?: ApiConfig }) {
  const [tab, setTab] = useState<TabId>('mind')
  return (
    <div className="jarvis-mind">
      <nav className="jm-tabs" role="tablist" aria-label="Jarvis Mind">
        {TABS.map((t) => (
          <button
            key={t.id}
            type="button"
            role="tab"
            aria-selected={tab === t.id}
            className={`jm-tab ${tab === t.id ? 'active' : ''}`}
            onClick={() => setTab(t.id)}
          >
            {t.label}
          </button>
        ))}
      </nav>
      <div className="jm-body">
        {tab === 'mind' ? <MindSection config={config} active />
          : tab === 'overview' ? <OverviewSection config={config} active />
          : <PlaceholderSection tab={tab} />}
      </div>
    </div>
  )
}

/** Sind: de ~70 cognitive surfaces (server-cachet 75s). MC: Mind › Cognitive/Consciousness. */
function MindSection({ config, active }: { config?: ApiConfig; active: boolean }) {
  const { data, loading, error } = usePollWhenVisible(
    () => getCognitiveArchitecture(config!), POLL_MS, !!config && active,
  )
  if (error) return <SectionError msg={error} />
  if (!data) return <SectionLoading loading={loading} />
  const systems = data.systems ?? []
  return (
    <div className="jm-section">
      <div className="jm-section-head">
        <span>{data.summary || `${data.active_count ?? 0}/${data.total_count ?? systems.length} systemer aktive`}</span>
        {loading && <span className="jm-dim">opdaterer…</span>}
      </div>
      <div className="jm-grid">
        {systems.map((s) => (
          <div key={s.system} className={`jm-card ${s.active ? 'on' : 'off'}`}>
            <div className="jm-card-title">
              <span className={`jm-dot ${s.active ? 'on' : 'off'}`} />
              {s.system.replace(/_/g, ' ')}
            </div>
            {s.summary && <div className="jm-card-sub">{s.summary}</div>}
          </div>
        ))}
      </div>
    </div>
  )
}

/** Oversigt: runtime-sundhed (aktive runs, model, approvals). MC: Overview-tab. */
function OverviewSection({ config, active }: { config?: ApiConfig; active: boolean }) {
  const { data, loading, error } = usePollWhenVisible(
    () => getMcOverview(config!), POLL_MS, !!config && active,
  )
  if (error) return <SectionError msg={error} />
  if (!data) return <SectionLoading loading={loading} />
  return (
    <div className="jm-section">
      <div className="jm-section-head"><span>Runtime-oversigt</span>{loading && <span className="jm-dim">opdaterer…</span>}</div>
      <pre className="jm-raw">{JSON.stringify(data, null, 2)}</pre>
    </div>
  )
}

function PlaceholderSection({ tab }: { tab: TabId }) {
  return (
    <div className="jm-section jm-placeholder">
      <p>Denne sektion er endnu ikke flyttet fra Mission Control.</p>
      <p className="jm-dim">Følger dæknings-kontrakten — verificeres mod gammel MC-tab "{tab}" inden MC udfases.</p>
    </div>
  )
}

function SectionLoading({ loading }: { loading: boolean }) {
  return <div className="jm-section jm-dim">{loading ? 'Henter…' : 'Ingen data endnu.'}</div>
}
function SectionError({ msg }: { msg: string }) {
  return <div className="jm-section jm-error">Kunne ikke hente: {msg}</div>
}
