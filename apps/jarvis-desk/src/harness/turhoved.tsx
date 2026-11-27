/**
 * BROWSER-HARNESS — den ÆGTE komponent, målt med rigtig layout-motor.
 *
 * jsdom har ingen layout-motor, så kollapset kan ikke måles der. En statisk
 * læsning af CSS-filen beviser kun at egenskaben STÅR i filen, ikke at
 * containeren mister sin højde eller at besvarelserne glider sammen.
 *
 * Denne harness monterer `ChatFlowPresentation` uændret (samme komponent,
 * samme CSS-importer) og lader Playwright skifte turen fra live til terminal
 * på den SAMME monterede instans. Kun sådan kan kollapset måles som højde.
 *
 * Køres med `npx vite --port 5199` og åbnes på
 * `http://localhost:5199/src/harness/turhoved.html`.
 *
 * ## Hvad den kan (Bjørn 27/11-2026)
 *
 * «Udvid browsermålingen til at følge den faktiske afstand mellem besvarelse A
 * og B, med rundecontaineren imellem. Mål flere forskellige containerhøjder,
 * og kræv at både synlighed og den samlede optagede plads reduceres
 * kontinuerligt.»
 *
 * Derfor kan `__sætHoejde` vælge hvor meget arbejde runden bærer, så kollapset
 * måles ved både en lav og en høj container — `1fr → 0fr` skal virke ens for
 * begge, hvor `max-height`-loftet ikke gjorde.
 */
import { StrictMode, useState } from 'react'
import { createRoot } from 'react-dom/client'
// Tokens FØRST: `--fold-varighed: var(--dur-sheet)` peger på en token der bor
// her. Uden den er transitionen ugyldig og falder tilbage til øjeblikkelig —
// så et kollaps ville se hårdt ud i harnessen uden at være det i app'en.
import '../styles/tokens.css'
import { ChatFlowPresentation } from '../components/rich/ChatFlowPresentation'
import type { ContentBlock } from '../lib/sseProtocol'
import type { StreamStatus } from '../lib/streamReducer'
import type { ApiConfig } from '../lib/api'

const config: ApiConfig = {
  apiBaseUrl: 'https://api.srvlab.dk',
  authToken: 'harness', // noqa: literal-credential — dummy, intet kald går gennem den
}

const SVAR_A: ContentBlock = {
  type: 'text',
  text: 'Første besvarelse, som skal blive stående gennem hele forløbet.',
  phase: 'final_answer',
}
const SVAR_B: ContentBlock = {
  type: 'text',
  text: 'Anden besvarelse, som skal glide op mod den første.',
  phase: 'final_answer',
}

/** Hvor meget arbejde runden bærer — styrer containerens højde. */
type Hoejde = 'lav' | 'hoej'

function rundeBlokke(hoejde: Hoejde): ContentBlock[] {
  const antal = hoejde === 'lav' ? 1 : 6
  return Array.from({ length: antal }, (_, i) => ({
    type: 'tool_use' as const,
    id: `kald-${i}`,
    name: 'bash',
    input: { command: `echo trin ${i}` },
  }))
}

interface Tilstand {
  streaming: boolean
  status: StreamStatus
  arbejdeEfterSvar: boolean
}

const LIVE: Tilstand = { streaming: false, status: 'working', arbejdeEfterSvar: true }
const TERMINAL: Tilstand = { streaming: false, status: 'done', arbejdeEfterSvar: false }

function Harness() {
  const [t, setT] = useState<Tilstand>(LIVE)
  const [fase, setFase] = useState<'uden' | 'med'>('uden')
  const [hoejde, setHoejde] = useState<Hoejde>('lav')

  // Playwright styrer tilstanden herfra — samme mount, ingen remount.
  ;(window as unknown as Record<string, unknown>).__sætTilstand = (navn: 'live' | 'terminal') =>
    setT(navn === 'live' ? LIVE : TERMINAL)
  ;(window as unknown as Record<string, unknown>).__sætBlokke = (navn: 'uden-runde' | 'med-runde') =>
    setFase(navn === 'med-runde' ? 'med' : 'uden')
  ;(window as unknown as Record<string, unknown>).__sætHoejde = (navn: Hoejde) => setHoejde(navn)

  // A → runde → B: runden ligger MELLEM de to besvarelser, så afstanden
  // mellem dem er det brugeren ser når containeren kollapser.
  const blocks: ContentBlock[] =
    fase === 'med' ? [SVAR_A, ...rundeBlokke(hoejde), SVAR_B] : [SVAR_A]

  return (
    <div className="transcript" style={{ padding: '24px', maxWidth: '760px' }}>
      <ChatFlowPresentation
        blocks={blocks}
        mode="living"
        density="full"
        streaming={t.streaming}
        status={t.status}
        finalAnswerStarted
        arbejdeEfterSvar={t.arbejdeEfterSvar}
        runId="harness-run"
        turId="harness-tur"
        turStart={Date.now() - 4000}
        beskedId="harness-besked"
        config={config}
      />
    </div>
  )
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <Harness />
  </StrictMode>,
)
