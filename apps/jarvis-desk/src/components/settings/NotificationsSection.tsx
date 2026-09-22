import { useSettingsResource } from '../../hooks/useSettingsResource'
import { SettingsState } from './SettingsState'
import { useState } from 'react'
import { apiFetch, type ApiConfig } from '../../lib/api'
import { NotifikationsValg } from './NotifikationsValg'

type Channel = 'auto' | 'mobile' | 'desktop' | 'push' | 'discord' | 'telegram'
interface Prefs {
  global: Channel
  briefing: Channel | null
  reminder: Channel | null
  reach_out: Channel | null
  wakeup: Channel | null
  quiet_start: string
  quiet_end: string
}

const CHANNELS: Channel[] = ['auto', 'mobile', 'desktop', 'push', 'discord', 'telegram']

/**
 * V7 (22/9-2026): «no dual truth». Denne sektion viste FOER en per-type-vælger
 * for hver af de fem — men `briefing`, `reminder` og `reach_out` har ALLE en
 * modpart i NotifikationsValg (rækker i `notifikations_valg`), og det er DEN
 * der reelt vinder: `notification_router` læser rækkerne, ikke disse kolonner.
 * Et valg her saa ud til at gælde, men gjorde intet — «Morgenbriefing →
 * Discord» her, mens rækken sagde noget andet, ændrede ingenting.
 *
 * V9 (22/9-2026): `wakeup` var den sidste tilbage her, fordi NotifikationsValg's
 * NAVN-liste manglede en `wakeup`-nøgle. Den nøgle er nu tilføjet (og
 * `notifikations_valg.STANDARD` har fået en standard for den), så `wakeup`
 * er flyttet til den nye sektion — samme grund som de tre andre: rækken i
 * `notifikations_valg` vinder, denne kolonne gjorde intet.
 */
const TYPES: { key: keyof Prefs; label: string }[] = [
  { key: 'global', label: 'Standard (alle)' },
]

/** Notifikations-routing (spec §6): vælg HVOR proaktive notifikationer lander —
 *  globalt eller per type — + quiet hours. Gemmer via /notifications/preferences. */
export function NotificationsSection({ config }: { config?: ApiConfig }) {
  const resource = useSettingsResource(config, async cfg => (await apiFetch<{ preferences: Prefs }>(cfg, '/notifications/preferences', { retries: 0 })).preferences)
  const prefs = resource.data
  const [status, setStatus] = useState('')
  const [busy, setBusy] = useState(false)
  const save = async (patch: Partial<Prefs>) => {
    if (!config || !prefs || busy) return
    setBusy(true); setStatus('Gemmer…')
    try {
      const r = await apiFetch<{ preferences: Prefs }>(config, '/notifications/preferences', { method: 'POST', body: patch, retries: 0 })
      resource.setData(r.preferences); setStatus('Gemt ✓')
    } catch { setStatus('Kunne ikke gemme. Prøv igen.') }
    finally { setBusy(false) }
  }
  if (!prefs) return <SettingsState status={resource.status} label="notifikationer" onRetry={resource.retry} />

  return (
    <>
      <div className="settings-section notif-section">
        <h3>Notifikationer</h3>
        <p className="settings-hint">Vælg hvor Jarvis' proaktive beskeder lander. "Standard" gælder alle typer; sæt en specifik kanal per type for at overstyre.</p>
        {TYPES.map((t) => {
          const isGlobal = t.key === 'global'
          const val = (prefs[t.key] as Channel | null) ?? (isGlobal ? 'auto' : '')
          return (
            <div key={t.key} className="notif-row">
              <label className="notif-label">{t.label}</label>
              <select aria-label={t.label} disabled={busy}
                value={val}
                onChange={(e) => void save({ [t.key]: (e.target.value || null) } as Partial<Prefs>)}
              >
                {!isGlobal && <option value="">— følg standard —</option>}
                {CHANNELS.map((c) => <option key={c} value={c}>{{ auto: 'Automatisk', mobile: 'Mobil', desktop: 'Desk', push: 'Pushbesked', discord: 'Discord', telegram: 'Telegram' }[c]}</option>)}
              </select>
            </div>
          )
        })}
        <div className="notif-row">
          <label className="notif-label">Stille-timer</label>
          <span className="notif-quiet">
            <input aria-label="Stilletid fra" disabled={busy} type="time" value={prefs.quiet_start} onChange={(e) => void save({ quiet_start: e.target.value })} />
            <span> – </span>
            <input aria-label="Stilletid til" disabled={busy} type="time" value={prefs.quiet_end} onChange={(e) => void save({ quiet_end: e.target.value })} />
          </span>
        </div>
        <p className="settings-hint">Stille-timer: ikke-kritiske notifikationer holdes tilbage og leveres efter.</p>
        {status && <p role={status.startsWith('Kunne') ? 'alert' : 'status'} className="settings-hint">{status}</p>}
      </div>
      <NotifikationsValg config={config} />
    </>
  )
}
