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
 * ## To flader, to forskellige beviser
 *
 * `?flade=` vælger hvad der måles, og forskellen er ikke kosmetisk:
 *
 * - **standard (ingen parameter)** — `Maaleflade`. Folder geometrien gennem
 *   `RaekkeTranskript`. Dens `PaceProbe` kalder den ægte hook, men er en
 *   SØSKENDEkomponent der returnerer `null`. Den beviser at mekanismen holder;
 *   den beviser IKKE at transskriptets egen pacer gør. (GPT 26/11-2026.)
 *
 * - **`?flade=pace`** — `PaceIntegrationsflade`. Mounter den ægte
 *   `ChatFlowPresentation`, som ER den komponent der leverer teksten til
 *   brugeren, og læser pacens cursor ud af DOM'en. Det er integrationen, ikke
 *   mekanismen — og det er den eneste måling der kan svare på om folden rører
 *   den pacer brugeren faktisk ser.
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
import { ChatFlowPresentation } from './components/rich/ChatFlowPresentation'
import { useChatPacedBlocks } from './lib/useChatPacedBlocks'
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

/**
 * MEKANISME-PROBEN — måler at hooken holder, ikke at integrationen gør.
 *
 * Bjørn 26/11-2026: «fraværet af direkte pace-operationer ved fold-toggle
 * beviser ikke, at pacen er upåvirket. Indirekte remount, ændrede props,
 * ændret komponentidentitet og ændret dataprojektion skal måles.»
 *
 * ⚠️ HVAD DENNE KOMPONENT IKKE BEVISER (GPT 26/11-2026, og han har ret):
 * den er en SØSKENDE til transskriptet og returnerer `null`. Den har sin egen
 * pacer og sin egen livscyklus. At den fortsætter mens en ANDEN komponent
 * folder, siger intet om den pacer der leverer teksten til brugeren. Det gør
 * `PaceIntegrationsflade` nedenfor — denne her er kun mekanismen.
 *
 * `__skiftNoegle(true)` er MODPRØVEN: den skifter nøglen med vilje, så
 * målingen kan bevise at den kan fejle. En probe der aldrig kan fejle måler
 * intet.
 */
const PROBE_TEKST =
  'Fold-låsen er bygget. Grænsen læses nu af serverens stempel i stedet for af tekstens placering, og faden arver foldens varighed. ' +
  'Det jeg ikke har gjort er at se det rendere — og det er præcis hvad denne måling skal afgøre, tegn for tegn, gennem hvert fold.'

function PaceProbe({ turId }: { turId: string }) {
  const [noegleSkift, setNoegleSkift] = useState(false)
  // `koersel` bumper nøglen, så cursoren starter TOM og pacingen begynder forfra
  // på kommando. Uden den er teksten allerede færdig når scriptet måler, og så
  // beviser en stabil nøgle ingenting — der var intet at afbryde.
  const [koersel, setKoersel] = useState(0)
  const paceNoegle = noegleSkift
    ? `tur-${turId}-MODPROEVE`
    : `tur-${turId}-k${koersel}`
  const blokke: ContentBlock[] = [{ type: 'text', text: PROBE_TEKST, phase: 'final_answer' }]
  const paced = useChatPacedBlocks(blokke, {
    live: true,
    finalAnswerStarted: true,
    runId: paceNoegle,
  })
  const vist = (paced[0] && paced[0].type === 'text' ? paced[0].text : '') ?? ''
  const vistTegn = Array.from(vist).length

  useEffect(() => {
    const w = window as unknown as Record<string, unknown>
    w.__pace = () => ({ key: `${paceNoegle}:chat-text`, vistTegn, targetTegn: Array.from(PROBE_TEKST).length })
    w.__skiftNoegle = (paa: boolean) => setNoegleSkift(paa)
    w.__startPace = () => setKoersel((n) => n + 1)
  }, [paceNoegle, vistTegn])

  return null
}

function Maaleflade() {
  const [trin, setTrin] = useState(0)
  const t = TRIN[trin] ?? TRIN[0]!

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
        <PaceProbe turId="maaling-tur-1" />
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

/**
 * INTEGRATIONS-MÅLINGEN — den pacer brugeren faktisk ser.
 *
 * GPT 26/11-2026: «Han beviser dermed, at en isoleret pacer fortsætter, mens
 * en anden komponent folder. Han beviser ikke, at den pacer, der faktisk
 * leverer teksten til brugerens transskript, overlever foldet. Det kræver, at
 * han instrumenterer den eksisterende pace-instans i `ChatFlowPresentation`.»
 *
 * Derfor mounter denne flade `ChatFlowPresentation` selv — komponenten der
 * kalder `useChatPacedBlocks` og renderer resultatet. Der er ingen probe ved
 * siden af: det er den samme instans, den samme hook-kald og den samme
 * React-node som i produktion.
 *
 * Cursoren læses ud af DOM'en, ikke ud af hook-state. Det er bevidst: en
 * remount der nulstiller paceren ville stadig efterlade hookens state korrekt
 * i den nye instans — kun den viste tekst afslører at den begyndte forfra.
 *
 * Teksten måles som det længste PRÆFIKS af slutsvaret der findes i sidens
 * tekst. Det gør målingen uafhængig af CSS-klassenavne og af hvordan
 * ord-animationen deler teksten i spans.
 */
const INT_SLUT =
  'Fold-låsen er bygget, og grænsen læses nu af serverens stempel i stedet for af tekstens placering. ' +
  'Det jeg ikke har gjort er at se det rendere gennem den pacer der faktisk leverer teksten til brugeren, ' +
  'og det er præcis hvad denne måling skal afgøre: om den viste tekst fortsætter monotont gennem hvert fold, ' +
  'eller om den falder tilbage til et tidligere punkt fordi komponenten blev remounted. ' +
  'En søskendeprobe kan ikke svare på det, fordi den har sin egen pacer og sin egen livscyklus, ' +
  'og derfor ville den fortsætte uanset hvad der skete med den pacer brugeren ser.'

const INT_BLOKKE: ContentBlock[] = [
  kald('bash', { command: 'git log -1' }, '916a1670c fix(desk): turens id'),
  tekst('Nu ser jeg på om pacen overlever foldet.', 'commentary'),
  kald('read_file', { path: 'ChatFlowPresentation.tsx' }, 'useChatPacedBlocks(blocks, {…})'),
  { type: 'text', text: INT_SLUT, phase: 'final_answer' },
]

const normaliser = (s: string): string => s.replace(/\s+/g, ' ').trim()

function PaceIntegrationsflade() {
  // `turId` er en prop og ikke en konstant, fordi MODPRØVEN skal kunne skifte
  // den: skifter identiteten, skifter pacing-nøglen, og cursoren SKAL falde.
  // Uden den kontrol kan en grøn måling lige så godt skyldes at paceren aldrig
  // reagerede på noget som helst.
  const [turId, setTurId] = useState('maaling-tur-int')

  useEffect(() => {
    const w = window as unknown as Record<string, unknown>
    const maal = normaliser(INT_SLUT)

    // Cursoren = hvor langt et SAMMENHÆNGENDE præfiks af slutsvaret der står
    // på skærmen. Falder tallet, er svaret pacet forfra.
    w.__intMaal = () => {
      const alt = normaliser(document.body.textContent ?? '')
      let n = 0
      while (n < maal.length && alt.includes(maal.slice(0, n + 1))) n++
      const hoved = document.querySelector('[aria-expanded]')
      return {
        vistTegn: n,
        targetTegn: maal.length,
        udfoldet: hoved?.getAttribute('aria-expanded') ?? null,
      }
    }

    // Fold-toggle uden at kende klassens navn: hovedet er det element der
    // bærer `aria-expanded`.
    w.__intFold = () => {
      const hoved = document.querySelector('[aria-expanded]') as HTMLElement | null
      if (!hoved) return { klikket: false, udfoldet: null }
      hoved.click()
      return { klikket: true, udfoldet: hoved.getAttribute('aria-expanded') }
    }

    w.__intSkiftTur = (ny: string) => setTurId(ny)
  }, [])

  return (
    <div style={{ padding: 24, maxWidth: 780, margin: '0 auto' }}>
      <div style={{ fontFamily: 'monospace', fontSize: 12, opacity: 0.7, marginBottom: 12 }}>
        INTEGRATION — ægte ChatFlowPresentation, cursor læst fra DOM
      </div>
      <div className="chat-flow">
        <ChatFlowPresentation
          blocks={INT_BLOKKE}
          mode="living"
          density="full"
          streaming={true}
          status="working"
          finalAnswerStarted={true}
          turId={turId}
          runId="maaling-run-int"
          beskedId="maaling-int-1"
        />
      </div>
    </div>
  )
}

const fladeNavn = new URLSearchParams(window.location.search).get('flade')

const root = document.getElementById('root')
if (!root) throw new Error('Root mangler')
createRoot(root).render(
  <StrictMode>
    <SettingsProvider initialConfig={{ apiBaseUrl: 'http://127.0.0.1:8080', authToken: 'maaling' /* noqa: literal-credential — pladsholder, ikke en noegle */ }}>
      {fladeNavn === 'pace' ? <PaceIntegrationsflade /> : <Maaleflade />}
    </SettingsProvider>
  </StrictMode>,
)
