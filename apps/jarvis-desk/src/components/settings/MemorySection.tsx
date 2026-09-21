import { useEffect, useRef, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import type { ApiConfig } from '../../lib/api'
import { getAccountMemory, searchAccountMemory } from '../../lib/coworkApi'
import { useSettingsResource } from '../../hooks/useSettingsResource'
import { SettingsState, SettingsActionError } from './SettingsState'

/** Self-scoped memory overview. The original documents stay available as details. */
export function MemorySection({ config }: { config: ApiConfig | undefined }) {
  const resource = useSettingsResource(config, getAccountMemory)
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<{ id: string; content: string }[] | null>(null)
  const [searching, setSearching] = useState(false)
  const [error, setError] = useState('')
  const request = useRef(0)
  useEffect(() => {
    request.current++; setResults(null); setSearching(false); setError(''); setQuery('')
    return () => { request.current++ }
  }, [config?.apiBaseUrl, config?.authToken])
  const search = async () => {
    const q = query.trim()
    if (!q || !config) return
    const id = ++request.current
    setSearching(true); setError(''); setResults(null)
    try {
      const found = await searchAccountMemory(config, q)
      if (request.current === id) setResults(found)
    } catch {
      if (request.current === id) setError('Søgningen kunne ikke gennemføres. Prøv at søge igen.')
    } finally { if (request.current === id) setSearching(false) }
  }
  const data = resource.data
  if (!data) return <SettingsState status={resource.status} label="hukommelsen" onRetry={resource.retry} />
  return (
    <div className="settings-section memory-section">
      <h3>Det Jarvis husker om dig</h3>
      <p className="settings-hint">Dine gemte noter og oplysninger, som hjælper Jarvis med at fortsætte samtalen.</p>
      <form className="settings-search" onSubmit={e => { e.preventDefault(); void search() }}>
        <label htmlFor="memory-query">Søg i seneste observationer</label>
        <div className="settings-search-controls">
          <input id="memory-query" className="memory-search" placeholder="Søg efter et emne…" value={query}
            onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); void search() } }}
            onChange={e => { request.current++; setQuery(e.target.value); setResults(null); setError(''); setSearching(false) }} />
          <button type="submit" disabled={searching || !query.trim()}>{searching ? 'Søger…' : 'Søg'}</button>
        </div>
      </form>
      <SettingsActionError message={error} />
      <div aria-live="polite" aria-busy={searching}>
        {results && <section className="memory-results-section"><h4>Søgeresultater</h4>
          {results.length === 0 ? <p className="settings-empty">Ingen observationer matcher din søgning.</p>
            : <ul className="memory-results">{results.map(r => <li key={r.id}>{r.content}</li>)}</ul>}
        </section>}
      </div>
      <section className="memory-reading"><h4>Gemte noter</h4>
        {data.memory_md ? <ReactMarkdown>{data.memory_md}</ReactMarkdown>
          : <p className="settings-empty">Der er endnu ingen gemte noter. Du kan bede Jarvis om at huske noget i samtalen.</p>}
      </section>
      <section className="memory-reading"><h4>Om dig</h4>
        {data.user_md ? <ReactMarkdown>{data.user_md}</ReactMarkdown> : <p className="settings-empty">Der er endnu ingen oplysninger om dig her.</p>}
      </section>
      <section><h4>Seneste observationer</h4>
        {data.recent_sensory.length ? <ul className="memory-sensory">{data.recent_sensory.map(s => <li key={s.id}>{s.content}</li>)}</ul>
          : <p className="settings-empty">Ingen observationer at vise endnu.</p>}
      </section>
      <details className="settings-details"><summary>Tekniske detaljer og originaldokumenter</summary>
        <p>{data.brain_count} poster i hukommelseslageret</p>
        <h4>MEMORY.md</h4><pre className="memory-doc">{data.memory_md || '(tom)'}</pre>
        <h4>USER.md</h4><pre className="memory-doc">{data.user_md || '(tom)'}</pre>
      </details>
    </div>
  )
}
