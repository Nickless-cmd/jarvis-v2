import { useState } from 'react'
import { loadTheme, saveTheme, applyTheme, type Theme } from '../../lib/themeStore'

const OPTIONS: { key: Theme; label: string }[] = [
  { key: 'dark', label: 'Mørkt' },
  { key: 'light', label: 'Lyst' },
  { key: 'contrast', label: 'Høj kontrast' },
]

/** Tema-sektion (§4.11). Ren klient — persisteres i localStorage og anvendes
 *  via data-theme på document-root. */
export function ThemeSection() {
  const [theme, setTheme] = useState<Theme>(loadTheme())
  const pick = (t: Theme) => { setTheme(t); saveTheme(t); applyTheme(t) }

  return (
    <div className="settings-section theme-section">
      <h3>Tema</h3>
      <div className="theme-options">
        {OPTIONS.map((o) => (
          <button
            key={o.key}
            type="button"
            className={theme === o.key ? 'theme-btn active' : 'theme-btn'}
            onClick={() => pick(o.key)}
          >{o.label}</button>
        ))}
      </div>
    </div>
  )
}
