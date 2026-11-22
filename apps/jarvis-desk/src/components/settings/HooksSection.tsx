import { useState } from 'react'
import type { ApiConfig } from '../../lib/api'
import { useSettingsResource } from '../../hooks/useSettingsResource'
import { SettingsActionError, SettingsState } from './SettingsState'
import { getToolHookLog, getToolHooks, reloadToolHooks, type HookLogEntry } from '../../lib/toolHooksApi'

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

export function HooksSection({ config }: { config: ApiConfig | undefined }) {
  const resource = useSettingsResource(config, async cfg => {
    const [status, log] = await Promise.all([getToolHooks(cfg), getToolHookLog(cfg)])
    return { status, log }
  })
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

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
      <button type="button" disabled={busy} onClick={() => void reload()}>
        {busy ? 'Genindlæser…' : 'Genindlæs hooks'}
      </button>

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
