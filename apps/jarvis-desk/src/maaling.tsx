/**
 * Måle-flade: folden og runden der kommer EFTER slutbeskeden.
 *
 * ## Hvorfor den findes
 *
 * Bjørn 26/11-2026: «nogen gange ville jeg ønske du kunne se det selv». Jeg
 * kunne bevise at koden var rigtig — tests, typer, bundler, CI — men ikke se
 * hvad der faktisk stod på skærmen. Denne side er svaret: den mounter den
 * ÆGTE `RaekkeTranskript` med den ÆGTE CSS og lader en headless browser
 * fotografere hvert trin i forløbet.
 *
 * ## Forløbet der måles
 *
 * Præcis Bjørns sekvens: tre arbejdsrunder med mellem-synteser, så foldet ved
 * `final_answer`, så slutbeskeden, så ET KALD DER LANDER EFTER den. Det er den
 * sekvens der historisk fik hovedet til at blinke.
 *
 * ## Styring
 *
 * `window.__trin(n)` vælger trin. `window.__maal()` returnerer geometrien, så
 * en måling kan efterprøves uden at se på et billede.
 */
import { StrictMode, useState, useEffect } from 'react'
import { createRoot } from 'react-dom/client'
import './styles/tokens.css'
import './styles/app.css'
import './styles/chat-viewport.css'
import './styles/chat-reading.css'
import './styles/raekkevisning.css'
import './styles/turhoved.css'
import './styles/chat-flow.css'
import { RaekkeTranskript } from './components/rich/RaekkeTranskript'
import { SettingsProvider } from './contexts/SettingsContext'
import { RAEKKE_KEY } from './lib/visningsPref'
import type { ContentBlock } from './lib/sseProtocol'

localStorage.setItem(RAEKKE_KEY, '1')

const kald = (navn: string, input: Record<string, unknown>, result: string): ContentBlock => ({
  type: 'tool_use', id: `${navn}-${Math.random().toString(36).slice(2, 8)}`, name: navn, input, result,
})
const tekst = (t: string, phase?: 'commentary' | 'final_answer'): ContentBlock =>
  phase ? { type: 'text', text: t, phase } : { type: 'text', text: t }

const KALD1 = kald('bash', { command: 'git log -3 --oneline' }, '0c8ea5d40 chore(desk): 0.6.434')
const SYN1 = tekst('Bundlen er den nye. Nu tjekker jeg om den serveres.', 'commentary')
const KALD2 = kald('bash', { command: 'curl -sI api.srvlab.dk' }, 'HTTP 200 · 2459274 bytes')
const SYN2 = tekst('Den serveres live. Så mangler kun at se den.', 'commentary')
const KALD3 = kald('read_file', { path: 'raekkeModel.ts' }, 'export function opdel(...)')
const SLUT = tekst('Fold-låsen er bygget og udgivet. Grænsen læses nu af serverens stempel i stedet for af tekstens placering, og faden arver foldens varighed. Det jeg ikke har gjort er at se det rendere — og det er præcis hvad denne tur måler.', 'final_answer')
const KALD_EFTER = kald('bash', { command: 'echo "et kald efter slutbeskeden"' }, 'et kald efter slutbeskeden')

/** Trinene i forløbet. Hvert trin er en tilstand af blok-listen. */
const TRIN: { navn: string; blokke: ContentBlock[]; finalAnswerStarted: boolean; streaming: boolean }[] = [
  { navn: '1 · arbejde: første kald', blokke: [KALD1], finalAnswerStarted: false, streaming: true },
  { navn: '2 · mellem-syntese', blokke: [KALD1, SYN1], finalAnswerStarted: false, streaming: true },
  { navn: '3 · andet kald + syntese', blokke: [KALD1, SYN1, KALD2, SYN2], finalAnswerStarted: false, streaming: true },
  { navn: '4 · tredje kald', blokke: [KALD1, SYN1, KALD2, SYN2, KALD3], finalAnswerStarted: false, streaming: true },
  { navn: '5 · FOLD + slutbesked', blokke: [KALD1, SYN1, KALD2, SYN2, KALD3, SLUT], finalAnswerStarted: true, streaming: true },
  { navn: '6 · kald EFTER slutbeskeden', blokke: [KALD1, SYN1, KALD2, SYN2, KALD3, SLUT, KALD_EFTER], finalAnswerStarted: true, streaming: true },
  { navn: '7 · done', blokke: [KALD1, SYN1, KALD2, SYN2, KALD3, SLUT, KALD_EFTER], finalAnswerStarted: true, streaming: false },
]

function Maaleflade() {
  const [trin, setTrin] = useState(0)
  const t = TRIN[trin]

  useEffect(() => {
    ;(window as unknown as Record<string, unknown>).__trin = (n: number) => setTrin(n)
    ;(window as unknown as Record<string, unknown>).__antalTrin = TRIN.length
    ;(window as unknown as Record<string, unknown>).__maal = () => {
      const root = document.querySelector('.raekkevisning') as HTMLElement | null
      const hoved = document.querySelector('.rv-tur') as HTMLElement | null
      const gruppe = document.querySelector('.rv-gruppe-ydre') as HTMLElement | null
      const svar = document.querySelector('.rv-svar') as HTMLElement | null
      const mellem = document.querySelectorAll('.rv-mellem')
      const synlig = (el: Element | null): boolean => {
        if (!el) return false
        const r = (el as HTMLElement).getBoundingClientRect()
        const stil = getComputedStyle(el as HTMLElement)
        return r.height > 0.5 && stil.opacity !== '0' && stil.display !== 'none'
      }
      return {
        trin,
        navn: t.navn,
        hovedTekst: hoved?.textContent ?? null,
        hovedUdfoldet: hoved?.getAttribute('aria-expanded') ?? null,
        gruppeHoejde: gruppe ? Math.round(gruppe.getBoundingClientRect().height) : null,
        gruppeSynlig: synlig(gruppe),
        svarFindes: !!svar,
        svarSynlig: synlig(svar),
        svarTekst: svar?.textContent?.slice(0, 60) ?? null,
        antalMellemSyneser: mellem.length,
        rodHoejde: root ? Math.round(root.getBoundingClientRect().height) : null,
        heleTeksten: root?.textContent ?? null,
      }
    }
  }, [trin, t.navn])

  return (
    <div style={{ padding: 24, maxWidth: 780, margin: '0 auto' }}>
      <div style={{ fontFamily: 'monospace', fontSize: 12, opacity: 0.7, marginBottom: 12 }}>
        TRIN {trin + 1}/{TRIN.length} — {t.navn}
      </div>
      <div className="chat-flow">
        <RaekkeTranskript
          blocks={t.blokke}
          streaming={t.streaming}
          finalAnswerStarted={t.finalAnswerStarted}
          beskedId="maaling-1"
          runId="maaling-run"
        />
      </div>
    </div>
  )
}

const root = document.getElementById('root')
if (!root) throw new Error('Root mangler')
createRoot(root).render(
  <StrictMode>
    <SettingsProvider initialConfig={{ apiBaseUrl: 'http://127.0.0.1:8080', authToken: 'maaling' /* noqa: literal-credential — pladsholder, ikke en noegle */ }}>
      <Maaleflade />
    </SettingsProvider>
  </StrictMode>,
)
