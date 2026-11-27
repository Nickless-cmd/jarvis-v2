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

/**
 * Runde-blokke med en RUNDE-PRÆFIKS i id'et.
 *
 * `kildeNoegle` bygger segment-id'et på `tool_use.id`, så to runder der
 * genererer de samme id'er får SAMME React-key. Det er en anden fejl end den
 * der måles her, og den ville sløre resultatet: React kan ikke skelne børnene,
 * og så kan man ikke afgøre om en hængende container skyldes den delte ref
 * eller de kolliderende keys. Præfikset holder dem adskilt.
 */
function rundeBlokke(hoejde: Hoejde, runde = 0): ContentBlock[] {
  const antal = hoejde === 'lav' ? 1 : 6
  return Array.from({ length: antal }, (_, i) => ({
    type: 'tool_use' as const,
    id: `r${runde}-kald-${i}`,
    name: 'bash',
    input: { command: `echo trin ${i}` },
  }))
}

/**
 * Blok-sættene.
 *
 * `to-runder` findes fordi `kollapsRef` er ÉN ref til ALLE runde-containere
 * (GPT, 27/11-2026). Med ét runde-segment kan den fejl ikke måles — ref'en
 * peger på den eneste container der findes, og alt ser rigtigt ud. Først med
 * to selvstændige containere kan man se om hver af dem afmonteres på sit eget
 * `transitionend`, eller om de deler én fælles tilstand.
 *
 * `[runde, besvarelse, runde]` giver præcis to runde-segmenter: `byggSegmenter`
 * slår kun sammen når `sidste.slags === rolle`, så besvarelsen i midten bryder
 * sammenlægningen. To `tool_use`-blokke i træk ville smelte til ét segment.
 */
type Fase = 'uden' | 'med' | 'to-runder' | 'ekstra-runde' | 'kun-svar'

interface Tilstand {
  streaming: boolean
  status: StreamStatus
  arbejdeEfterSvar: boolean
}

const LIVE: Tilstand = { streaming: false, status: 'working', arbejdeEfterSvar: true }
const TERMINAL: Tilstand = { streaming: false, status: 'done', arbejdeEfterSvar: false }

function Harness() {
  const [t, setT] = useState<Tilstand>(LIVE)
  const [fase, setFase] = useState<Fase>('uden')
  const [hoejde, setHoejde] = useState<Hoejde>('lav')

  // Playwright styrer tilstanden herfra — samme mount, ingen remount.
  ;(window as unknown as Record<string, unknown>).__sætTilstand = (navn: 'live' | 'terminal') =>
    setT(navn === 'live' ? LIVE : TERMINAL)
  // De gamle navne (`med-runde`/`uden-runde`) oversættes her. Syv kaldesteder
  // i de øvrige målinger bruger dem, og en omdøbning af fasen må ikke gøre
  // dem tavst til no-ops: `setFase('med-runde')` ville ellers sætte en
  // ugyldig værdi, ramme `else`-grenen og give nul runde-containere — hvorefter
  // målingen ville time ud på `waitForSelector` uden at sige hvorfor.
  ;(window as unknown as Record<string, unknown>).__sætBlokke = (navn: string) => {
    const oversat: Fase =
      navn === 'med-runde' ? 'med' : navn === 'uden-runde' ? 'uden' : (navn as Fase)
    setFase(oversat)
  }
  ;(window as unknown as Record<string, unknown>).__sætHoejde = (navn: Hoejde) => setHoejde(navn)

  // A → runde → B: runden ligger MELLEM de to besvarelser, så afstanden
  // mellem dem er det brugeren ser når containeren kollapser.
  //
  // `uden` er REFERENCEN (GPT, 27/11-2026: «Referencemålingen for gap'et er
  // stadig cirkulær»). Den skal have BEGGE besvarelser — ellers findes der
  // ingen afstand at måle, og referencen bliver `null`. Før gav den kun
  // `[SVAR_A]`, så sammenligningen var tom.
  const blocks: ContentBlock[] =
    fase === 'med'
      ? [SVAR_A, ...rundeBlokke(hoejde), SVAR_B]
      : fase === 'to-runder'
        ? [...rundeBlokke(hoejde, 0), SVAR_A, ...rundeBlokke(hoejde, 1)]
        : fase === 'ekstra-runde'
          // Bjørns forløb 27/11-2026: slutsvaret er ALLEREDE vist, pacen kører
          // stadig — og så ankommer en ekstra runde EFTER det. Det er den eneste
          // bloksekvens hvor `plassering` bliver `'efter'` for et runde-segment,
          // og dermed den eneste der kan gøre `fladtFlow` sand MIDT i en tur.
          ? [SVAR_A, ...rundeBlokke(hoejde)]
          // `kun-svar` er den TILSTAND runden ankommer ind i: samme besvarelse,
          // ingen runde. Uden den er der intet at sammenligne med — `uden` har
          // to besvarelser, så svar-højden ændrer sig af en anden grund end
          // runden, og målingen ville tilskrive runden en forskel der ikke er
          // dens.
          : fase === 'kun-svar'
            ? [SVAR_A]
            : [SVAR_A, SVAR_B]

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
