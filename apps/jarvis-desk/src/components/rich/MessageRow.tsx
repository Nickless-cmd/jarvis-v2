import { memo, useEffect, useRef } from 'react'
import type { ContentBlock } from '../../lib/sseProtocol'
import { BlocksRenderer } from './BlocksRenderer'
import { MessageActions } from './MessageActions'
import { ArtifactAffordance } from './ArtifactAffordance'
import { detectArtifacts } from '../../lib/artifacts'
import { blocksToPlainText } from '../../lib/formatTime'
import { Kilder } from './Kilder'
import { hasPasteReference, splitPasteSegments } from '../../lib/pasteSegments'
import { PasteReferenceChip } from './PasteReferenceChip'
import { apiFetch, type ApiConfig } from '../../lib/api'
import { InlineErrorBoundary } from '../ErrorBoundary'
import { denseBlocks } from '../../lib/blockHelpers'
import { KlikbartBillede } from './BilledLightbox'
import { AttachmentBlock } from './AttachmentBlock'
import { RaekkeTranskript } from './RaekkeTranskript'
import { useRaekkevisning } from '../../lib/visningsPref'
import { EditedFilesCard } from './EditedFilesCard'
import { maalteRedigeringer, redigeredeDiffPar, redigeredeFiler } from '../../lib/redigeredeFiler'
import { visAendring } from '../../lib/aendringsFokus'
import { usePacedBlocks } from '../../lib/usePacedBlocks'
import { useChatPacedBlocks } from '../../lib/useChatPacedBlocks'
import { usePaceMode } from '../../lib/streamPacing'
import { ChatFlowPresentation } from './ChatFlowPresentation'
import type { StreamStatus } from '../../lib/streamReducer'
import type { ActiveChatFlowMode } from '../../lib/chatFlowApi'
import { usePacingWorkLine } from '../../lib/usePacingWorkLine'

function CodeAssistantTranscript({ blocks, density, streaming, finalAnswerStarted, beskedId, config,
  rundeEtiketter, tankeResumeer, raekker, elapsedMs, tokens, varighedSekunder, runId, onPaced }: {
  blocks: ContentBlock[]
  density: 'compact' | 'full'
  streaming: boolean
  finalAnswerStarted: boolean
  beskedId?: string
  config?: ApiConfig
  rundeEtiketter?: Record<string, string>
  tankeResumeer?: Record<string, string>
  raekker: boolean
  elapsedMs?: number
  tokens?: number
  varighedSekunder?: number | null
  /** Kørslens id — pacing-cursoren nøgles på det, så to beskeder ikke deler ur. */
  runId?: string | null
  /** Kaldes når pacingen har indhentet hele teksten (se `pacingFaerdig`). */
  onPaced?: () => void
}) {
  // ── To ure, ét valg (19/10-2026) ────────────────────────────────────────
  //
  // Begge hooks KALDES ubetinget — hooks-reglen forbyder en betinget call. Men
  // kun det valgte lag er AKTIVT: `live` er false for det andet, og så starter
  // hverken dets interval eller dets frame-løkke. En ubetinget call er derfor
  // ikke det samme som to kørende ure.
  //
  // Nøglen er `runId` og ikke kun beskedens id: cursoren ligger i hookets
  // state under `${runId}:chat-text`, og uden et unikt id pr. kørsel ville
  // alle levende beskeder dele ét ur og hoppe mellem hinanden. Persisterede
  // beskeder er inaktive (streaming=false → `harVaeretLive` er falsk), så de
  // rører aldrig cursoren; `beskedId` er kun faldback for en levende besked
  // der endnu ikke har fået sit run-id.
  const paceMode = usePaceMode()
  const jaevn = paceMode === 'chat'
  const chatPaced = useChatPacedBlocks(blocks, {
    live: streaming && jaevn,
    finalAnswerStarted,
    // Også arbejdets narration paces — samme kurve som Chat Mode. Se
    // `streamPacing.ts`: forskellen mellem de to lag er kurven, ikke træet.
    paceAllText: streaming && jaevn,
    runId: runId ?? beskedId ?? null,
  })
  const codePaced = usePacedBlocks(blocks, streaming && !jaevn)
  const paced = jaevn ? chatPaced : codePaced
  // ── Hvornår er pacingen FÆRDIG? (målt 20/10-2026) ────────────────────────
  //
  // Code mode holdt før kun den levende række på skærmen mens `status` var
  // `working`. Ved `done` blev den revet ned, og den persisterede række lagt
  // ind med HELE svaret i samme frame — så pacen rullede et par linjer og
  // derefter landede resten i ét hug (Bjørn: «bang så lander hele svaret»).
  //
  // Paceren selv er uskyldig: den fortsætter efter `message_stop` via
  // `harVaeretLive`. Det var VISNINGEN der blev skiftet ud midt i kurven.
  // Chat-laget har længe haft `onAnswerPaced`; nu melder code-grenen også.
  const alleTekst = blocks.flatMap((b) => (b?.type === 'text' ? [b.text] : [])).join('')
  const vistTekst = paced.flatMap((b) => (b?.type === 'text' ? [b.text] : [])).join('')
  const pacingFaerdig = alleTekst.length > 0 && vistTekst === alleTekst
  // Kun mellemsynteser: slutsvaret har sin egen overgang. En 420 ms tærskel
  // gør at korte synteser aldrig får arbejdslinjen til at blinke.
  const skjulAktivRunde = usePacingWorkLine(
    streaming && !finalAnswerStarted && alleTekst.length > 0 && !pacingFaerdig,
    runId ?? beskedId ?? null,
  )
  const onPacedRef = useRef(onPaced)
  onPacedRef.current = onPaced
  useEffect(() => {
    // Kun EFTER strømmen er slut: undervejs indhenter paceren kilden hele
    // tiden, og et signal dér ville melde «færdig» midt i turen.
    if (!streaming && pacingFaerdig) onPacedRef.current?.()
  }, [streaming, pacingFaerdig])
  return raekker
    ? <RaekkeTranskript blocks={paced} streaming={streaming} finalAnswerStarted={finalAnswerStarted}
        beskedId={beskedId} config={config} rundeEtiketter={rundeEtiketter}
        elapsedMs={elapsedMs} tokens={tokens} varighedSekunder={varighedSekunder}
        skjulAktivRunde={skjulAktivRunde} />
    : <BlocksRenderer blocks={paced} density={density} streaming={streaming}
        rundeEtiketter={rundeEtiketter} tankeResumeer={tankeResumeer}
        beskedId={beskedId} config={config} />
}

/** Besked-række med locked boble-layout: bruger højre (boble), Jarvis venstre
 *  (avatar + tekst, ingen boble). Density videregives til rich-blocks.
 *
 *  memo: afsluttede beskeder har stabile props → re-renderer IKKE når
 *  StreamContext tikker (elapsed-timer hver 500ms). Det er det der gør lange
 *  samtaler tunge — uden memo highlighter hver CodeBlock forfra 2×/sekund. */
function MessageRowImpl({
  role,
  blocks: rawBlocks,
  presentation = 'code',
  chatMode = 'living',
  status,
  workingStep,
  runId,
  turStart,
  turSlut,
  varighedSekunder,
  elapsedMs,
  tokens,
  onWorkExpanded,
  paceFinalAnswer,
  onAnswerPaced,
  density,
  streaming,
  finalAnswerStarted = false,
  rundeEtiketter,
  tankeResumeer,
  createdAt,
  onResend,
  config,
  pinned,
  onTogglePin,
  onRewind,
  beskedId,
  sessionId,
  canUndo,
}: {
  role: 'user' | 'assistant'
  blocks: ContentBlock[]
  presentation?: 'chat' | 'code'
  chatMode?: ActiveChatFlowMode
  status?: StreamStatus
  workingStep?: string | null
  runId?: string | null
  /** Turens starttid (ms epoch) — uret i turhovedet måler turen. */
  turStart?: number | null
  /** Turens sluttid (ms epoch) — uret fryser her og bliver stående. */
  turSlut?: number | null
  /** Turens varighed udledt af transskriptet (persisterede ture). */
  varighedSekunder?: number | null
  /** Hele den aktive turs forløbne tid; code-rækken viser den ved den aktive runde. */
  elapsedMs?: number
  /** Code-turens levende output-token-tal. */
  tokens?: number
  onWorkExpanded?: () => void
  paceFinalAnswer?: boolean
  onAnswerPaced?: () => void
  density: 'compact' | 'full'
  streaming: boolean
  /** Bekræftet slutsvar fra serveren; folder arbejdet mens teksten stadig kommer. */
  finalAnswerStarted?: boolean
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
  /** Filfortrydelse er kun til ejeren og kun for gemte beskeder. */
  sessionId?: string | null
  canUndo?: boolean
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
            {/* Bruger-egne billeder. To slags kilder, og de skal håndteres hver
                for sig — samme forgrening som `BlocksRenderer` bruger for
                Jarvis' billeder:
                  - LIVE/optimistisk: en blob-URL fra composeren → tegnes straks
                  - PERSISTERET: kun en REFERENCE (`attachment_id`) → hentes med
                    token gennem `AttachmentBlock`, fordi `/attachments/...`
                    svarer 401 uden `Authorization`.
                Uden forgreningen stod der `src=''` for alt der kom fra serveren:
                ens egen upload var synlig som preview og forsvandt i samme
                øjeblik serveren overtog beskeden (målt 27/9-2026). Sanitering er
                fortsat forbeholdt Jarvis' (utrusted) indhold — begge veje her er
                brugerens EGNE filer. */}
            {images.map((img, i) => (
              img.src
                ? <KlikbartBillede key={i} src={img.src} alt={img.alt ?? ''} />
                : <AttachmentBlock key={i} block={{ ...img, type: 'image' }} />
            ))}
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
  // Hele beskedens tool-kald er tilgængelige her. Rækkevisningen sender kun
  // slutteksten til BlocksRenderer, så et kort dér missede alle redigeringer.
  const redigerede = !streaming ? redigeredeFiler(blocks) : []
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
            {presentation === 'chat'
              ? <ChatFlowPresentation blocks={blocks} mode={chatMode} density={density}
                  streaming={streaming} status={status ?? (streaming ? 'working' : 'done')}
                  finalAnswerStarted={finalAnswerStarted} workingStep={workingStep}
                  runId={runId} turStart={turStart} turSlut={turSlut} varighedSekunder={varighedSekunder} rundeEtiketter={rundeEtiketter} tankeResumeer={tankeResumeer}
                  beskedId={beskedId} config={config} onWorkExpanded={onWorkExpanded}
                  paceFinalAnswer={paceFinalAnswer} onAnswerPaced={onAnswerPaced} />
              : <CodeAssistantTranscript blocks={blocks} density={density} streaming={streaming} onPaced={onAnswerPaced}
                  finalAnswerStarted={finalAnswerStarted} beskedId={beskedId} config={config}
                  rundeEtiketter={rundeEtiketter} tankeResumeer={tankeResumeer} raekker={raekker}
                  runId={runId}
                  elapsedMs={elapsedMs} tokens={tokens} varighedSekunder={varighedSekunder} />}
            {/* 25/10-2026 (Bjørn): «Åbn visible_runs.py» stod under hvert svar i
                chat mode. Detektionen er rigtig — artifacts.ts regel 3 bygger
                file-artifacts af FAKTISKE tool_use-kald — men i en samtale står
                svaret lige der, og knappen hører til maskinrummet. `presentation`
                fandtes allerede og blev brugt til transskriptet ovenfor; badgen
                var det eneste sted den ikke blev brugt. */}
            {!streaming && presentation !== 'chat' && detectArtifacts(blocks).map((a, i) => (
              <ArtifactAffordance key={`${a.kind}-${i}`} artifact={a} />
            ))}
          </InlineErrorBoundary>
        </div>
      </article>
      {/* 25/10-2026 (Bjørn), to ting med samme rod:
          1. «Redigerede N filer» hører til maskinrummet — i en samtale står
             svaret lige der, og filkortet er arbejde, ikke svar. Gated på
             `presentation`, som artifact-badgen ovenfor.
          2. Begge felter blev vist FØR pacen var færdig. Gaten var `!streaming`,
             men `streaming` bliver falsk når SSE'en er done — ikke når teksten
             er rullet ind. Mellem de to tidspunkter stod felterne færdige under
             en tekst der stadig skrev sig. `paceFinalAnswer` er sand mens
             pacingen kører og falsk når `onAnswerPaced` har meldt færdig, så
             den er den rigtige betingelse: de ruller ind MED pacen. */}
      {!streaming && !paceFinalAnswer && presentation !== 'chat'
        && <EditedFilesCard filer={redigerede} tal={maalteRedigeringer(blocks)}
          diffs={redigeredeDiffPar(blocks)} onAabn={visAendring}
          onFortryd={canUndo && config && sessionId && beskedId
            ? () => apiFetch<{ status: string; files?: number; error?: string }>(config,
                `/workbench/messages/${encodeURIComponent(beskedId)}/undo`,
                { method: 'POST', body: { session_id: sessionId }, retries: 0 })
            : undefined} />}
      {/* Kilderne står tættest på teksten: «hvor ved du det fra?».
          «Forløb»-linjen under dem er slået fra (Bjørn 17/9-2026) — runde-,
          tanke- og skill-linjerne i selve beskeden siger det samme. */}
      {!streaming && !paceFinalAnswer && <Kilder blocks={blocks} />}
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
