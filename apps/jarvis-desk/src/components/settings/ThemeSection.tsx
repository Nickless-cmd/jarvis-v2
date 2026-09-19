import { useState } from 'react'
import { loadTheme, saveTheme, applyTheme, type Theme } from '../../lib/themeStore'
import { useFigurVist } from '../../lib/figurVist'

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
  const [figur, saetFigur] = useFigurVist()

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
      {/* Jarvis-figuren (electron/figur.ts). Kun i desk — i en browser-fane
          findes der intet skrivebord at stå på. */}
      {figur !== null ? (
        <label className="figur-indstilling">
          <input type="checkbox" checked={figur} onChange={(e) => saetFigur(e.target.checked)} />
          <span>
            <strong>Jarvis-figuren på skrivebordet</strong>
            <span className="account-google-hint">Viser hvad han laver, også når vinduet er lukket. Klik for at hoppe, træk for at flytte.</span>
          </span>
        </label>
      ) : null}
    </div>
  )
}
