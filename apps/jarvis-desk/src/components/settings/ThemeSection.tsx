import { useState } from 'react'
import { loadTheme, saveTheme, applyTheme, type Theme } from '../../lib/themeStore'
import { useFigurVist } from '../../lib/figurVist'
import { useFigurSkin, SKIN_VALG } from '../../lib/figurSkin'
import { useRaekkevisning, writeRaekkevisning } from '../../lib/visningsPref'

const OPTIONS: { key: Theme; label: string }[] = [
  { key: 'dark', label: 'Mørkt' },
  { key: 'light', label: 'Lyst' },
  { key: 'contrast', label: 'Høj kontrast' },
]

/** Tema-sektion (§4.11). Ren klient — persisteres i localStorage og anvendes
 *  via data-theme på document-root. */
export function ThemeSection() {
  const [theme, setTheme] = useState<Theme>(loadTheme())
  const raekker = useRaekkevisning()
  const pick = (t: Theme) => { setTheme(t); saveTheme(t); applyTheme(t) }
  const [figur, saetFigur] = useFigurVist()
  // Skinnet bor samme sted som til/fra (figur.json i main-processen), så
  // indstillingerne og figur-vinduet altid ser det samme.
  const [skin, saetSkin] = useFigurSkin()

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
      {/* Udseendet (20/9-2026). Vælgeren står også mens figuren er slukket,
          så man kan bestemme sig før man tænker på at tænde den. Skiftet slår
          straks igennem uden genstart: main-processen gemmer valget og sender
          det videre til figur-vinduet, som er en anden renderer. */}
      {skin !== null ? (
        <div className="figur-skin">
          <span className="figur-skin-label">Figurens udseende</span>
          <div className="theme-options">
            {SKIN_VALG.map((s) => (
              <button
                key={s.key}
                type="button"
                className={skin === s.key ? 'theme-btn active' : 'theme-btn'}
                onClick={() => saetSkin(s.key)}
              >{s.label}</button>
            ))}
          </div>
        </div>
      ) : null}
      {/* Rækkevisning (22/9-2026). Samtalen som en flad hændelsesrække i
          stedet for bobler: hver tanke og hvert værktøjskald er én linje af
          samme højde, arbejdet folder sig sammen bag turens hoved, og kun
          svaret bliver stående. Skiftet slår igennem på HELE tråden med det
          samme — samme samtale, anden tegning. Composer, liveness-linje og
          save-rail er de samme i begge visninger. */}
      <label className="figur-indstilling">
        <input
          type="checkbox"
          checked={raekker}
          onChange={(e) => writeRaekkevisning(e.target.checked)}
        />
        <span>
          <strong>Rækkevisning i chatten</strong>
          <span className="account-google-hint">Ét svar, én linje pr. hændelse. Fold en linje ud for at se indholdet. Slå fra for at få boblerne tilbage.</span>
        </span>
      </label>
    </div>
  )
}
