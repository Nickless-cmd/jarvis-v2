import type { ContentBlock } from '../../lib/sseProtocol'
import type { ApiConfig } from '../../lib/api'
import { groupToolRounds, type RenderBlock } from '../../lib/toolRounds'
import { denseBlocks } from '../../lib/blockHelpers'
import { MarkdownRenderer } from './MarkdownRenderer'
import { ToolCard } from './ToolCard'
import { ToolGroupCard } from './ToolGroupCard'
import { ImageBlock } from './ImageBlock'
import { AttachmentBlock } from './AttachmentBlock'
import { EditedFilesCard } from './EditedFilesCard'
import { redigeredeFiler } from '../../lib/redigeredeFiler'
import { visAendring } from '../../lib/aendringsFokus'
import { ThinkingLine } from './ThinkingLine'
import { SkillLine, SkillSurfaceLine } from './SkillLine'
import { SKILL_VAERKTOEJER } from '../../lib/skillLinje'
import { useVisningen, type Visning } from '../../lib/visning'
import { TankeResumeLinje } from './TankeResumeLinje'

type ProgressBlock = Extract<ContentBlock, { type: 'progress' }>

/**
 * Et kald han er GÅET VIDERE fra, kører ikke — uanset hvad blokken siger.
 *
 * Bjørn 17/9-2026: «mange gange står tool kørsler og pulserer selv om han er
 * videre». To veje dertil: en gemt besked hvis resultat-blok mangler (foldningen
 * starter alle kald som «running»), og en udfalds-status klienten ikke kendte.
 *
 * Regler, i den rækkefølge de afgør:
 *  - Beskeden er færdig (ikke streaming) → intet kører.
 *  - Der kommer en tekst eller tanke EFTER kaldet → modellen har fået alle
 *    resultater fra den batch og er i gang med næste runde.
 * Et andet kald efter det tæller IKKE: parallelle kald i samme batch kan blive
 * færdige i vilkårlig rækkefølge, og det ene kører stadig.
 */
export function afslutForladteKald(blocks: ContentBlock[], streaming: boolean): ContentBlock[] {
  let senereOrd = !streaming
  const ud = blocks.slice()
  for (let i = ud.length - 1; i >= 0; i--) {
    const b = ud[i]
    if (!b) continue
    if (b.type === 'text' || b.type === 'thinking') { senereOrd = true; continue }
    if (b.type === 'tool_use' && senereOrd && (b.status ?? 'running') === 'running') {
      // Beskeden er FÆRDIG og kaldet fik aldrig et resultat: udfaldet er
      // ukendt. Før blev det vist som lykkedes (18/9-2026). Mens der streames
      // kan resultatet stadig være på vej, så dér gælder den gamle regel.
      ud[i] = streaming ? { ...b, status: 'done' } : { ...b, status: 'done', anomali: 'uden-resultat' }
    }
  }
  return ud
}

/** Saml sammenhængende progress-blokke til ét ProgressTrail-element; alt andet
 *  passeres uændret. Ren transform (view-lokal) — persist/wire urørt. */
type ProgressTrailBlock = { type: 'progress_trail'; items: ProgressBlock[] }

function coalesceProgress(blocks: RenderBlock[]): (RenderBlock | ProgressTrailBlock)[] {
  const out: (RenderBlock | ProgressTrailBlock)[] = []
  let run: ProgressBlock[] = []
  const flush = () => {
    if (run.length > 0) {
      out.push({ type: 'progress_trail', items: run })
      run = []
    }
  }
  for (const b of blocks) {
    if (b.type === 'progress') {
      run.push(b as ProgressBlock)
    } else {
      flush()
      out.push(b)
    }
  }
  flush()
  return out
}

/** Dispatcher content-blocks til de rette rich-komponenter. Density-aware:
 *  videregives til ToolCard (compact|full).
 *
 *  Ren render-lags-transform: groupToolRounds folder en HEL runde vaerktoejs-
 *  kald til ét foldbart tool_group — som mobilen. Ingen wire/persist-aendring;
 *  transformen koerer her, efter fold, lige foer dispatch. */
/** Gemte runde-sætninger slået op på hvert kald de dækker. */
export function etiketterFraBlokke(blocks: ContentBlock[]): Record<string, string> {
  const ud: Record<string, string> = {}
  for (const b of blocks) {
    if (b && b.type === 'tool_use_summary') {
      for (const id of b.preceding_tool_use_ids) ud[id] = b.summary
    }
  }
  return ud
}

/** Gemte tænke-resuméer slået op på hvert kald de dækker (visningen «thinking»). */
export function resumeerFraBlokke(blocks: ContentBlock[]): Record<string, string> {
  const ud: Record<string, string> = {}
  for (const b of blocks) {
    if (b && b.type === 'tool_use_summary' && b.thinking_summary) {
      for (const id of b.preceding_tool_use_ids) ud[id] = b.thinking_summary
    }
  }
  return ud
}

export function BlocksRenderer({
  blocks,
  density,
  streaming,
  rundeEtiketter,
  tankeResumeer,
  beskedId,
  config,
}: {
  blocks: ContentBlock[]
  density: 'compact' | 'full'
  streaming: boolean
  /** Beskeden blokkene hører til — så et afkortet værktøjs-resultat kan hentes. */
  beskedId?: string
  config?: ApiConfig
  /**
   * Runde-etiketter slået op på tool-id — «Rettede fejl i login».
   *
   * Kommer fra streamens `tool_round_label`. Udeladt = ingen overskrifter;
   * tråden ser ud som før.
   */
  rundeEtiketter?: Record<string, string>
  /** Live tænke-resuméer fra streamen (visningen «thinking»). */
  tankeResumeer?: Record<string, string>
}) {
  const visning = useVisningen()
  // denseBlocks FØRST: fjern sparsomme huller (foldede tool_result-indices) FØR
  // groupToolRounds/coalesceProgress itererer med for..of — ellers crash på et
  // undefined-hul (sort skærm, Bjørn 9. jul).
  // Rundernes sætninger: de GEMTE (tool_use_summary-blokke i beskeden) plus
  // de LIVE (streamens tool_round_label). Blokkene tages ud før grupperingen —
  // midt i blokkene ville de dele en runde op.
  const taet = denseBlocks(blocks)
  const etiketter = { ...etiketterFraBlokke(taet), ...(rundeEtiketter ?? {}) }
  const udenEtiketter = taet.filter((b) => b.type !== 'tool_use_summary')
  const resumeer = { ...resumeerFraBlokke(taet), ...(tankeResumeer ?? {}) }
  // «Alt» (verbose): ingen gruppering — hvert kald står for sig og åbent.
  const afsluttet = afslutForladteKald(udenEtiketter, streaming)
  const rendered = coalesceProgress(visning === 'verbose' ? afsluttet : groupToolRounds(afsluttet))
  const lastIdx = rendered.length - 1
  // Filerne Jarvis redigerede i DENNE besked. Kortet staar nederst — som i CC
  // — og kun naar der faktisk er redigeret noget.
  const redigerede = redigeredeFiler(blocks)

  return (
    <>
      {rendered.map((b, i) => (
        <BlockView key={i} block={b} density={density} streaming={streaming} isLast={i === lastIdx} rundeEtiketter={etiketter} tankeResumeer={resumeer} visning={visning} beskedId={beskedId} config={config} />
      ))}
      <EditedFilesCard filer={redigerede} onAabn={visAendring} />
    </>
  )
}

function BlockView({
  block,
  density,
  streaming,
  isLast,
  rundeEtiketter,
  tankeResumeer,
  visning,
  beskedId,
  config,
}: {
  block: RenderBlock | ProgressTrailBlock
  density: 'compact' | 'full'
  streaming: boolean
  isLast: boolean
  /** Se `BlocksRenderer` — til at hente et afkortet værktøjs-resultat. */
  beskedId?: string
  config?: ApiConfig
  /** Rundens overskrift, slået op på kaldets id. Se `BlocksRenderer`. */
  rundeEtiketter?: Record<string, string>
  tankeResumeer?: Record<string, string>
  visning: Visning
}) {
  switch (block.type) {
    // Narrationen vises KUN mens der streames. Når turen er slut, staar den i
    // «Forløb» under beskeden — hvor den er blevet til den metadata linjen
    // manglede. Foer stod begge dele samtidig, og Bjoern saa to forloeb paa
    // samme besked (8/9-2026). Live har den stadig en opgave: den er det
    // eneste der fortaeller hvad der sker lige nu.
    case 'progress_trail':
    case 'progress':
      // «Forløb (N)» er erstattet af «Redigerede N filer» nederst i beskeden
      // (Bjørn 16/9-2026). Narrationen stod kun under streaming og forsvandt
      // bagefter; kortet bliver stående og kan klikkes.
      return null
    case 'text':
      return <MarkdownRenderer text={block.text} streaming={streaming} />
    case 'tool_group':
      {
        // Etiketten daekker HELE runden, saa det foerste kald der har en, er
        // rundens. Opslaget gaar paa kaldets id og ikke paa raekkefoelgen: en
        // sen etiket ville ellers saette sig over de forkerte kald.
        const etik = block.tools.map((t) => rundeEtiketter?.[t.id]).find(Boolean)
        // «Tænkning»: resuméet af tænkningen står OVER gruppen (Claude Desktop §2).
        const resume = visning === 'thinking' ? block.tools.map((t) => tankeResumeer?.[t.id]).find(Boolean) : undefined
        return (
          <>
            {resume ? <TankeResumeLinje tekst={resume} /> : null}
            <ToolGroupCard block={block} density={density} etiket={etik} />
          </>
        )
      }
    case 'tool_use':
      return SKILL_VAERKTOEJER.has(block.name)
        ? <SkillLine block={block} density={density} />
        : <ToolCard block={block} density={density} aabenFraStart={visning === 'verbose'}
            beskedId={beskedId} config={config} />
    case 'image':
      // LIVE billede bærer en `src` (data-URL fra streamen) og kan tegnes med
      // det samme. PERSISTERET bærer kun en reference og skal hentes med token
      // — uden denne forgrening faldt et gemt billede ud af tråden efter reload.
      return block.src
        ? <ImageBlock src={block.src} alt={block.alt} />
        : <AttachmentBlock block={{ ...block, type: 'image' }} />
    case 'file':
      // UDGIVET fil (`publish_file`) eller en vedhæftning. Havde ingen gren
      // før, så den ramte `default: return null` — filen lå i beskeden og nåede
      // aldrig skærmen (målt 15/9-2026).
      return <AttachmentBlock block={block} />
    case 'skill_surface':
      return <SkillSurfaceLine block={block} />
    case 'thinking':
      // Én linje med live-tid og fold-ud — som mobilen og runde-linjen (Bjørn
      // 16/9-2026). Før strømmede hele monologen ind i tråden og forsvandt
      // bagefter. «Live» = sidste blok mens der streames.
      return <ThinkingLine text={block.thinking} seconds={block.seconds} startet={block.startet} live={streaming && isLast && block.seconds == null} aabenFraStart={visning === 'verbose'} />
    default:
      return null
  }
}
