import { useEffect, useState } from 'react'
import type { ApiConfig } from '../../../lib/api'
import { getMcEvents, type McEvent } from '../../../lib/missionControlApi'

const FAMILIES = ['alle', 'runtime', 'tool', 'approvals', 'cost', 'channel', 'incident'] as const
type Family = typeof FAMILIES[number]

/** Live hændelsesfeed (projektion fra eventbus). Filtrerbar pr. familie. Poller 4s +
 *  nudges via /ws (samme WS som resten af MC). Read-only observabilitet. */
export function EventStream({ config }: { config: ApiConfig | undefined }) {
  const [family, setFamily] = useState<Family>('alle')
  const [events, setEvents] = useState<McEvent[]>([])

  useEffect(() => {
    if (!config) return
    let alive = true
    const load = () => {
      getMcEvents(config, 60, family === 'alle' ? undefined : family)
        .then((e) => { if (alive) setEvents(e) })
        .catch(() => { /* behold sidste */ })
    }
    load()
    const id = setInterval(load, 4000)
    let ws: WebSocket | null = null
    try {
      ws = new WebSocket(config.apiBaseUrl.replace(/^http/, 'ws').replace(/\/$/, '') + '/ws')
      ws.onmessage = load
      ws.onerror = () => { /* polling dækker */ }
    } catch { /* polling dækker */ }
    return () => { alive = false; clearInterval(id); try { ws?.close() } catch { /* noop */ } }
  }, [config, family])

  return (
    <div className="mc-events">
      <div className="mc-filters">
        {FAMILIES.map((f) => (
          <button key={f} type="button" className={`mc-filter ${family === f ? 'active' : ''}`} onClick={() => setFamily(f)}>
            {f}
          </button>
        ))}
      </div>
      {events.length === 0 ? (
        <div className="cowork-empty">Ingen hændelser</div>
      ) : (
        <div className="mc-event-list">
          {events.slice().reverse().map((e, i) => (
            <div key={e.id ?? i} className="mc-event-row">
              <span className="mc-event-fam">{e.family || '—'}</span>
              <span className="mc-event-kind mc-mono">{e.kind || ''}</span>
              <span className="mc-event-at">{e.created_at ? fmt(e.created_at) : ''}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function fmt(iso: string): string {
  try {
    return new Date(iso).toLocaleTimeString('da-DK', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
  } catch {
    return iso
  }
}
