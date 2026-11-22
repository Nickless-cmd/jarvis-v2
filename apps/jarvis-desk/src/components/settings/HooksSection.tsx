import { useState } from 'react'
import type { ApiConfig } from '../../lib/api'
import { useSettingsResource } from '../../hooks/useSettingsResource'
import { SettingsActionError, SettingsState } from './SettingsState'
import {
  getToolHookConfig,
  getToolHookLog,
  getToolHooks,
  reloadToolHooks,
  saveToolHooks,
  validateToolHooks,
  type HookLogEntry,
  type HookRule,
} from '../../lib/toolHooksApi'

const formatBytes = (bytes: number) => {
  if (bytes < 1024) return `${bytes} B`
  return `${(bytes / 1024).toLocaleString('da-DK', { minimumFractionDigits: 1, maximumFractionDigits: 1 })} KB`
}

const entryResult = (entry: HookLogEntry) => {
  if (entry.status) return entry.status
  if (typeof entry.result === 'string') return entry.result
  if (entry.exit_code !== undefined) return `exit ${entry.exit_code}`
  return '—'
}

const tomRegel = (): HookRule => ({ name: '', match: '', before: '', after: '', timeout_s: 5, cwd: '' })

/** Config-filen kan indeholde felter der mangler eller har en anden type end
 *  editoren forventer. Normalisér FØR redigering, så et gem aldrig skriver
 *  `undefined` tilbage over en gyldig regel. */
const tilRegel = (raw: Record<string, unknown>): HookRule => ({
  name: String(raw.name ?? ''),
  match: String(raw.match ?? ''),
  before: String(raw.before ?? ''),
  after: String(raw.after ?? ''),
  timeout_s: Number(raw.timeout_s ?? 5) || 5,
  cwd: String(raw.cwd ?? ''),
})

export function HooksSection({ config }: { config: ApiConfig | undefined }) {
  const resource = useSettingsResource(config, async cfg => {
    const [status, log] = await Promise.all([getToolHooks(cfg), getToolHookLog(cfg)])
    return { status, log }
  })
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  // ── redigering ────────────────────────────────────────────────────────
  const [redigerer, setRedigerer] = useState(false)
  const [regler, setRegler] = useState<HookRule[]>([])
  const [aktiveret, setAktiveret] = useState(true)
  const [regelFejl, setRegelFejl] = useState<string[]>([])
  const [bekraeft, setBekraeft] = useState(false)
  const [gemt, setGemt] = useState('')

  const aabnEditor = async () => {
    if (!config || busy) return
    setBusy(true); setError(''); setRegelFejl([]); setGemt('')
    try {
      const dokument = await getToolHookConfig(config)
      setRegler((dokument.hooks ?? []).map(tilRegel))
      setAktiveret(Boolean(dokument.enabled))
      setRedigerer(true)
    } catch {
      setError('Hook-konfigurationen kunne ikke læses til redigering.')
    } finally {
      setBusy(false)
    }
  }

  const opdater = (indeks: number, aendring: Partial<HookRule>) => {
    setRegler(aktuelle => aktuelle.map((regel, i) => i === indeks ? { ...regel, ...aendring } : regel))
  }

  const gem = async () => {
    if (!config || busy) return
    setBusy(true); setError(''); setRegelFejl([])
    const payload = { enabled: aktiveret, hooks: regler }
    try {
      const kontrol = await validateToolHooks(config, payload)
      if (!kontrol.ok) {
        setRegelFejl(kontrol.fejl ?? [])
        return
      }
      await saveToolHooks(config, payload)
      setGemt('Reglerne er gemt og indlæst i den kørende proces.')
      setBekraeft(false)
      setRedigerer(false)
      resource.retry()
    } catch {
      // 422 betyder at serveren forstod input og afviste det — så skal
      // brugeren se hvorfor, ikke bare at det gik galt.
      setRegelFejl(['Serveren afviste ændringen. Se om et felt mangler eller et regex er ugyldigt.'])
    } finally {
      setBusy(false)
    }
  }

  const reload = async () => {
    if (!config || busy) return
    setBusy(true); setError('')
    try {
      await reloadToolHooks(config)
      resource.retry()
    } catch {
      setError('Hook-konfigurationen kunne ikke genindlæses.')
    } finally {
      setBusy(false)
    }
  }

  if (!resource.data) {
    return <SettingsState status={resource.status} label="tool-hooks" onRetry={resource.retry} />
  }
  const { status, log } = resource.data
  const warning = !status.config_findes
    ? `Hook-config mangler: ${status.config}`
    : !status.enabled ? 'Hook-mekanismen er slukket. Ingen hooks beskytter eller observerer tool-kald.' : ''

  return (
    <div className="settings-section hooks-section">
      <h3>Tool-hooks</h3>
      <p className="settings-hint">Indlæste shell-hooks, deres hændelseslog og den faktisk målte sandbox-dækning.</p>
      {warning && <p className="settings-feedback error" role="alert">{warning}</p>}
      <SettingsActionError message={error || status.fejl || ''} />
      {gemt && <p className="settings-feedback" role="status">{gemt}</p>}

      <div className="hooks-knapper">
        <button type="button" disabled={busy} onClick={() => void reload()}>
          {busy ? 'Genindlæser…' : 'Genindlæs hooks'}
        </button>
        <button type="button" disabled={busy} onClick={() => void aabnEditor()}>
          {redigerer ? 'Redigerer regler…' : 'Rediger regler'}
        </button>
      </div>

      {redigerer && (
        <div className="hooks-editor">
          <p className="settings-feedback error" role="alert">
            Reglerne bestemmer hvad der kører shell på <strong>hvert</strong> tool-kald.
            En fejl her rammer alt arbejde — læs kommandoen igennem før du gemmer.
          </p>

          <label className="hooks-flag">
            <input type="checkbox" checked={aktiveret} onChange={e => setAktiveret(e.target.checked)} />
            {' '}Mekanismen er slået til
          </label>

          {regelFejl.length > 0 && (
            <ul className="settings-feedback error" role="alert">
              {regelFejl.map(fejl => <li key={fejl}>{fejl}</li>)}
            </ul>
          )}

          {regler.length === 0 && <div className="cowork-empty">Ingen regler endnu.</div>}

          {regler.map((regel, indeks) => (
            <fieldset className="hooks-regel" key={indeks}>
              <legend>{regel.name || `regel ${indeks + 1}`}</legend>
              <label>Navn
                <input value={regel.name} onChange={e => opdater(indeks, { name: e.target.value })} />
              </label>
              <label>Match (regex på tool-navn)
                <input value={regel.match} onChange={e => opdater(indeks, { match: e.target.value })} />
              </label>
              <label>Before — shell-kommando (exit 2 blokerer)
                <textarea rows={2} value={regel.before}
                  onChange={e => opdater(indeks, { before: e.target.value })} />
              </label>
              <label>After — observatør (kan intet stoppe)
                <textarea rows={2} value={regel.after}
                  onChange={e => opdater(indeks, { after: e.target.value })} />
              </label>
              <label>Timeout (sekunder)
                <input type="number" min={0.1} max={60} step={0.5} value={regel.timeout_s}
                  onChange={e => opdater(indeks, { timeout_s: Number(e.target.value) })} />
              </label>
              <button type="button" onClick={() => setRegler(aktuelle => aktuelle.filter((_, i) => i !== indeks))}>
                Fjern regel
              </button>
            </fieldset>
          ))}

          <div className="hooks-knapper">
            <button type="button" onClick={() => setRegler(aktuelle => [...aktuelle, tomRegel()])}>
              Tilføj regel
            </button>
            <button type="button" disabled={busy} onClick={() => setBekraeft(true)}>Gem regler</button>
            <button type="button" onClick={() => { setRedigerer(false); setRegelFejl([]) }}>Annullér</button>
          </div>

          {bekraeft && (
            <div className="settings-feedback error" role="alert">
              <p>Gem {regler.length} regel/regler og indlæs dem straks i den kørende proces?</p>
              <div className="hooks-knapper">
                <button type="button" disabled={busy} onClick={() => void gem()}>
                  {busy ? 'Gemmer…' : 'Ja, gem og indlæs'}
                </button>
                <button type="button" onClick={() => setBekraeft(false)}>Nej</button>
              </div>
            </div>
          )}
        </div>
      )}

      {status.hooks.length === 0 ? <div className="cowork-empty">Ingen hooks indlæst.</div> : (
        <table className="hooks-table">
          <thead><tr><th>Navn</th><th>Match</th><th>Faser</th><th>Status</th></tr></thead>
          <tbody>{status.hooks.map(hook => (
            <tr key={hook.name}>
              <td>{hook.name}</td><td><code>{hook.match}</code></td>
              <td>{[hook.before && 'before', hook.after && 'after'].filter(Boolean).join(' + ') || '—'}</td>
              <td>{hook.active ? 'Aktiv' : 'Inaktiv'}</td>
            </tr>
          ))}</tbody>
        </table>
      )}

      <h4>Sandbox-dækning · sidste døgn</h4>
      <div className={log.coverage_24h.confined === 0 ? 'settings-feedback error' : 'settings-hint'}>
        {log.coverage_24h.confined} indespærret · {log.coverage_24h.fail_open} fail-open · {log.coverage_24h.non_shell} ikke-shell
        {log.coverage_24h.confined === 0 && ' — ingen målte shell-kald kørte indespærret.'}
      </div>

      <h4>Seneste hook-hændelser</h4>
      <p className="settings-hint">
        {formatBytes(log.log.size_bytes)} · {log.log.rotated ? 'roteret generation findes' : 'ingen roteret generation'}
      </p>
      {log.entries.length === 0 ? <div className="cowork-empty">Hook-loggen er tom.</div> : (
        <table className="hooks-table">
          <thead><tr><th>Tid</th><th>Tool</th><th>Fase</th><th>Resultat</th></tr></thead>
          <tbody>{log.entries.map((entry, index) => (
            <tr key={`${entry.time ?? entry.timestamp ?? entry.ts ?? ''}:${index}`}>
              <td>{entry.time ?? entry.timestamp ?? entry.ts ?? '—'}</td>
              <td>{entry.tool ?? entry.tool_name ?? '—'}</td>
              <td>{entry.phase ?? '—'}</td><td>{entryResult(entry)}</td>
            </tr>
          ))}</tbody>
        </table>
      )}
    </div>
  )
}
