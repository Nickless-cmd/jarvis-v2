import type { ContentBlock } from './sseProtocol'
import type { StreamStatus } from './streamReducer'

export interface ChatFlowInput {
  blocks: readonly ContentBlock[]
  workingStep?: string | null
  rundeEtiketter?: Readonly<Record<string, string>>
  tankeResumeer?: Readonly<Record<string, string>>
  finalAnswerStarted: boolean
  status: StreamStatus
  /** Et nyt run arbejder EFTER svar-låsen. Uden dette felt ville modellen kun
   *  kende `status`, og et run mellem to streams ville se afsluttet ud mens
   *  hovedet skulle stå i `aktiv`. (18/11-2026) */
  arbejdeEfterSvar?: boolean
}

export type ChatFlowTerminalState = 'active' | 'completed' | 'interrupted' | 'failed'

/**
 * Arbejdets tilstand i turen — fire, ikke to.
 *
 * ## Hvorfor (14/11-2026)
 *
 * Arbejdsvisningen havde to tilstande: foldet ud eller foldet ind. Det er for
 * få til at svare på «hvad sker der nu», og derfor blev hver klage over fladen
 * løst med endnu en pacing-konstant i stedet for en tilstand. Seks konstanter
 * senere var grundlaget det samme.
 *
 * Bjørn undersøgte hvordan ChatGPTs app gør (hans research — ikke en kopi af
 * deres visuelle lag). Deres arbejdsrække har fire `ReasoningRowKind`:
 * `Summary`, `History`, `Active`, `Placeholder`, med fire tilsvarende
 * render-metoder. Pointen er ikke navnene, men at de er forskellige TING og
 * ikke varianter af det samme: en tom skal, en kørende aktivitet, et afsluttet
 * forløb og en opsummering opfører sig hver især forskelligt.
 *
 * Det er præcis den skelnen vi manglede. En tur der lige er startet (ingen
 * blokke endnu) blev vist som en tur uden arbejde — altså som ingenting.
 */
export type ArbejdsTilstand = 'placeholder' | 'active' | 'history' | 'summary'

/**
 * Turens hoved som fire tilstande — ikke en komponent med en fødsel og en død.
 *
 * ## Hvorfor de er eksplicitte (18/11-2026)
 *
 * MÅLT i ChatGPT-mobilens udpakkede `oai_reasoning`-modul
 * (`~/rea/reasoning/`, `ReasoningView.js`): deres hoved er ÉN komponent med
 * fire række-typer — `Summary`, `History`, `Active`, `Placeholder` — og
 * overgangen mellem dem er et `kind`-skift på en række der ALLEREDE står der.
 * Der findes ingen frame hvor turens ansigt er væk, fordi der ikke er noget
 * der monteres eller afmonteres.
 *
 * Vores hoved var gated på `!turenKoerer`, altså AFMONTERET når turen
 * sluttede — og gaten blev genåbnet ved hver ekstra runde
 * (`arbejdeEfterSvar`). Hver runde var en hel fold-cyklus, så det blinkede
 * proportionalt med antallet af runder, ikke med tiden.
 *
 * Fejlen var ikke gaten alene: ordet (`hovedTekst`) og gaten (`visTurhoved`)
 * blev udledt af HVER SIN definition af «kører». Derfor kunne hovedet sige
 * «Tænkte» mens turen stadig kørte. Tilstanden her er den ene sandhed begge
 * læser fra.
 */
export type HovedTilstand = 'aktiv' | 'formidlet' | 'afbrudt' | 'fejlet'

export interface ChatFlowModel {
  allSynthesis: string[]
  visibleSynthesis: string[]
  calmStatus: string
  workBlocks: ContentBlock[]
  finalBlocks: ContentBlock[]
  hasObservableWork: boolean
  terminalState: ChatFlowTerminalState
  /** Turens hoved som ord — «Arbejder» mens den kører, «Arbejdet» når den er
   *  færdig, og «Tænker»/«Tænkte» på en tur uden værktøjskald (17/10-2026). */
  hovedTekst: string
  /** Hvilken af de fire hoved-tilstande turen er i. Se `HovedTilstand`. */
  hovedTilstand: HovedTilstand
  /** Hvilken af de fire arbejds-tilstande turen er i. Se `ArbejdsTilstand`. */
  arbejdsTilstand: ArbejdsTilstand
}

export interface AdaptiveSnapshot {
  shortDirectRuns: number
  multiStepRuns: number
  workExpansions: number
  livingOverrides: number
  calmOverrides: number
}

// `progress` er en projektion af værktøjskaldet, og ved persistens bliver de
// blokke samlet sidst i content_json — også efter det egentlige slutsvar. De
// er arbejde i folden, men kan derfor ikke bruges som svargrænse. De øvrige
// typer følger turens kronologiske rækkefølge og markerer sidste arbejdsrunde.
const ANSWER_BOUNDARY_TYPES = new Set<ContentBlock['type']>([
  'thinking', 'skill_surface', 'tool_use_summary', 'tool_use',
  // 18/11-2026: et medie-kald er ikke længere en `tool_use` (det blev sin
  // egen part, se `image_generation_call`), men det er stadig et STYKKE
  // ARBEJDE der skiller commentary fra slutsvaret. Uden den her ville tekst
  // skrevet efter et billedkald blive læst som slutsvar — og så forsvandt
  // Jarvis' mellemregning ned i svaret.
  'image_generation_call',
])

function normalizeLine(value: string | null | undefined): string {
  return (value ?? '').replace(/\s+/g, ' ').trim()
}

/** Mechanical tool output belongs in the disclosure, never in Chat's status rail. */
export function isMeaningfulStatus(value: string): boolean {
  if (!value) return false
  if (/^(?:kalder|kører kommando|koerer kommando|bash\b|edit_file\b)/i.test(value)) return false
  // working_step kommer før den asynkrone menneskelige rundeetiket. Interne
  // navne som `operator_bash` og `search_memory` må ikke blinke frem i det
  // tidsvindue; behold den seneste gode etiket eller brug UI'ens fallback.
  if (/\b(?:operator|mcp|tool)_[a-z0-9_]+\b/i.test(value)) return false
  if (/^[a-z][a-z0-9]*(?:_[a-z0-9]+)+(?:\s*[:(].*)?$/i.test(value)) return false
  return true
}

function terminal(status: StreamStatus): Pick<ChatFlowModel, 'terminalState'> {
  if (status === 'done') return { terminalState: 'completed' }
  if (status === 'interrupted') return { terminalState: 'interrupted' }
  if (status === 'error') return { terminalState: 'failed' }
  return { terminalState: 'active' }
}

/**
 * Turens hoved som ord — hvad den laver NU, eller hvad den gjorde.
 *
 * Bjørn 17/10-2026: «istedet for arbejdsorløb så bare arbejder under kørslen og
 * arbejdet når den er færdig. og hvis det er tekst uden tool kald så tænker
 * under kørsel og tænkte efter.» Ordet bøjes altså i tid frem for at beskrive
 * et forløb, og det skelner en tur der rørte værktøjer fra en der kun tænkte.
 * Før stod der «Arbejdsforløb» i alle faser, hvilket hverken sagde hvad der
 * foregik eller om den var ovre.
 */
/**
 * De fire tilstande, udledt af ÉN «kører»-definition.
 *
 * Rækkefølgen er det, der gør dem ærlige:
 *
 * - `fejlet`/`afbrudt` vinder over alt andet — et terminalt udfald er turens
 *   sandhed, uanset hvad der ellers er i gang.
 * - `aktiv` kræver at ARBEJDET foregår: turen kører OG slutsvaret er ikke
 *   begyndt. Skriver jeg svaret, er arbejdet formidlet — også mens turen
 *   stadig løber. Den skelnen fandtes før som `!finalAnswerStarted` i
 *   `hovedTekst`; nu er den en del af tilstanden i stedet for en løs boolean.
 * - `arbejdeEfterSvar` slår `finalAnswerStarted`: et nyt run kan arbejde efter
 *   den låste besked, og så er turen aktiv igen selv om svaret står der.
 */
function hovedTilstandFor(
  state: ChatFlowTerminalState,
  koerer: boolean,
  finalAnswerStarted: boolean,
  arbejdeEfterSvar: boolean,
): HovedTilstand {
  if (state === 'failed') return 'fejlet'
  if (state === 'interrupted') return 'afbrudt'
  if (arbejdeEfterSvar) return 'aktiv'
  if (koerer && !finalAnswerStarted) return 'aktiv'
  return 'formidlet'
}

function hovedTekst(tilstand: HovedTilstand, harArbejde: boolean): string {
  switch (tilstand) {
    case 'aktiv':
      return harArbejde ? 'Arbejder' : 'Tænker'
    case 'afbrudt':
      return harArbejde ? 'Arbejdet afbrudt' : 'Afbrudt'
    case 'fejlet':
      return harArbejde ? 'Arbejdet fejlede' : 'Fejlede'
    case 'formidlet':
      return harArbejde ? 'Arbejdet' : 'Tænkte'
  }
}

function isDelivery(block: ContentBlock): boolean {
  return block.type === 'image' || block.type === 'video' || block.type === 'file'
}

/**
 * En genereret `text/html` er en widget — samme definition som `erWidget` i
 * `BlocksRenderer`. Begge betingelser skal holde: `kilde: 'generated'`
 * udelukker en UDGIVET html-fil (`publish_file`), som Bjørn selv har bedt om
 * at få som fil.
 */
function erWidget(block: ContentBlock): boolean {
  if (block.type !== 'file') return false
  return String(block.mime_type || '').toLowerCase().startsWith('text/html')
    && String(block.kilde || '') === 'generated'
    && !!String(block.attachment_id || '').trim()
}

/**
 * Leverancen hører i BUNDEN — samme regel som serverens `_leverance_i_bunden`
 * i `core/services/visible_runs_outcomes.py`.
 *
 * Bjørn 29/10-2026: «når du tegner et widget, vises det over din slut besked
 * mens der paces og derefter hopper det til under din besked». Reglen fandtes
 * kun ved persistering, så den levende tur tegnede widgetten på sit
 * oprindelige indeks — og `vis_widget` kaldes typisk i en runde FØR teksten
 * skrives, altså øverst. Da den persisterede besked (med serverens
 * rækkefølge) afløste den levende, hoppede blokken ned.
 *
 * Hoppet forsvinder kun hvis de to visninger er ENS. Derfor udledes
 * placeringen her, hvor begge veje går igennem.
 *
 * `image` og `video` røres ikke: de illustrerer det der tales om netop dér
 * (serverens `_SET_FOR_OEJET`), og bliver ved deres værktøj.
 */
function leveranceIBunden(blocks: ContentBlock[]): ContentBlock[] {
  const leverancer = blocks.filter(erWidget)
  if (leverancer.length === 0) return blocks
  const resten = blocks.filter((block) => !erWidget(block))
  // Efter den sidste blok der ikke er værktøjsstøj — ikke «bagerst i arrayet».
  // Det er forskellen mellem bagerst i DATA og bagerst i LÆSNINGEN.
  let sidste = -1
  for (let index = 0; index < resten.length; index += 1) {
    const block = resten[index]
    if (block && block.type !== 'progress') sidste = index
  }
  return [...resten.slice(0, sidste + 1), ...leverancer, ...resten.slice(sidste + 1)]
}

function synthesisLines(input: ChatFlowInput): string[] {
  const candidates: string[] = []
  for (const block of input.blocks) {
    // `blocks` kan være sparsomt: SSE'en adresserer blokke med et eksplicit
    // indeks, og falder et indeks ud (gen-tilslutning midt i et run), står der
    // et hul — og `for…of` gør et hul til `undefined`. De øvrige læsninger i
    // denne fil værner allerede (`if (block && …)`, `if (!block) continue`);
    // denne manglede, og krasjede i produktion 15/10-2026 med
    // «can't access property "type", s is undefined».
    if (block && block.type === 'tool_use_summary') candidates.push(block.summary)
  }
  candidates.push(...Object.values(input.rundeEtiketter ?? {}))
  candidates.push(...Object.values(input.tankeResumeer ?? {}))
  const step = normalizeLine(input.workingStep)
  if (isMeaningfulStatus(step)) candidates.push(step)

  const seen = new Set<string>()
  const result: string[] = []
  for (const candidate of candidates) {
    const normalized = normalizeLine(candidate)
    if (!normalized || seen.has(normalized)) continue
    seen.add(normalized)
    result.push(normalized)
  }
  return result
}

/**
 * De fire tilstande, udledt af fire fakta: kører turen, har den arbejde at
 * vise, er svaret begyndt, og står der allerede noget på skærmen.
 *
 * Rækkefølgen er en prioritering, ikke vilkårlig:
 *
 * 1. `summary` når turen er TERMINAL. Så er forløbet et faktum, og hovedet
 *    bærer ordet i datid («Arbejdet»/«Tænkte»).
 * 2. `history` når svaret er begyndt men turen stadig løber. Arbejdet er
 *    overstået, men turen er ikke — det er dét vindue hvor en to-tilstands
 *    visning enten viste for meget eller for lidt.
 * 3. `active` når der er arbejde at vise. Den kørende tilstand.
 * 4. `history` også når et direkte svar allerede skrives: der ER indhold på
 *    skærmen, så der er intet at fylde ud. (Uden denne gren ville et direkte
 *    svar vise en «Tænker»-linje oven over sin egen tekst.)
 * 5. `placeholder` ellers: turen er startet, der er intet at vise endnu.
 *    Det er den tilstand der tidligere slet ikke fandtes, og som gjorde
 *    skærmen tom i det vindue hvor turen lige var begyndt.
 */
function arbejdsTilstandFor(
  end: ChatFlowTerminalState,
  harArbejde: boolean,
  finalAnswerStarted: boolean,
  harSvar: boolean,
): ArbejdsTilstand {
  if (end !== 'active') return 'summary'
  if (finalAnswerStarted) return 'history'
  if (harArbejde) return 'active'
  if (harSvar) return 'history'
  return 'placeholder'
}

/** Derives Chat presentation without changing or generating the underlying run data. */
export function deriveChatFlow(input: ChatFlowInput): ChatFlowModel {
  const allSynthesis = synthesisLines(input)
  const visibleSynthesis = allSynthesis.slice(-3)
  const end = terminal(input.status)
  // Den ENE «kører»-definition. `arbejdeEfterSvar` dækker vinduet mellem to
  // streams, hvor `status` allerede er `done` men et nyt run er i gang.
  const koerer = input.status === 'working' || !!input.arbejdeEfterSvar
  const terminalFallback = end.terminalState !== 'active' && !input.finalAnswerStarted

  let lastWorkIndex = -1
  for (let index = 0; index < input.blocks.length; index += 1) {
    const block = input.blocks[index]
    if (block && ANSWER_BOUNDARY_TYPES.has(block.type)) lastWorkIndex = index
  }

  const workBlocks: ContentBlock[] = []
  const finalBlocks: ContentBlock[] = []
  for (let index = 0; index < input.blocks.length; index += 1) {
    const block = input.blocks[index]
    if (!block) continue
    if (isDelivery(block)) {
      finalBlocks.push(block)
    } else if (block.type === 'text') {
      // Efter et værktøj kan tekst være enten en mellemliggende syntese eller
      // slutsvaret. Placeringen alene kan ikke skelne dem: mens syntesen
      // streamer, er den midlertidigt også teksten efter det seneste kald.
      // Serveren sender `final_answer_start` FØR første synlige slutdelta, så
      // dét signal er grænsen. Et direkte svar uden værktøj kan derimod vises
      // med det samme.
      const isFinal = block.phase === 'final_answer'
        || (block.phase !== 'commentary' && (lastWorkIndex < 0
          || (index > lastWorkIndex && (input.finalAnswerStarted || terminalFallback))))
      ;(isFinal ? finalBlocks : workBlocks).push(block)
    } else {
      workBlocks.push(block)
    }
  }

  // `thinking` tæller ikke som observerbart arbejde (målt 14/11-2026): uden
  // denne udelukkelse sagde hovedet «Arbejder» på en tur der kun tænkte — og
  // «Arbejdet afbrudt» på en tur der blev afbrudt før noget arbejde. Bjørns
  // regel fra 17/10-2026 er den modsatte: «hvis det er tekst uden tool kald så
  // tænker under kørsel og tænkte efter».
  const hasObservableWork = workBlocks.some((block) => (
    (block.type !== 'text' && block.type !== 'thinking')
    || (block.type === 'text' && block.phase === 'commentary')
  )) || allSynthesis.length > 0
  return {
    allSynthesis,
    visibleSynthesis,
    calmStatus: visibleSynthesis.at(-1) ?? 'Jarvis tænker ...',
    // Runde-metadataen skal blive sammen med arbejdet. `BlocksRenderer`
    // fjerner selve metadata-blokken fra output og bruger dens ids til at
    // placere etiketten og tænke-resuméet ved den rigtige værktøjsrunde.
    workBlocks,
    // Leverancen (widgetten) lægges i bunden, så den levende tur og den
    // persisterede besked giver IDENTISK rækkefølge — se `leveranceIBunden`.
    finalBlocks: leveranceIBunden(finalBlocks),
    hasObservableWork,
    ...end,
    // «Kører» er arbejdsfasen. Det er den ENE definition: hovedets tilstand,
    // hovedets ord og visningens gate læser alle denne. Før blev ordet udledt
    // af `status === 'working' && !finalAnswerStarted`, mens gaten brugte
    // `streaming || arbejdeEfterSvar` — to svar på samme spørgsmål, og derfor
    // kunne hovedet sige «Tænkte» mens turen kørte (målt 18/11-2026).
    hovedTilstand: hovedTilstandFor(
      end.terminalState,
      koerer,
      input.finalAnswerStarted,
      !!input.arbejdeEfterSvar,
    ),
    hovedTekst: hovedTekst(
      hovedTilstandFor(
        end.terminalState,
        koerer,
        input.finalAnswerStarted,
        !!input.arbejdeEfterSvar,
      ),
      hasObservableWork,
    ),
    arbejdsTilstand: arbejdsTilstandFor(
      end.terminalState,
      hasObservableWork,
      input.finalAnswerStarted,
      finalBlocks.some((block) => block.type !== 'text' || block.text.trim().length > 0),
    ),
  }
}

/** Deterministic and intentionally conservative; callers cache this once per run. */
export function chooseAdaptiveMode(snapshot: AdaptiveSnapshot): 'living' | 'calm' {
  if (snapshot.workExpansions + snapshot.livingOverrides >= snapshot.calmOverrides + 2) {
    return 'living'
  }
  if (
    snapshot.shortDirectRuns >= 4
    && snapshot.shortDirectRuns >= snapshot.multiStepRuns * 2
    && snapshot.calmOverrides >= snapshot.livingOverrides
  ) {
    return 'calm'
  }
  return 'living'
}
