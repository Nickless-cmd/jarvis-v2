import { useSettingsResource } from '../../hooks/useSettingsResource'
import { SettingsState } from './SettingsState'
import { useState } from 'react'
import type { ApiConfig } from '../../lib/api'
import {
  SVARSTILE, hentSvarPreferences, saetChatStyle, saetSvarstil,
  type ChatStyle, type Svarstil,
} from '../../lib/svarstil'

const CHAT_VALG: Array<{
  key: keyof ChatStyle; label: string; options: Array<{ value: string; label: string }>
}> = [
  { key: 'tone', label: 'Tone', options: [
    { value: 'adaptive', label: 'Tilpas automatisk' }, { value: 'warm', label: 'Varm' },
    { value: 'direct', label: 'Direkte' }, { value: 'playful', label: 'Legende' },
  ] },
  { key: 'emoji', label: 'Emoji', options: [
    { value: 'adaptive', label: 'Tilpas automatisk' }, { value: 'rare', label: 'Sjældent' },
    { value: 'expressive', label: 'Udtryksfuldt' },
  ] },
  { key: 'profanity', label: 'Kraftsprog', options: [
    { value: 'adaptive', label: 'Spejl forsigtigt' }, { value: 'avoid', label: 'Undgå' },
    { value: 'comfortable', label: 'Naturligt tilladt' },
  ] },
  { key: 'visuals', label: 'Visuelle svar', options: [
    { value: 'adaptive', label: 'Når det hjælper' }, { value: 'plain', label: 'Mest tekst' },
    { value: 'rich', label: 'Gerne visuelt' },
  ] },
  { key: 'questions', label: 'Opfølgende spørgsmål', options: [
    { value: 'adaptive', label: 'Når det åbner noget' }, { value: 'rare', label: 'Sjældent' },
    { value: 'curious', label: 'Nysgerrigt' },
  ] },
]

/**
 * Svarstil — Claude Codes «output styles» (cc-codex-hvad-vi-mangler.md).
 * Valget gælder din bruger på alle enheder, og Jarvis mindes om det hver tur,
 * så det holder hele samtalen i stedet for at glide.
 */
export function SvarstilSection({ config }: { config: ApiConfig | undefined }) {
  const resource = useSettingsResource(config, hentSvarPreferences)
  const prefs = resource.data
  const [gemt, setGemt] = useState(false)
  const [fejl, setFejl] = useState('')
  const [busy, setBusy] = useState(false)
  const skift = async (v: Svarstil) => {
    if (!config || v === prefs?.outputStyle || busy) return
    setBusy(true); setFejl(''); setGemt(false)
    try {
      await saetSvarstil(config, v)
      if (prefs) resource.setData({ ...prefs, outputStyle: v })
      setGemt(true)
    }
    catch { setFejl('Svarstilen kunne ikke gemmes. Prøv igen.') }
    finally { setBusy(false) }
  }
  const skiftChat = async <K extends keyof ChatStyle>(key: K, value: ChatStyle[K]) => {
    if (!config || !prefs || value === prefs.chatStyle[key] || busy) return
    setBusy(true); setFejl(''); setGemt(false)
    try {
      await saetChatStyle(config, { [key]: value })
      resource.setData({ ...prefs, chatStyle: { ...prefs.chatStyle, [key]: value } })
      setGemt(true)
    } catch { setFejl('Samtalestilen kunne ikke gemmes. Prøv igen.') }
    finally { setBusy(false) }
  }
  if (!prefs) return <SettingsState status={resource.status} label="svarstilen" onRetry={resource.retry} />

  const valgt = SVARSTILE.find((s) => s.value === prefs.outputStyle)
  return (
    <div className="settings-section sprog-section">
      <h3>Svarstil</h3>
      <label className="sprog-field">
        <span>Hvordan Jarvis svarer</span>
        <select value={prefs.outputStyle} disabled={busy} onChange={(e) => void skift(e.target.value as Svarstil)}>
          {SVARSTILE.map((s) => <option key={s.value} value={s.value}>{s.navn}</option>)}
        </select>
      </label>
      {valgt ? <p className="account-google-hint">{valgt.forklaring}. Gælder alle dine samtaler og enheder.</p> : null}
      <h4>Samtalestil</h4>
      <p className="account-google-hint">Jarvis tilpasser sig stadig den aktuelle samtale. Dine valg sætter rammerne—de kopierer ikke én fast persona.</p>
      <div className="chat-style-grid">
        {CHAT_VALG.map((felt) => (
          <label className="sprog-field" key={felt.key}>
            <span>{felt.label}</span>
            <select
              value={prefs.chatStyle[felt.key]}
              disabled={busy}
              onChange={(e) => void skiftChat(felt.key, e.target.value as never)}
            >
              {felt.options.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
            </select>
          </label>
        ))}
      </div>
      {gemt && <span className="settings-saved">Gemt</span>}
      {fejl ? <p className="account-google-msg" role="alert">{fejl}</p> : null}
    </div>
  )
}
