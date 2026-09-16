import type { ContentBlock } from '../../lib/sseProtocol'
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
import { LiveVerb } from '../shell/LiveVerb'

type ProgressBlock = Extract<ContentBlock, { type: 'progress' }>

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
export function BlocksRenderer({
  blocks,
  density,
  streaming,
  rundeEtiketter,
}: {
  blocks: ContentBlock[]
  density: 'compact' | 'full'
  streaming: boolean
  /**
   * Runde-etiketter slået op på tool-id — «Rettede fejl i login».
   *
   * Kommer fra streamens `tool_round_label`. Udeladt = ingen overskrifter;
   * tråden ser ud som før.
   */
  rundeEtiketter?: Record<string, string>
}) {
  // denseBlocks FØRST: fjern sparsomme huller (foldede tool_result-indices) FØR
  // groupToolRounds/coalesceProgress itererer med for..of — ellers crash på et
  // undefined-hul (sort skærm, Bjørn 9. jul).
  const rendered = coalesceProgress(groupToolRounds(denseBlocks(blocks)))
  const lastIdx = rendered.length - 1
  // Filerne Jarvis redigerede i DENNE besked. Kortet staar nederst — som i CC
  // — og kun naar der faktisk er redigeret noget.
  const redigerede = redigeredeFiler(blocks)

  return (
    <>
      {rendered.map((b, i) => (
        <BlockView key={i} block={b} density={density} streaming={streaming} isLast={i === lastIdx} rundeEtiketter={rundeEtiketter} />
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
}: {
  block: RenderBlock | ProgressTrailBlock
  density: 'compact' | 'full'
  streaming: boolean
  isLast: boolean
  /** Rundens overskrift, slået op på kaldets id. Se `BlocksRenderer`. */
  rundeEtiketter?: Record<string, string>
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
        return <ToolGroupCard block={block} density={density} etiket={etik} />
      }
    case 'tool_use':
      return <ToolCard block={block} density={density} />
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
    case 'thinking': {
      // "Live" = han tænker lige NU (sidste blok + streamer stadig) → vis
      // "tænker…" + den ægte thinking-content mens den strømmer.
      const live = streaming && isLast
      // FORBI-tænkning skjules. Den sammenfoldede "tænkte…"-chip var legacy fra
      // FØR vi havde ægte thinking-content — en hardcoded label der bare stod
      // tilbage som rod mellem tool-kald og i færdige beskeder (Bjørn 2026-06-13).
      // Den ægte thinking-content forsvinder som den skal; labelen skal også væk.
      if (!live) return null
      return (
        <div className="thinking live">
          <LiveVerb text="tænker" />
          <MarkdownRenderer text={block.thinking} streaming />
        </div>
      )
    }
    default:
      return null
  }
}
