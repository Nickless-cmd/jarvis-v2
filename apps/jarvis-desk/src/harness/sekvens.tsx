/**
 * BROWSER-HARNESS — Bjørns seks trin, i den komponent der faktisk tegner skærmen.
 *
 * ## Hvorfor den findes
 *
 * Bjørn 27/11-2026: «du skal stoppe med at bygge og køre den sekvens jeg beder
 * dig om ellers har jeg aldrig en jordisk chance for at se det ske!!»
 *
 * Sekvensen er `runde → syntese → fold → slutbesked → runde → syntese`. Den
 * kunne måles i jsdom, men jsdom har ingen layout-motor: den kan sige at
 * elementet FINDES, ikke at det står det rigtige sted, har den rigtige højde
 * eller bliver revet væk af folden. Det er præcis de tre ting der er hele
 * klagen. Derfor monteres `RaekkeTranskript` uændret her — samme komponent,
 * samme CSS-importer som `App.tsx` — og Playwright skifter trinnene på den
 * SAMME monterede instans.
 *
 * ## Hvorfor `RaekkeTranskript` og ikke `ChatFlowPresentation`
 *
 * Målt 27/11-2026: code mode tegnes af `RaekkeTranskript` (`raekker`-indstillingen
 * i `CodeView`). Fem rettelser blev først lagt i chat-fladen og ramte derfor
 * intet af det Bjørn så. Den fejl skal harnessen ikke gentage.
 *
 * Køres med `npx vite --port 5199` og åbnes på
 * `http://localhost:5199/src/harness/sekvens.html`.
 */
import { StrictMode, useState } from 'react'
import { createRoot } from 'react-dom/client'
// Tokens FØRST: `raekkevisning.css` læser `--rv-h`, `--fold-varighed` og
// farvetokens herfra. Uden den falder hver `var()` tilbage til tom, og
// højderne ville være 0 — altså en harness der måler sin egen mangel.
import '../styles/tokens.css'
import '../styles/raekkevisning.css'
import { RaekkeTranskript } from '../components/rich/RaekkeTranskript'
import { SettingsProvider } from '../contexts/SettingsContext'
import { RAEKKE_KEY } from '../lib/visningsPref'
import type { ContentBlock } from '../lib/sseProtocol'
import type { ApiConfig } from '../lib/api'

// Rækkevisningen er bag en brugerindstilling. Uden dette ville komponenten
// stadig tegne — men `CodeView` er den der læser flaget, ikke komponenten.
localStorage.setItem(RAEKKE_KEY, '1')

const config: ApiConfig = {
  apiBaseUrl: 'https://api.srvlab.dk',
  authToken: 'harness', // noqa: literal-credential — dummy, intet kald går gennem den
}

/** Et værktøjskald. `result` bor PÅ kaldet — `tool_result` er ikke en egen blok. */
const kald = (navn: string, id: string, kommando: string): ContentBlock => ({
  type: 'tool_use',
  id,
  name: navn,
  input: { command: kommando },
  status: 'done',
  result: 'ok',
})

/** En mellemsyntese: tekst UDEN `phase`. Det er den der skal blive i folden. */
const syntese = (t: string): ContentBlock => ({ type: 'text', text: t })

/** Slutbeskeden: tekst MED `phase: 'final_answer'`. Det er den der låser folden. */
const slutbesked = (t: string): ContentBlock => ({ type: 'text', text: t, phase: 'final_answer' })

/**
 * De seks trin, som Bjørn skrev dem.
 *
 * Hvert trin er en HEL tilstand, ikke en delta — så et trin kan måles uden at
 * de foregående skal have kørt. `arbejdeEfterSvar` er sand fra trin 5, fordi
 * det er den tilstand en ekstra runde ankommer ind i: svaret er allerede vist,
 * og der kommer arbejde bagefter det.
 */
const TRIN: { navn: string; blocks: ContentBlock[]; streaming: boolean; finalAnswerStarted: boolean; arbejdeEfterSvar: boolean }[] = [
  {
    navn: '1-runde',
    blocks: [kald('bash', 'k1', 'git status')],
    streaming: true,
    finalAnswerStarted: false,
    arbejdeEfterSvar: false,
  },
  {
    navn: '2-syntese',
    blocks: [kald('bash', 'k1', 'git status'), syntese('Lad mig se på filen.')],
    streaming: true,
    finalAnswerStarted: false,
    arbejdeEfterSvar: false,
  },
  {
    navn: '3-fold',
    blocks: [
      kald('bash', 'k1', 'git status'),
      syntese('Lad mig se på filen.'),
      slutbesked('Sådan ser det ud.'),
    ],
    streaming: true,
    finalAnswerStarted: true,
    arbejdeEfterSvar: false,
  },
  {
    navn: '4-slutbesked',
    blocks: [
      kald('bash', 'k1', 'git status'),
      syntese('Lad mig se på filen.'),
      slutbesked('Sådan ser det ud. Rækkerne samles nu i én linje, og syntesen før foldet bliver stående i den.'),
    ],
    streaming: true,
    finalAnswerStarted: true,
    arbejdeEfterSvar: false,
  },
  {
    navn: '5-runde-efter',
    blocks: [
      kald('bash', 'k1', 'git status'),
      syntese('Lad mig se på filen.'),
      slutbesked('Sådan ser det ud. Rækkerne samles nu i én linje, og syntesen før foldet bliver stående i den.'),
      kald('remember_this', 'k2', 'gem et minde'),
    ],
    streaming: true,
    finalAnswerStarted: true,
    arbejdeEfterSvar: true,
  },
  {
    navn: '6-syntese-efter',
    blocks: [
      kald('bash', 'k1', 'git status'),
      syntese('Lad mig se på filen.'),
      slutbesked('Sådan ser det ud. Rækkerne samles nu i én linje, og syntesen før foldet bliver stående i den.'),
      kald('remember_this', 'k2', 'gem et minde'),
      syntese('Gemt.'),
    ],
    streaming: true,
    finalAnswerStarted: true,
    arbejdeEfterSvar: true,
  },
]

function Harness() {
  const [i, setI] = useState(0)
  const trin = TRIN[i]!

  // Playwright skifter trin her — samme mount, ingen remount. Et remount ville
  // nulstille fold-tilstanden og gøre hvert trin til en frisk tur, altså måle
  // noget andet end det Bjørn ser.
  ;(window as unknown as Record<string, unknown>).__sætTrin = (n: number) => setI(n)
  ;(window as unknown as Record<string, unknown>).__antalTrin = TRIN.length
  ;(window as unknown as Record<string, unknown>).__trinNavn = (n: number) => TRIN[n]?.navn

  return (
    <div style={{ padding: '24px', maxWidth: '760px' }}>
      <div
        style={{
          font: '12px ui-monospace, monospace',
          color: '#8a8a8a',
          marginBottom: '18px',
          paddingBottom: '10px',
          borderBottom: '1px solid #2a2a2a',
        }}
      >
        TRIN {i + 1}/{TRIN.length} — {trin.navn}
      </div>
      <SettingsProvider>
        <RaekkeTranskript
          blocks={trin.blocks}
          streaming={trin.streaming}
          finalAnswerStarted={trin.finalAnswerStarted}
          arbejdeEfterSvar={trin.arbejdeEfterSvar}
          beskedId="harness-besked"
          runId="harness-run"
          config={config}
          elapsedMs={7400}
          tokens={1234}
          varighedSekunder={null}
        />
      </SettingsProvider>
    </div>
  )
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <Harness />
  </StrictMode>,
)
