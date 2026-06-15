import { useEffect, useState } from 'react'
import type { ApiConfig } from '../../lib/api'
import { getAccountMe, setAccountLanguage } from '../../lib/coworkApi'

const OPTIONS = [
  { value: 'da', label: 'Dansk' },
  { value: 'en', label: 'English' },
  { value: 'auto', label: 'Auto (følg input)' },
]

/** Sprog-sektion (§4.10). Self-scope: brugeren sætter sit eget sprog. */
export function SprogSection({ config }: { config: ApiConfig | undefined }) {
  const [lang, setLang] = useState<string | null>(null)
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    if (!config) return
    let alive = true
    getAccountMe(config)
      .then((p) => { if (alive) setLang(p.language) })
      .catch(() => { if (alive) setLang('da') })
    return () => { alive = false }
  }, [config?.apiBaseUrl, config?.authToken])

  const change = async (value: string) => {
    if (!config) return
    setLang(value)
    await setAccountLanguage(config, value)
    setSaved(true)
    setTimeout(() => setSaved(false), 1600)
  }

  return (
    <div className="settings-section sprog-section">
      <h3>Sprog</h3>
      <label className="sprog-field">
        <span>Sprog</span>
        <select value={lang ?? 'da'} disabled={lang === null} onChange={(e) => void change(e.target.value)}>
          {OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
        </select>
      </label>
      {saved && <span className="settings-saved">Gemt ✓</span>}
    </div>
  )
}
