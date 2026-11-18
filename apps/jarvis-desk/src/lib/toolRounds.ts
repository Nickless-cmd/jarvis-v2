import type { ContentBlock } from './sseProtocol'
import { SKILL_VAERKTOEJER } from './skillLinje'

/** Ét led i en tanke: et værktøjskald eller det stykke mellemtekst der bandt
 *  det til det næste. */
export type TankeDel =
  | { slags: 'kald'; kald: Extract<ContentBlock, { type: 'tool_use' }> }
  | { slags: 'tekst'; tekst: string }

/** Render-lokal blok-type: en sammenfoldet run af read/søge-tool-kald.
 *  IKKE en del af sseProtocol.ContentBlock (wire/persist) — den findes kun i
 *  view-laget og persisteres/sendes aldrig. */
export interface ToolGroupBlock {
  type: 'tool_group'
  kind: 'round'
  count: number
  tools: Array<Extract<ContentBlock, { type: 'tool_use' }>>
  /** Hele forløbet i rækkefølge, kald og mellemtekst blandet. Sat KUN af
   *  `mergeActiveItem`; udeladt betyder «vis `tools` som før». */
  dele?: TankeDel[]
}

/** Union som render-laget dispatcher over: alle wire-blokke + den view-lokale
 *  tool_group. */
export type RenderBlock = ContentBlock | ToolGroupBlock

/**
 * Gruppér ALLE sammenhængende tool-kald til ÉN runde — 1:1 med mobilen.
 *
 * Før foldede vi kun ≥3 read/søge-kald og lod resten stå enkeltvis. Mobilen
 * grupperer HELE runden uanset værktøj: fortælling → én linje → fortælling.
 * En tekst- eller thinking-blok afslutter runden.
 *
 * Fejlede kald brydes stadig ud og står alene. En fejl må aldrig forsvinde
 * ind i «Kørte 5 værktøjer» — den er netop det man leder efter.
 */
function erSamlbar(b: RenderBlock): b is Extract<ContentBlock, { type: 'tool_use' }> {
  // Skill-kald står på deres egen linje (lib/skillLinje.ts) — i en runde ville
  // «hvilken skill, og blev den indlæst» forsvinde i «Kørte 3 ting».
  // En anomali (resultat uden kald / kald uden resultat) står også alene: den
  // er lige så meget noget man leder efter som en fejl.
  return b.type === 'tool_use' && b.status !== 'error' && !b.anomali
    && b.name !== 'pause_and_ask' && !SKILL_VAERKTOEJER.has(b.name)
}

export function groupToolRounds(blocks: RenderBlock[]): RenderBlock[] {
  const ud: RenderBlock[] = []
  let buffer: Array<Extract<ContentBlock, { type: 'tool_use' }>> = []
  const flush = () => {
    if (buffer.length === 0) return
    ud.push({ type: 'tool_group', kind: 'round', count: buffer.length, tools: buffer })
    buffer = []
  }
  for (const b of blocks) {
    if (erSamlbar(b)) buffer.push(b)
    else { flush(); ud.push(b) }
  }
  flush()
  return ud
}

/**
 * Hvor lang en mellemtekst må være og stadig være tankens stemme.
 *
 * Grænsen er ikke æstetisk, den er en skelnen: en kort sætning mellem to kald
 * («Nu retter jeg det») er modellen der tænker HØJT — den hører til tanken.
 * Et længere stykke er en replik til brugeren, og den skal ikke gemmes bag en
 * fold. Målt på denne sessions egne synteser ligger de korte på 60–200 tegn og
 * de replik-agtige over 400, så 280 skiller dem uden at ramme kanten af nogen
 * af dem. Er tallet forkert, er det ét sted at rette.
 */
const TANKE_MAKS_TEGN = 280

function erTankestemme(tekst: string): boolean {
  const t = (tekst ?? '').trim()
  return t.length > 0 && t.length <= TANKE_MAKS_TEGN
}

/**
 * Smelt sammenhængende aktiviteter til ÉN række — «forløbet skal ligne en
 * tanke, ikke en log».
 *
 * ## Hvorfor (mønster fra ChatGPT-mobil-appen, målt 14/11-2026)
 *
 * Deres `ReasoningActivitySequence` holder `items` + `activeItem` + `texts`,
 * og `mergeActiveItem` lægger en ny aktivitet IND i den aktive række i
 * stedet for at tilføje en ny. `activeTextIndex` binder teksten til den række
 * den hører til, og `continuation` i `ReasoningRenderItemData` er flaget der
 * får rækken til at fortsætte visuelt frem for at starte forfra.
 *
 * Vi havde det modsatte: `groupToolRounds` bryder runden ved ENHVER tekstblok,
 * så fem runder med mellemtekst blev fem linjer med tekst imellem. Det er en
 * log — hver handling står for sig, og læseren skal selv samle forløbet.
 *
 * ## Hvad der bliver anderledes — og hvad der IKKE gør
 *
 * Rækkefølgen bevares fuldstændig: `dele` er kald og mellemtekst i den orden
 * de kom. Intet går tabt; det flytter ind bag folden i stedet for at fylde
 * overfladen. Det er hele pointen — én linje der fortæller hvad turen lavede,
 * og detaljerne når man åbner den.
 *
 * To ting bryder stadig tanken, og det er med vilje:
 *  - en FEJL eller anomali (`groupToolRounds` lader dem stå alene) — den er
 *    netop det man leder efter, og den må ikke forsvinde i «Kørte 12 ting».
 *  - en mellemtekst der er en replik, ikke en tankestemme (se
 *    `TANKE_MAKS_TEGN`).
 *
 * Køres EFTER `groupToolRounds` og KUN i chat mode. Code mode har sin egen
 * rækkevisning (`raekkeModel.opdelArbejdsrunder`), hvor synteser bevidst står
 * frit som `syntese`-sektioner.
 */
export function mergeActiveItem(blocks: RenderBlock[]): RenderBlock[] {
  const ud: RenderBlock[] = []
  let dele: TankeDel[] = []
  let tools: Array<Extract<ContentBlock, { type: 'tool_use' }>> = []

  const flush = () => {
    if (tools.length > 0) {
      ud.push({ type: 'tool_group', kind: 'round', count: tools.length, tools, dele })
    } else {
      // Kun tekst i bufferen: der er intet at folde, så den står frit.
      for (const d of dele) if (d.slags === 'tekst') ud.push({ type: 'text', text: d.tekst })
    }
    dele = []
    tools = []
  }

  for (const b of blocks) {
    if (b.type === 'tool_group') {
      for (const kald of b.tools) {
        dele.push({ slags: 'kald', kald })
        tools.push(kald)
      }
      continue
    }
    if (b.type === 'text' && erTankestemme(b.text)) {
      dele.push({ slags: 'tekst', tekst: b.text })
      continue
    }
    flush()
    ud.push(b)
  }
  flush()
  return ud
}
