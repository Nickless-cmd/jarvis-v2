import { useState } from 'react'
import {
  loadMode, saveMode, loadManual, geocodeAndSaveManual, type LocationMode,
} from '../../lib/deskLocation'

const OPTIONS: { key: LocationMode; label: string }[] = [
  { key: 'off', label: 'Fra' },
  { key: 'ip', label: 'Automatisk (IP)' },
  { key: 'manual', label: 'Indtast adresse' },
  { key: 'browser', label: 'Browser GPS' },
]

const HINTS: Record<LocationMode, string> = {
  off: 'Jarvis kan ikke se hvor du er. Ingen IP- eller GPS-opslag.',
  ip: 'By-niveau via din internetforbindelse — fx "Svendborg". Opdateres hver 10. minut.',
  manual: 'Indtast din adresse én gang — den geocodes og sendes som præcis lokation.',
  browser: 'Browser-Geolocation (WiFi/GPS på laptops). Spørger om tilladelse første gang.',
}

/** Lokations-sektion (geolocation §Del 2). Opt-in, default Fra. Persisteres i
 *  localStorage; selve lokationen sendes kun via presence-ping. */
export function LocationSection() {
  const [mode, setMode] = useState<LocationMode>(loadMode())
  const [address, setAddress] = useState(loadManual()?.label ?? '')
  const [status, setStatus] = useState('')

  const pick = (m: LocationMode) => { setMode(m); saveMode(m); setStatus('') }

  const saveAddress = async () => {
    if (!address.trim()) return
    setStatus('Slår adresse op…')
    const r = await geocodeAndSaveManual(address.trim())
    setStatus(r ? `Gemt: ${r.label || `${r.lat.toFixed(3)}, ${r.lon.toFixed(3)}`} ✓` : 'Kunne ikke finde adressen')
  }

  return (
    <div className="settings-section location-section">
      <h3>Lokation</h3>
      <p className="settings-hint">Del lokation med Jarvis — opt-in, slået fra som standard.</p>
      <div className="loc-options">
        {OPTIONS.map((o) => (
          <button
            key={o.key}
            type="button"
            className={mode === o.key ? 'loc-btn active' : 'loc-btn'}
            onClick={() => pick(o.key)}
          >{o.label}</button>
        ))}
      </div>
      {mode === 'manual' && (
        <div className="loc-manual">
          <input
            type="text"
            value={address}
            placeholder="fx Toftegårdsvej 12, Svendborg"
            onChange={(e) => setAddress(e.target.value)}
          />
          <button type="button" className="loc-save" onClick={() => void saveAddress()}>Gem adresse</button>
        </div>
      )}
      <p className="settings-hint">{HINTS[mode]}</p>
      {status && <p className="settings-hint loc-status">{status}</p>}
      {mode !== 'off' && (
        <p className="settings-hint loc-privacy">🔒 Jarvis kan se din lokation når desktop-appen kører.</p>
      )}
    </div>
  )
}
