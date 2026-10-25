import { useState } from 'react'
import { Check } from 'lucide-react'
import {
  ACCENTS, applyTheme, loadAccent, loadTheme, saveAccent, saveTheme,
  type AccentName, type Theme,
} from '../../lib/themeStore'
import { useFigurVist } from '../../lib/figurVist'
import { useFigurSkin, SKIN_VALG } from '../../lib/figurSkin'
import { useRaekkevisning, writeRaekkevisning } from '../../lib/visningsPref'
import { usePaceMode, writePaceMode } from '../../lib/streamPacing'
import { useChatFlow } from '../../hooks/useChatFlow'
import type { ChatFlowPreference } from '../../lib/chatFlowApi'

const OPTIONS: { key: Theme; label: string }[] = [
  { key: 'dark', label: 'Mørkt' },
  { key: 'light', label: 'Lyst' },
  { key: 'auto', label: 'Automatisk' },
]

/** Tema-sektion (§4.11). Ren klient — persisteres i localStorage og anvendes
 *  via data-theme på document-root. */
export function ThemeSection() {
  const [theme, setTheme] = useState<Theme>(loadTheme())
  const [accent, setAccent] = useState<AccentName>(loadAccent())
  const raekker = useRaekkevisning()
  const jaevn = usePaceMode() === 'chat'
  const pick = (t: Theme) => { setTheme(t); saveTheme(t); applyTheme(t, accent) }
  const pickAccent = (next: AccentName) => {
    setAccent(next)
    saveAccent(next)
    applyTheme(theme, next)
  }
  const [figur, saetFigur] = useFigurVist()
  // Skinnet bor samme sted som til/fra (figur.json i main-processen), så
  // indstillingerne og figur-vinduet altid ser det samme.
  const [skin, saetSkin] = useFigurSkin()
  const chatFlow = useChatFlow()
  const chatOptions: { key: ChatFlowPreference; label: string; description: string }[] = [
    { key: 'living', label: 'Levende', description: 'Viser én levende statuslinje i det åbne turhoved.' },
    { key: 'calm', label: 'Rolig', description: 'Viser kun Jarvis’ aktuelle arbejdsstatus.' },
    { key: 'adaptive', label: 'Adaptiv', description: 'Jarvis vælger automatisk den visning, der passer til samtalen.' },
  ]

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
      <h4>Farve</h4>
      <div className="accent-options" role="group" aria-label="Accentfarve">
        {ACCENTS.map((option) => (
          <button
            key={option.name}
            type="button"
            className={accent === option.name ? 'accent-btn active' : 'accent-btn'}
            aria-label={option.label}
            aria-pressed={accent === option.name}
            onClick={() => pickAccent(option.name)}
          >
            <span className="accent-swatch" style={{ backgroundColor: option.color }}>
              {accent === option.name ? <Check size={16} strokeWidth={3} /> : null}
            </span>
            <span>{option.label}</span>
          </button>
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
      <div className="settings-mode-group">
      <h4>Code Mode</h4>
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
          <strong>Rækkevisning</strong>
          <span className="account-google-hint">Ét svar, én linje pr. hændelse. Fold en linje ud for at se indholdet. Slå fra for at få boblerne tilbage.</span>
        </span>
      </label>
      {/* Jævn tekststrøm (19/10-2026). Code Mode har haft sit eget pacing-lag
          siden rækkevisningen blev bygget: 33 ms-tick med op til 28 tegn pr.
          tick (~848 tegn/s) og et spring frem ved 330 tegns efterslæb. Chat
          Mode ruller med 48–72 kodepunkter pr. SEKUND og fordeler efterslæbet
          over 12 s. Forskellen er kurven — træet, folden og teleporteringen af
          slutsvaret er det samme i begge. Skiftet virker MIDT i en strøm, så
          man kan mærke forskellen på den samme tekst. */}
      <label className="figur-indstilling">
        <input
          type="checkbox"
          checked={jaevn}
          onChange={(e) => writePaceMode(e.target.checked ? 'chat' : 'code')}
        />
        <span>
          <strong>Jævn tekststrøm</strong>
          <span className="account-google-hint">Samme rul som Chat Mode: teksten kommer i et jævnt tempo og springer ikke frem, når serveren sender hurtigere end skærmen kan læse.</span>
        </span>
      </label>
      </div>
      <fieldset className="settings-mode-group chat-flow-settings">
        <legend><h4>Chat Mode</h4></legend>
        {chatOptions.map((option) => (
          <label className="figur-indstilling" key={option.key}>
            <input
              type="radio"
              name="chat-flow-preference"
              checked={chatFlow.state.preference === option.key}
              onChange={() => void chatFlow.setPreference(option.key)}
            />
            <span>
              <strong>{option.label}</strong>
              <span className="account-google-hint">{option.description}</span>
            </span>
          </label>
        ))}
      </fieldset>
    </div>
  )
}
