import { useEffect, useState } from 'react'
import type { ApiConfig } from '../../lib/api'
import { getAccountMemory, searchAccountMemory, type MemoryOverview } from '../../lib/coworkApi'

/** Memory-sektion (§4.3). Self-scope: brugerens egen MEMORY.md/USER.md, seneste
 *  sansninger, brain-antal + søgning. Ingen cross-bruger-adgang. */
export function MemorySection({ config }: { config: ApiConfig | undefined }) {
  const [data, setData] = useState<MemoryOverview | null>(null)
  const [error, setError] = useState(false)
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<{ id: string; content: string }[] | null>(null)

  useEffect(() => {
    if (!config) return
    let alive = true
    getAccountMemory(config)
      .then((d) => { if (alive) setData(d) })
      .catch(() => { if (alive) setError(true) })
    return () => { alive = false }
  }, [config?.apiBaseUrl, config?.authToken])

  const search = async () => {
    const q = query.trim()
    if (!q || !config) return
    setResults(await searchAccountMemory(config, q))
  }

  if (error) return <div className="settings-section">Kunne ikke hente hukommelsen.</div>
  if (!data) return <div className="settings-section">Indlæser hukommelse…</div>

  return (
    <div className="settings-section memory-section">
      <h3>Hukommelse <span className="badge badge-ok">{data.brain_count} brain</span></h3>

      <input
        className="memory-search"
        placeholder="Søg i sansninger…"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        onKeyDown={(e) => { if (e.key === 'Enter') void search() }}
      />
      {results && (
        <ul className="memory-results">
          {results.length === 0 && <li className="cowork-empty">Ingen resultater</li>}
          {results.map((r) => <li key={r.id}>{r.content}</li>)}
        </ul>
      )}

      <h4>MEMORY.md</h4>
      <pre className="memory-doc">{data.memory_md || '(tom)'}</pre>
      <h4>USER.md</h4>
      <pre className="memory-doc">{data.user_md || '(tom)'}</pre>

      {data.recent_sensory.length > 0 && (
        <>
          <h4>Seneste sansninger</h4>
          <ul className="memory-sensory">
            {data.recent_sensory.map((s) => <li key={s.id}>{s.modality ? `[${s.modality}] ` : ''}{s.content}</li>)}
          </ul>
        </>
      )}
    </div>
  )
}
