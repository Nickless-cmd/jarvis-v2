import { useEffect, useState } from 'react'
import type { ApiConfig } from '../../lib/api'
import { SVARSTILE, hentSvarstil, saetSvarstil, type Svarstil } from '../../lib/svarstil'

/**
 * Svarstil — Claude Codes «output styles» (cc-codex-hvad-vi-mangler.md).
 * Valget gælder din bruger på alle enheder, og Jarvis mindes om det hver tur,
 * så det holder hele samtalen i stedet for at glide.
 */
export function SvarstilSection({ config }: { config: ApiConfig | undefined }) {
  const [stil, setStil] = useState<Svarstil | null>(null)
  const [gemt, setGemt] = useState(false)
  const [fejl, setFejl] = useState('')

  useEffect(() => {
    if (!config) return
    let alive = true
    hentSvarstil(config)
      .then((s) => { if (alive) setStil(s) })
      .catch(() => { if (alive) setStil('balanced') })
    return () => { alive = false }
  }, [config?.apiBaseUrl, config?.authToken]) // eslint-disable-line react-hooks/exhaustive-deps

  const skift = async (v: Svarstil) => {
    if (!config || v === stil) return
    const foer = stil
    setStil(v); setFejl('')
    try {
      await saetSvarstil(config, v)
      setGemt(true)
      setTimeout(() => setGemt(false), 1600)
    } catch (e) {
      setStil(foer)
      setFejl(e instanceof Error ? e.message : 'Kunne ikke gemme svarstilen')
    }
  }

  const valgt = SVARSTILE.find((s) => s.value === stil)
  return (
    <div className="settings-section sprog-section">
      <h3>Svarstil</h3>
      <label className="sprog-field">
        <span>Hvordan Jarvis svarer</span>
        <select value={stil ?? 'balanced'} disabled={stil === null} onChange={(e) => void skift(e.target.value as Svarstil)}>
          {SVARSTILE.map((s) => <option key={s.value} value={s.value}>{s.navn}</option>)}
        </select>
      </label>
      {valgt ? <p className="account-google-hint">{valgt.forklaring}. Gælder alle dine samtaler og enheder.</p> : null}
      {gemt && <span className="settings-saved">Gemt</span>}
      {fejl ? <p className="account-google-msg" role="alert">{fejl}</p> : null}
    </div>
  )
}
