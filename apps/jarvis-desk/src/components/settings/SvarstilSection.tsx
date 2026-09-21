import { useSettingsResource } from '../../hooks/useSettingsResource'
import { SettingsState } from './SettingsState'
import { useState } from 'react'
import type { ApiConfig } from '../../lib/api'
import { SVARSTILE, hentSvarstil, saetSvarstil, type Svarstil } from '../../lib/svarstil'

/**
 * Svarstil — Claude Codes «output styles» (cc-codex-hvad-vi-mangler.md).
 * Valget gælder din bruger på alle enheder, og Jarvis mindes om det hver tur,
 * så det holder hele samtalen i stedet for at glide.
 */
export function SvarstilSection({ config }: { config: ApiConfig | undefined }) {
  const resource = useSettingsResource(config, hentSvarstil)
  const stil = resource.data
  const [gemt, setGemt] = useState(false)
  const [fejl, setFejl] = useState('')
  const [busy, setBusy] = useState(false)
  const skift = async (v: Svarstil) => {
    if (!config || v === stil || busy) return
    setBusy(true); setFejl(''); setGemt(false)
    try { await saetSvarstil(config, v); resource.setData(v); setGemt(true) }
    catch { setFejl('Svarstilen kunne ikke gemmes. Prøv igen.') }
    finally { setBusy(false) }
  }
  if (!stil) return <SettingsState status={resource.status} label="svarstilen" onRetry={resource.retry} />

  const valgt = SVARSTILE.find((s) => s.value === stil)
  return (
    <div className="settings-section sprog-section">
      <h3>Svarstil</h3>
      <label className="sprog-field">
        <span>Hvordan Jarvis svarer</span>
        <select value={stil ?? 'balanced'} disabled={busy} onChange={(e) => void skift(e.target.value as Svarstil)}>
          {SVARSTILE.map((s) => <option key={s.value} value={s.value}>{s.navn}</option>)}
        </select>
      </label>
      {valgt ? <p className="account-google-hint">{valgt.forklaring}. Gælder alle dine samtaler og enheder.</p> : null}
      {gemt && <span className="settings-saved">Gemt</span>}
      {fejl ? <p className="account-google-msg" role="alert">{fejl}</p> : null}
    </div>
  )
}
