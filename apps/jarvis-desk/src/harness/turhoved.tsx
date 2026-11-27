/**
 * BROWSER-HARNESS — den ÆGTE komponent, målt med rigtig layout-motor.
 *
 * jsdom har ingen layout-motor, så `max-height`-transitionen i
 * `chat-flow.css` kan ikke måles der. En statisk læsning af CSS-filen beviser
 * kun at egenskaben STÅR i filen, ikke at containeren mister sin højde.
 *
 * Denne harness monterer `ChatFlowPresentation` uændret (samme komponent,
 * samme CSS-importer) og lader Playwright skifte turen fra live til terminal
 * på den SAMME monterede instans. Kun sådan kan kollapset måles som højde.
 *
 * Køres med `npx vite --port 5199` og åbnes på
 * `http://localhost:5199/src/harness/turhoved.html`.
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

/** Kun besvarelse — ingen runde. `fladtFlow` er FALSK i denne form. */
const UDEN_RUNDE: ContentBlock[] = [
  { type: 'text', text: 'Første besvarelse, som skal blive stående gennem hele forløbet.', phase: 'final_answer' },
]

/** Besvarelse + værktøjskald: nu findes en runde EFTER svaret, så `fladtFlow` bliver SAND. */
const MED_RUNDE: ContentBlock[] = [
  ...UDEN_RUNDE,
  // Ingen `tool_result`-blok: typen findes ikke i `ContentBlock` — resultatet
  // hænger på selve `tool_use`. Runden opstår af kaldet alene.
  { type: 'tool_use', id: 'kald-1', name: 'bash', input: { command: 'echo hej' } },
]

interface Tilstand {
  streaming: boolean
  status: StreamStatus
  arbejdeEfterSvar: boolean
}

const LIVE: Tilstand = { streaming: false, status: 'working', arbejdeEfterSvar: true }
const TERMINAL: Tilstand = { streaming: false, status: 'done', arbejdeEfterSvar: false }

function Harness() {
  const [t, setT] = useState<Tilstand>(LIVE)
  const [medRunde, setMedRunde] = useState(false)

  // Playwright styrer tilstanden herfra — samme mount, ingen remount.
  ;(window as unknown as Record<string, unknown>).__sætTilstand = (navn: 'live' | 'terminal') =>
    setT(navn === 'live' ? LIVE : TERMINAL)
  ;(window as unknown as Record<string, unknown>).__sætBlokke = (navn: 'uden-runde' | 'med-runde') =>
    setMedRunde(navn === 'med-runde')

  const blocks = medRunde ? MED_RUNDE : UDEN_RUNDE

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
