/**
 * Visuelt stillads til Arbejde-fladen — ikke en del af appen.
 *
 * Aabnes med `npm run dev` og saa /desk-audit.html. Den monterer CoworkView
 * med en fikstur-SettingsContext og en ejer-rolle, saa man kan klikke alle
 * kategorier igennem uden at logge ind og uden en koerende backend.
 *
 * API'et peger MED VILJE paa /audit-api, som ikke findes: saa fejler hvert
 * eneste kald, og fladen viser sine fejl-tilstande. Det var praecis dét der
 * afsloerede at Mission Controls forside skrev «alt roligt» over fem nuller
 * mens den intet vidste (21/9-2026).
 *
 * Den ligger i src/ og ikke i roden, fordi tsconfig kun daekker src — udenfor
 * stod den uden for baade tsc og eslint og kunne raadne tavst. Da jeg flyttede
 * den ind, fandt tsc straks to fejl i den.
 */
import { createRoot } from 'react-dom/client'
import { CoworkView } from './views/CoworkView'
import { SettingsContext } from './contexts/SettingsContext'
import { COWORK_ZONES, emitZone } from './lib/coworkZone'
import { AiTransparencyNotice } from './components/AiTransparencyNotice'
import './styles/tokens.css'
import './styles/app.css'
import './styles/cheap-lane.css'
import './styles/cowork-categories.css'
import './styles/desk-settings.css'
// Husets maade at naa broen paa — `window.jarvisDesk` findes ikke paa Window.
;(window as unknown as { jarvisDesk?: unknown }).jarvisDesk =
  { config: { get: async () => ({ channelPlugins: [] }), set: async () => true } }
localStorage.setItem('jarvis-desk:ai-notice-v1','1')
const value = {
  settings: {
    // /audit-api findes ikke — se hvorfor oeverst i filen.
    apiBaseUrl: location.origin + '/audit-api',
    authToken: 'fixture', // noqa: literal-credential — ordet er hele pointen
    theme: 'dark', defaultModel: 'demo', defaultThinking: 'think', trustDefault: 'ask',
  },
  auth: { role: 'owner' },
  isConfigured: true,
  update: async () => {},
}
createRoot(document.getElementById('root')!).render(<SettingsContext.Provider value={value as any}>
 <div className="window"><nav aria-label="Kategorier" style={{width:245,flexShrink:0,padding:18,overflow:'auto'}}>{COWORK_ZONES.map(z=><button style={{display:'block',width:'100%',padding:9,textAlign:'left',background:'transparent',color:'var(--fg-1)',border:0,cursor:'pointer'}} onClick={()=>emitZone(z.id)} key={z.id}>{z.label}</button>)}</nav><main className="main"><CoworkView role="owner" sessionId="audit" /></main></div><AiTransparencyNotice />
</SettingsContext.Provider>)
