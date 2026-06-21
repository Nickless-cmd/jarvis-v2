import { useEffect, useState } from 'react'
import { apiFetch, type ApiConfig } from '../../lib/api'

type Channel = 'auto' | 'mobile' | 'desktop' | 'push' | 'discord' | 'telegram'
interface Prefs {
  global: Channel
  briefing: Channel | null
  reminder: Channel | null
  reach_out: Channel | null
  team_invite: Channel | null
  wakeup: Channel | null
  quiet_start: string
  quiet_end: string
}

const CHANNELS: Channel[] = ['auto', 'mobile', 'desktop', 'push', 'discord', 'telegram']
const TYPES: { key: keyof Prefs; label: string }[] = [
  { key: 'global', label: 'Standard (alle)' },
  { key: 'briefing', label: 'Morgenbriefing' },
  { key: 'reminder', label: 'Påmindelser' },
  { key: 'reach_out', label: 'Jarvis tager kontakt' },
  { key: 'team_invite', label: 'Team-invitationer' },
  { key: 'wakeup', label: 'Wakeups' },
]

/** Notifikations-routing (spec §6): vælg HVOR proaktive notifikationer lander —
 *  globalt eller per type — + quiet hours. Gemmer via /notifications/preferences. */
export function NotificationsSection({ config }: { config?: ApiConfig }) {
  const [prefs, setPrefs] = useState<Prefs | null>(null)
  const [status, setStatus] = useState('')

  useEffect(() => {
    if (!config) return
    void apiFetch<{ preferences: Prefs }>(config, '/notifications/preferences', { retries: 0 })
      .then((r) => setPrefs(r.preferences)).catch(() => setStatus('Kunne ikke hente'))
  }, [config?.authToken])

  const save = async (patch: Partial<Prefs>) => {
    if (!config || !prefs) return
    const next = { ...prefs, ...patch }
    setPrefs(next)
    setStatus('Gemmer…')
    try {
      const r = await apiFetch<{ preferences: Prefs }>(config, '/notifications/preferences',
        { method: 'POST', body: patch, retries: 0 })
      setPrefs(r.preferences); setStatus('Gemt ✓')
    } catch { setStatus('Kunne ikke gemme') }
  }

  if (!prefs) {
    return (
      <div className="settings-section">
        <h3>Notifikationer</h3>
        <p className="settings-hint">{status || 'Henter…'}</p>
      </div>
    )
  }

  return (
    <div className="settings-section notif-section">
      <h3>Notifikationer</h3>
      <p className="settings-hint">Vælg hvor Jarvis' proaktive beskeder lander. "Standard" gælder alle typer; sæt en specifik kanal per type for at overstyre.</p>
      {TYPES.map((t) => {
        const isGlobal = t.key === 'global'
        const val = (prefs[t.key] as Channel | null) ?? (isGlobal ? 'auto' : '')
        return (
          <div key={t.key} className="notif-row">
            <label className="notif-label">{t.label}</label>
            <select
              value={val}
              onChange={(e) => void save({ [t.key]: (e.target.value || null) } as Partial<Prefs>)}
            >
              {!isGlobal && <option value="">— følg standard —</option>}
              {CHANNELS.map((c) => <option key={c} value={c}>{c}</option>)}
            </select>
          </div>
        )
      })}
      <div className="notif-row">
        <label className="notif-label">Stille-timer</label>
        <span className="notif-quiet">
          <input type="time" value={prefs.quiet_start} onChange={(e) => void save({ quiet_start: e.target.value })} />
          <span> – </span>
          <input type="time" value={prefs.quiet_end} onChange={(e) => void save({ quiet_end: e.target.value })} />
        </span>
      </div>
      <p className="settings-hint">Stille-timer: ikke-kritiske notifikationer holdes tilbage og leveres efter.</p>
      {status && <p className="settings-hint">{status}</p>}
    </div>
  )
}
