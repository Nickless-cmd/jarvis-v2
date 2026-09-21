import { useSettingsResource } from '../../hooks/useSettingsResource'
import { SettingsState, SettingsActionError } from './SettingsState'
import { useEffect, useState } from 'react'
import type { ApiConfig } from '../../lib/api'
import { getAccountMe, setAccountLanguage } from '../../lib/coworkApi'
import { setLocale, t } from '../../lib/i18n'

const OPTIONS: Array<{ value: string; label?: string; labelKey?: string }> = [
  { value: 'da', label: 'Dansk' },
  { value: 'en', label: 'English' },
  { value: 'auto', labelKey: 'settings.language.auto' },
]

/** Sprog-sektion (§4.10). Self-scope: brugeren sætter sit eget sprog. */
export function SprogSection({ config }: { config: ApiConfig | undefined }) {
  const resource = useSettingsResource(config, getAccountMe)
  const lang = resource.data?.language
  const [saved, setSaved] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  useEffect(() => { if (lang) setLocale(lang) }, [lang])
  const change = async (value: string) => {
    if (!config || !resource.data || busy) return
    setBusy(true); setError(''); setSaved(false)
    try {
      await setAccountLanguage(config, value)
      resource.setData({ ...resource.data, language: value }); setLocale(value); setSaved(true)
    } catch { setError('Sproget kunne ikke gemmes. Prøv igen.') }
    finally { setBusy(false) }
  }
  if (!resource.data) return <SettingsState status={resource.status} label="sproget" onRetry={resource.retry} />

  return (
    <div className="settings-section sprog-section">
      <h3>{t('settings.language.title')}</h3>
      <label className="sprog-field">
        <span>{t('settings.language.label')}</span>
        <select value={lang ?? 'da'} disabled={busy} onChange={(e) => void change(e.target.value)}>
          {OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>{o.labelKey ? t(o.labelKey) : o.label}</option>
          ))}
        </select>
      </label>
      <SettingsActionError message={error} />
      {saved && <span className="settings-saved">{t('common.saved')}</span>}
    </div>
  )
}
