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
  const [lang, setLang] = useState<string | null>(null)
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    if (!config) return
    let alive = true
    getAccountMe(config)
      .then((p) => {
        if (!alive) return
        setLang(p.language)
        setLocale(p.language)
      })
      .catch(() => {
        if (!alive) return
        setLang('da')
        setLocale('da')
      })
    return () => { alive = false }
  }, [config?.apiBaseUrl, config?.authToken])

  const change = async (value: string) => {
    if (!config) return
    setLang(value)
    setLocale(value)
    await setAccountLanguage(config, value)
    setSaved(true)
    setTimeout(() => setSaved(false), 1600)
  }

  return (
    <div className="settings-section sprog-section">
      <h3>{t('settings.language.title')}</h3>
      <label className="sprog-field">
        <span>{t('settings.language.label')}</span>
        <select value={lang ?? 'da'} disabled={lang === null} onChange={(e) => void change(e.target.value)}>
          {OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>{o.labelKey ? t(o.labelKey) : o.label}</option>
          ))}
        </select>
      </label>
      {saved && <span className="settings-saved">{t('common.saved')}</span>}
    </div>
  )
}
