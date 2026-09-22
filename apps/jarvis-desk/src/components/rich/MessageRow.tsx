import { memo } from 'react'
import type { ContentBlock } from '../../lib/sseProtocol'
import { BlocksRenderer } from './BlocksRenderer'
import { MessageActions } from './MessageActions'
import { ArtifactAffordance } from './ArtifactAffordance'
import { detectArtifacts } from '../../lib/artifacts'
import { blocksToPlainText } from '../../lib/formatTime'
import { Kilder } from './Kilder'
import { hasPasteReference, splitPasteSegments } from '../../lib/pasteSegments'
import { PasteReferenceChip } from './PasteReferenceChip'
import type { ApiConfig } from '../../lib/api'
import { InlineErrorBoundary } from '../ErrorBoundary'
import { denseBlocks } from '../../lib/blockHelpers'
import { KlikbartBillede } from './BilledLightbox'
import { RaekkeTranskript } from './RaekkeTranskript'
import { useRaekkevisning } from '../../lib/visningsPref'

/** Besked-række med locked boble-layout: bruger højre (boble), Jarvis venstre
 *  (avatar + tekst, ingen boble). Density videregives til rich-blocks.
 *
 *  memo: afsluttede beskeder har stabile props → re-renderer IKKE når
 *  StreamContext tikker (elapsed-timer hver 500ms). Det er det der gør lange
 *  samtaler tunge — uden memo highlighter hver CodeBlock forfra 2×/sekund. */
function MessageRowImpl({
  role,
  blocks: rawBlocks,
  density,
  streaming,
  rundeEtiketter,
  tankeResumeer,
  createdAt,
  onResend,
  config,
  pinned,
  onTogglePin,
  onRewind,
  beskedId,
}: {
  role: 'user' | 'assistant'
  blocks: ContentBlock[]
  density: 'compact' | 'full'
  streaming: boolean
  /**
   * Rundens overskrift slået op på tool-id — «Rettede fejl i login».
   * Udeladt = ingen overskrifter; tråden ser ud som før.
   */
  rundeEtiketter?: Record<string, string>
  /** Live tænke-resuméer (visningen «thinking»). */
  tankeResumeer?: Record<string, string>
  createdAt?: string
  /** Kun bruger-beskeder: send samme tekst igen (sparer copy-paste). */
  onResend?: (text: string) => void
  /** Til lazy paste-reference-udfoldning (GET /paste/{id}). Uden config vises chip kompakt. */
  config?: ApiConfig
  /** Om beskeden er fastgjort, og hvordan man slår det til/fra. Udeladt =
   *  ingen pin-knap; se `MessageActions`. */
  pinned?: boolean
  onTogglePin?: () => void
  /** Kun bruger-beskeder: spol tilbage hertil (Claude Desktop §8). */
  onRewind?: () => void
  /** Beskedens id — så et afkortet værktøjs-resultat kan hentes ved udfoldning. */
  beskedId?: string
}) {
  // denseBlocks ÉN gang ved indgangen: state.blocks/content kan være SPARSOMT
  // (foldede tool_result-content-blok-indices → undefined-huller). ALLE nedstrøms-
  // iteratorer (user-map, images, BlocksRenderer, detectArtifacts, blocksToPlainText)
  // tilgår b.type → et hul crashede render ved svar-slut, uden om per-besked-hegnet
  // (Bjørn 10. jul, 2. crash). Densificér her → alle downstream er hul-frie.
  // FOER det tidlige return for bruger-grenen. Et hook efter et betinget
  // return braekker hele visningen, og hverken tsc eller testene ser det
  // (maalt tidligere i dette repo).
  const raekker = useRaekkevisning()
  const blocks = denseBlocks(rawBlocks)
  if (role === 'user') {
    const text = blocks.map((b) => (b.type === 'text' ? b.text : '')).join('')
    const images = blocks.filter((b): b is Extract<ContentBlock, { type: 'image' }> => b.type === 'image')
    return (
      <div className="msg-user-wrap">
        {images.length > 0 && (
          <div className="msg-user-images">
            {/* Bruger-egne billeder (blob: preview eller server-attachment) renderes
                direkte — sanitering er forbeholdt Jarvis' (utrusted) indhold. */}
            {images.map((img, i) => <KlikbartBillede key={i} src={img.src ?? ''} alt={img.alt ?? ''} />)}
          </div>
        )}
        {text && (
          hasPasteReference(text)
            ? (
              <div className="bubble">
                {splitPasteSegments(text).map((seg, i) =>
                  seg.kind === 'text'
                    ? <span key={i}>{seg.text}</span>
                    : <PasteReferenceChip key={i} pasteId={seg.pasteId} lineCount={seg.lineCount} config={config} />,
                )}
              </div>
            )
            : <div className="bubble">{text}</div>
        )}
        {!streaming && (
          <MessageActions
            text={text}
            createdAt={createdAt}
            onResend={onResend && text ? () => onResend(text) : undefined}
            pinned={pinned}
            onTogglePin={onTogglePin}
            onRewind={onRewind}
          />
        )}
      </div>
    )
  }
  return (
    <div className="msg-jarvis-wrap">
      <article className="msg-jarvis">
        <div className="jarvis-body">
          {/* Per-besked-hegn: en render-throw i ÉN besked (fx en degenereret
              tool-blok under streaming) isoleres i stedet for at nuke hele appen
              til sort skærm. Fejlen logges (localStorage jarvis-desk:lastCrash). */}
          <InlineErrorBoundary label="assistant-blocks">
            {/* Raekkevisning bag en knap (Bjoern 22/9-2026). KUN transskriptet
                skiftes — fejlhegn, artefakter, kilder og handlinger er de samme,
                og composer/liveness/save-rail roeres ikke. */}
            {raekker
              ? <RaekkeTranskript blocks={blocks} streaming={streaming} beskedId={beskedId} config={config} />
              : <BlocksRenderer blocks={blocks} density={density} streaming={streaming} rundeEtiketter={rundeEtiketter} tankeResumeer={tankeResumeer} beskedId={beskedId} config={config} />}
            {!streaming && detectArtifacts(blocks).map((a, i) => (
              <ArtifactAffordance key={`${a.kind}-${i}`} artifact={a} />
            ))}
          </InlineErrorBoundary>
        </div>
      </article>
      {/* Kilderne står tættest på teksten: «hvor ved du det fra?».
          «Forløb»-linjen under dem er slået fra (Bjørn 17/9-2026) — runde-,
          tanke- og skill-linjerne i selve beskeden siger det samme. */}
      {!streaming && <Kilder blocks={blocks} />}
      {!streaming && (
        <MessageActions
          text={blocksToPlainText(blocks)}
          createdAt={createdAt}
          pinned={pinned}
          onTogglePin={onTogglePin}
        />
      )}
    </div>
  )
}

export const MessageRow = memo(MessageRowImpl)
