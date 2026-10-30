import { useEffect, useRef, useState } from 'react'
import type { ApiConfig } from '../../lib/api'
import { deriveChatFlow } from '../../lib/chatFlowModel'
import type { ContentBlock } from '../../lib/sseProtocol'
import type { StreamStatus } from '../../lib/streamReducer'
import { useChatPacedBlocks } from '../../lib/useChatPacedBlocks'
import { useTurSekunder } from '../../lib/turTid'
import { usePacingWorkLine } from '../../lib/usePacingWorkLine'
import '../../styles/chat-flow.css'
import { BlocksRenderer } from './BlocksRenderer'
import { JarvisRing } from '../shell/JarvisRing'
import { LabelSkift, SynteseLinje } from './LabelSkift'
import { FoldPil, TurHoved } from './TurHoved'
import { RullendeTokens } from '../feedback/RullendeTal'

export interface ChatFlowPresentationProps {
  blocks: ContentBlock[]
  mode: 'living' | 'calm'
  density: 'compact' | 'full'
  streaming: boolean
  status: StreamStatus
  finalAnswerStarted: boolean
  /**
   * Der er kommet arbejde EFTER svar-låsen (et nyt run i samme tur). Hovedet
   * skal folde ud igen, så rundens tekst er synlig mens den kører — uden at
   * det låste svar rives op. Se `StreamState.arbejdeEfterSvar`.
   */
  arbejdeEfterSvar?: boolean
  runId?: string | null
  /** Turens starttid (ms epoch) — uret måler turen, ikke komponentens montering. */
  turStart?: number | null
  /** Turens sluttid (ms epoch) — uret fryser her og bliver stående efter turen. */
  turSlut?: number | null
  /** Turens varighed udledt af transskriptet. Bruges på persisterede ture, hvor
   *  stream-tilstanden (og dermed `turStart`/`turSlut`) ikke findes længere. */
  varighedSekunder?: number | null
  /** Levende output-token-estimat; erstattes af providerens slutmåling. */
  tokens?: number
  workingStep?: string | null
  rundeEtiketter?: Record<string, string>
  tankeResumeer?: Record<string, string>
  beskedId?: string
  config?: ApiConfig
  onWorkExpanded?: () => void
  /** Hold slutsvarets visuelle pacing i live efter message_stop, indtil den
   *  persisterede besked kan overtage uden et dump. */
  paceFinalAnswer?: boolean
  onAnswerPaced?: () => void
}

/**
 * Render one logical answer as one Markdown document.
 *
 * The stream protocol may split a single word across text blocks when an
 * autonomous/follow run crosses a round boundary (for example `L` +
 * `ukket`). The pacing layer already treats all answer text as one continuous
 * target. Keeping the transport blocks separate here would nevertheless make
 * BlocksRenderer create one Markdown paragraph per block, inserting a visual
 * line break that was never present in the text.
 *
 * This is deliberately presentation-only: the original blocks still drive
 * pacing, phases and work/final classification unchanged.
 */
function samletSvarMarkdown(blocks: ContentBlock[]): ContentBlock[] {
  const samlet: ContentBlock[] = []
  for (const block of blocks) {
    const previous = samlet.at(-1)
    if (block.type === 'text' && previous?.type === 'text') {
      samlet[samlet.length - 1] = { ...previous, text: previous.text + block.text }
    } else {
      samlet.push(block)
    }
  }
  return samlet
}

export function ChatFlowPresentation({
  blocks,
  mode,
  density,
  streaming,
  status,
  finalAnswerStarted,
  arbejdeEfterSvar = false,
  runId,
  turStart,
  turSlut,
  varighedSekunder,
  tokens = 0,
  workingStep,
  rundeEtiketter,
  tankeResumeer,
  beskedId,
  config,
  onWorkExpanded,
  paceFinalAnswer = false,
  onAnswerPaced,
}: ChatFlowPresentationProps) {
  // Pace fra FØRSTE levende teksttegn, ikke først efter final_answer_start.
  // No-tool-svar får ingen sådan grænse fra relæet og kunne derfor arve
  // providerens store bidder, mens autonome follow-runs så fine ud. Samme
  // cursor følger nu teksten gennem syntese → slutsvar → message_stop.
  const pacingFinal = finalAnswerStarted || (paceFinalAnswer && status === 'done')
  const pacedBlocks = useChatPacedBlocks(blocks, {
    live: streaming || paceFinalAnswer,
    finalAnswerStarted: pacingFinal,
    paceAllText: streaming,
    // Nøglen er TUREN, ikke runnet (28/10-2026). Cursoren ligger under
    // `${nøgle}:chat-text`; gav et follow-up-run en ny nøgle, faldt cursoren
    // til `''` og svaret blev pacet FORFRA — det Bjørn beskrev som «tom skærm,
    // og så starter slut besked med at pace uden for hoved». Turen har ét
    // starttidspunkt (sat ved `client_turn_start`), og det overlever runderne.
    runId: turStart != null ? `tur-${turStart}` : runId,
  })
  const model = deriveChatFlow({
    blocks: pacedBlocks,
    workingStep,
    rundeEtiketter,
    tankeResumeer,
    finalAnswerStarted,
    status,
  })
  const targetModel = deriveChatFlow({
    blocks,
    workingStep,
    rundeEtiketter,
    tankeResumeer,
    finalAnswerStarted,
    status,
  })
  const confirmedRef = useRef<{ runKey: string; texts: string[] }>({ runKey: '', texts: [] })
  const runKey = runId ?? '__historical-message__'
  const priorConfirmed = confirmedRef.current.runKey === runKey ? confirmedRef.current.texts : []
  let confirmedTexts = priorConfirmed
  if (finalAnswerStarted) {
    confirmedTexts = [...priorConfirmed]
    for (const block of targetModel.finalBlocks) {
      if (block.type !== 'text' || !block.text) continue
      const related = confirmedTexts.findIndex((text) => text.startsWith(block.text) || block.text.startsWith(text))
      if (related < 0) confirmedTexts.push(block.text)
      else if (block.text.length > confirmedTexts[related]!.length) confirmedTexts[related] = block.text
    }
    confirmedRef.current = { runKey, texts: confirmedTexts }
  } else if (confirmedRef.current.runKey !== runKey) {
    confirmedRef.current = { runKey, texts: [] }
  }
  const retainedWork = finalAnswerStarted && confirmedTexts.length > 0
    ? model.workBlocks.filter((block) => block.type !== 'text'
        || !confirmedTexts.some((text) => text === block.text || text.startsWith(block.text) || block.text.startsWith(text)))
    : model.workBlocks
  // Bjørn 20/10-2026: «det hurtige svar skal aldrig vises».
  //
  // `confirmedTexts` er den RÅ tekst fra serveren. Da den blev lagt foran
  // `model.finalBlocks`, stod hele svaret på skærmen i samme frame som turen
  // vendte tilbage til værktøjsarbejde — mens pacen stadig var på de første
  // tegn. Målt: 102 tegn vist mod 2 pacede.
  //
  // De bekræftede tekster findes OGSÅ i `model.workBlocks`, som er PACET.
  // Vi henter dem der i stedet: samme tekster, samme ur, og ingen upacet vej
  // ind i svar-lanen. `retainedWork` filtrerer præcis de samme blokke ud af
  // arbejdsvisningen, så teksten vises ét sted — aldrig to.
  const restoredText = finalAnswerStarted
    ? model.workBlocks.filter((block): block is Extract<ContentBlock, { type: 'text' }> =>
        block.type === 'text'
        && block.text.length > 0
        && confirmedTexts.some((text) => text === block.text
          || text.startsWith(block.text)
          || block.text.startsWith(text)))
    : []
  const answerBlocks = [...restoredText, ...model.finalBlocks]
  const answer = samletSvarMarkdown(answerBlocks)
  const targetSvar = blocks.flatMap((block) => block.type === 'text' ? [block.text] : []).join('')
  const vistSvar = pacedBlocks.flatMap((block) => block.type === 'text' ? [block.text] : []).join('')
  const svarFaerdigPacet = targetSvar.length > 0 && targetSvar === vistSvar
  // Bjørn 29/10-2026: «det bør kun tilføjes naturligt i enden af pacen altså
  // ikk før pacen er slut med en levende forlængning? fade eller sådan noget?»
  //
  // Widgetten er en leverance og hører i bunden (se `leveranceIBunden`), men
  // den skal ikke dukke op MIDT i pacen: den ankommer først når svaret er
  // rullet færdigt. Imens står en PLACEHOLDER med reserveret højde, så det er
  // widgetten der fader ind — ikke layoutet der hopper.
  //
  // `paceFinalAnswer` er gaten: en persisteret besked (uden pace) viser
  // widgetten med det samme, og en tur der ikke paces røres ikke.
  const venterPaaPace = paceFinalAnswer && !svarFaerdigPacet
  const erLeverance = (block: ContentBlock): boolean => block.type === 'file'
    && String(block.mime_type || '').toLowerCase().startsWith('text/html')
    && String(block.kilde || '') === 'generated'
    && !!String(block.attachment_id || '').trim()
  // Leverancen holdes ALTID ude af svar-lanen — ikke kun mens pacen ruller.
  //
  // Målt 29/10-2026 (Bjørn: «widget bliver vist 2 gange nu? men i bunden af
  // beskeden?»): filtreringen var gated på `venterPaaPace`, så i det øjeblik
  // pacen sluttede blev `synligeSvar === answer`, og widgetten stod BÅDE i
  // `.chat-flow-answer` og i leverance-blokken nedenfor. To instanser, begge
  // i bunden. Repro: 4 forekomster af filnavnet i hver. Leverance-blokken er
  // den eneste ejer, så svar-lanen må aldrig bære den.
  const synligeSvar = answer.filter((block) => !erLeverance(block))
  const ventendeLeverancer = venterPaaPace ? answer.filter(erLeverance) : []
  useEffect(() => {
    if (paceFinalAnswer && svarFaerdigPacet) onAnswerPaced?.()
  }, [onAnswerPaced, paceFinalAnswer, svarFaerdigPacet])
  // «Aktiv» er arbejdsfasen: Jarvis kører og har ikke begyndt at svare endnu.
  // Uden for den er turen enten afsluttet eller svaret er begyndt — og så
  // klapper hovedet sammen og arbejdet lægger sig som detaljer.
  const aktiv = streaming && !finalAnswerStarted && model.terminalState === 'active'
  // KUN rundelinjen fader — synteselinjen bliver stående. Første udgave satte
  // attributten på den fælles wrapper `chat-flow-activity`, så både syntese og
  // runde forsvandt i samme fade og skærmen blev tom (Bjørn 22/10-2026: «det
  // var kun runde linjen.. ikk syntese linjen»). Rundelinjen bliver i DOM'en
  // mens pacen ruller, så Jarvis-markørens animation og layoutet ikke hopper,
  // og fader ind igen når pacen er forbi. Korte synteser når ikke tærsklen
  // (420 ms) og blinker derfor aldrig.
  const skjulAktivRunde = usePacingWorkLine(
    aktiv && targetSvar.length > 0 && !svarFaerdigPacet,
    runId ?? beskedId ?? null,
  )
  const activeLine = mode === 'calm'
    ? model.calmStatus
    : model.visibleSynthesis.at(-1)
  // Den levende syntese er den seneste tekstblok i arbejdet — men kun hvis
  // den HAR indhold. En ny tekstblok starter tom, og det tidligere
  // `…?.text.trim() || null` rev linjen ned i netop det øjeblik: den gamle
  // forsvandt, der blev et glip, og den næste kom streamende bagefter
  // (Bjørn 17/10-2026). Vi springer tomme blokke over, så den forrige tekst
  // står stille indtil den nye har noget at vise.
  //
  // `noegle` er blokkens indeks i arbejdet. Det skifter KUN når syntesen
  // erstattes — ikke mens teksten vokser — så visningen kan opdatere på
  // stedet i stedet for at krydsfade ved hvert tegn.
  const levendeSyntese = (() => {
    if (mode !== 'living') return null
    for (let i = model.workBlocks.length - 1; i >= 0; i--) {
      const blok = model.workBlocks[i]
      if (blok && blok.type === 'text' && blok.text.trim()) {
        return { tekst: blok.text.trim(), noegle: i }
      }
    }
    // Femte gate, målt 22/10-2026: `model.workBlocks` er PACET. Når slutsvaret
    // begynder, er de pacede arbejdsblokke tømt — så synteselinjen forsvandt
    // mens rundelinjen blev. Syntesen skal blive stående gennem
    // pacing-vinduet, så vi falder tilbage til de RÅ blokke. Kun teksten
    // bruges til visning; paceren rører ikke denne vej.
    for (let i = targetModel.workBlocks.length - 1; i >= 0; i--) {
      const blok = targetModel.workBlocks[i]
      if (blok && blok.type === 'text' && blok.text.trim()) {
        return { tekst: blok.text.trim(), noegle: i }
      }
    }
    return null
  })()
  const activeSynthesis = levendeSyntese?.tekst ?? null
  // Hovedet skal stå fra FØRSTE ord — også i det vindue hvor turen lige er
  // startet og der endnu ikke er rapporteret arbejde eller synteser.
  // (Bjørn 17/10-2026: «lige som i code mode skal turhoved vises hele tiden
  // før de første ord».) Uden `streaming` her manglede hovedet netop i det
  // øjeblik turen begyndte, og dukkede først op bagefter.
  // Uret: sekunder mens turen kører, frosset når den slutter. Bjørn
  // 17/10-2026: «timer for turen Xm Xs startende med Xs og så Xm osv» — og
  // «ueret skal osse når strømmen er forbi». Derfor måles der til `turSlut`
  // (sat ved `message_stop`), ikke til `aktiv` som bliver falsk allerede når
  // svaret begynder.
  //
  // Persisterede ture har ingen stream-tilstand tilbage. Deres varighed er
  // udledt af transskriptet, så uret også står der (17/10-2026).
  const sekunder = useTurSekunder(turStart, turSlut) ?? varighedSekunder ?? null
  // Hovedet er turens skillestreg — ikke en overskrift for værktøjskald.
  // (Bjørn 17/10-2026: «tur hoved vises ikke hvis han ikk kalder tools… det
  // skal være der osse uden tool kald».) Derfor bæres det af tre ting: der er
  // arbejde at folde, turen kører, eller vi kender dens varighed.
  const harArbejde = model.hasObservableWork
  // Hovedet bliver stående gennem HELE turen — også mens slutsvaret rulles ud
  // efter `message_stop`.
  //
  // 29/10-2026 fjernede jeg det i pace-vinduet (`pacerSvar`), fordi Bjørn
  // beskrev at «pacen kører først inde i hoved». Det var den forkerte læsning
  // af symptomet: teksten lå dengang i ARBEJDSVISNINGEN under hovedet, fordi
  // de bekræftede tekster blev hentet fra de RÅ blokke. Den vej er lukket
  // siden — `restoredText` henter dem fra de PACEDE arbejdsblokke og lægger
  // dem i svar-lanen, og `retainedWork` filtrerer præcis de samme blokke ud af
  // arbejdet. Så pacen ruller allerede UDEN FOR hovedet.
  //
  // Målt 30/10-2026 (Bjørn: «nu forsvinder turhoved og skill linjen indtil
  // svaret er færdig»): gaten fjernede ikke et problem, den fjernede turens
  // skillestreg midt i turen. `.rv-tur` var væk fra DOM'en gennem hele
  // pace-vinduet og dukkede først op da svaret var færdigt. Hovedet er turens
  // vandrette streg — det er dét der fortæller at turen er én tur — så det må
  // ikke forsvinde mens turen stadig løber.
  //
  // Foldet er lukket under pacen (`arbejdeKoerer` er falsk når `streaming` er
  // falsk), så hovedet står som en stille streg over et svar der skriver sig.
  const visTurhoved = harArbejde || streaming || sekunder !== null
  // Rundelinjen må aldrig vise et internt tool-navn. Modellen filtrerer de
  // rå working_step-værdier; indtil den menneskelige etiket er klar, står en
  // rolig fallback i samme stabile celle UNDER syntesen — ikke i turhovedet.
  //
  // Turhovedet ejer allerede den overordnede tilstand «Arbejder». Backendens
  // generiske working_step med samme ord er derfor ikke en ny oplysning i
  // rundelinjen. Mellem de konkrete forklaringer («Læser filen», «Tester …»)
  // viser den i stedet den aktuelle indre fase: «Tænker».
  const generiskArbejde = /^arbejder(?:\s*(?:…|\.\.\.))?$/i.test(activeLine?.trim() ?? '')
  const rundeTekst = harArbejde
    ? (!activeLine || generiskArbejde ? 'Tænker' : activeLine)
    : null

  // ÉN gate — samme form som code mode (`RaekkeTranskript.tsx:434/449/469`).
  //
  // Bjørn 22/10-2026, fjerde runde: «ja gør som i code mode.. det virker». Jeg
  // havde bygget fem gates (`visArbejdslinje`, `aaben`, `rammeAaben`,
  // `arbejdeAabent`, `levendeSyntese`) for at holde linjerne synlige gennem
  // pacing-vinduet — og hver rettelse flyttede fejlen til den næste, fordi
  // `rammeAaben` holdt rammen åben efter at hovedet havde foldet. Resultatet
  // var at foldet så ud som om det ventede på pacen.
  //
  // Code mode har ikke det problem, fordi der kun er ÉN gate: `aaben` følger
  // svarets start, og gruppen skjules i samme frame som hovedet folder. Chat
  // mode gør nu præcis det samme. Glidningen bliver stående i CSS'en, så
  // foldet glider frem for at blinke — men det sker ved svarets start, ikke
  // når pacen er færdig.
  const [aabenManuelt, setAabenManuelt] = useState<boolean | null>(null)
  // Låsen beskytter SVARET, ikke hovedets tilstand (Bjørn 29/10-2026): er der
  // kommet arbejde efter svar-låsen, kører turen stadig og hovedet skal være
  // åbent. Samme formel som code mode (`RaekkeTranskript`: `arbejdeKoerer`).
  const arbejdeKoerer = streaming && (!finalAnswerStarted || arbejdeEfterSvar)
  const aaben = aabenManuelt ?? arbejdeKoerer
  // Arbejdsdetaljerne under rundelinjen. Mens der arbejdes er de foldet
  // sammen som udgangspunkt — den levende linje er nok — men Bjørn kan folde
  // dem ud UNDER streaming (17/10-2026: «runde linjen under streaming bør
  // have > i ende og kunne foldes ud»). Efter turen følger de turhovedets
  // fold, som før.
  const arbejdeAabent = aktiv ? aabenManuelt === true : aaben
  const visArbejdsdetaljer = retainedWork.length > 0 && arbejdeAabent

  return (
    <div className="chat-flow" data-chat-flow-mode={mode}>
      {visTurhoved ? (
        <>
          <TurHoved
            aaben={aaben}
            foldbar={harArbejde}
            koerer={arbejdeKoerer}
            sekunder={sekunder}
            tekst={model.hovedTekst}
            meta={streaming && tokens > 0
              ? <span className="rv-turMeta">~<RullendeTokens tokens={tokens} /> output</span>
              : null}
            skillelinje
            onToggle={() => {
              const naeste = !aaben
              setAabenManuelt(naeste)
              if (naeste) onWorkExpanded?.()
            }}
          />
          {/* Chat mode viser én levende statuslinje ad gangen. Den erstattes
              på stedet under turhovedets streg og forsvinder, når svaret
              begynder. De fulde arbejdsdetaljer er fortsat tilgængelige ved
              at folde en afsluttet tur ud. */}
          {/* Bjørn 20/10-2026: «synteser og runder forsvinder i et blink».
              `hidden` er `display: none` i ÉN frame — der er ingen højde at
              animere fra, så hele billedet rykker sammen med præcis linjernes
              højde. Gruppen bliver derfor stående i DOM'en, og den ydre ramme
              glider fra `1fr` til `0fr` (grid-rækker kan animeres i både
              Chromium og Safari; `height: auto` ville kræve `interpolate-size`,
              som kun Chromium har). */}
          <div className="chat-flow-gruppe-ydre" data-aaben={aaben ? 'true' : 'false'}>
            <div className="chat-flow-gruppe" aria-hidden={!aaben}>
            {aaben && harArbejde && !arbejdeAabent ? (
              <div className={`chat-flow-activity chat-flow-activity--${mode} chat-flow-activity--motion-safe`}
                data-testid="chat-flow-activity" role="status" aria-live="polite" aria-atomic="true"
                aria-label={[activeSynthesis, rundeTekst].filter(Boolean).join('. ')}>
                {levendeSyntese ? (
                  <div className="chat-flow-live-synthesis" data-testid="chat-flow-live-synthesis"
                    aria-hidden="true">
                    <SynteseLinje tekst={levendeSyntese.tekst} noegle={levendeSyntese.noegle} />
                  </div>
                ) : null}
                {rundeTekst ? (
                  <div className="chat-flow-round" data-testid="chat-flow-round"
                    data-pacing-skjult={skjulAktivRunde ? '' : undefined}>
                    <div className="chat-flow-round-line" data-testid="chat-flow-round-line"
                      aria-hidden="true">
                      <span className="chat-flow-presence" data-testid="chat-flow-presence">
                        <JarvisRing size={15} spinning tone="working" />
                      </span>
                      <span className="chat-flow-round-label" data-testid="chat-flow-round-label">
                        <LabelSkift tekst={rundeTekst} arbejder className="shimmer" fastIkon />
                      </span>
                    </div>
                    {retainedWork.length > 0 ? (
                      <button
                        type="button"
                        className="chat-flow-round-fold"
                        data-testid="chat-flow-round-fold"
                        aria-expanded={arbejdeAabent}
                        aria-label={arbejdeAabent ? 'Skjul arbejdet' : 'Vis arbejdet'}
                        onClick={() => setAabenManuelt(!arbejdeAabent)}
                      >
                        <FoldPil aaben={arbejdeAabent} />
                      </button>
                    ) : null}
                  </div>
                ) : null}
              </div>
            ) : null}

            {visArbejdsdetaljer ? (
              <div className="chat-flow-work-details">
                <BlocksRenderer blocks={retainedWork} density={density} streaming={streaming}
                  rundeEtiketter={rundeEtiketter} tankeResumeer={tankeResumeer}
                  visTankeResumeer
                  beskedId={beskedId} config={config} />
              </div>
            ) : null}
            </div>
          </div>
        </>
      ) : null}

      {synligeSvar.length > 0 ? (
        <div className="chat-flow-answer">
          <BlocksRenderer blocks={synligeSvar} density={density} streaming={streaming}
            beskedId={beskedId} config={config} />
        </div>
      ) : null}

      {/* Leverancen (widgetten) ankommer EFTER pacen — ikke midt i den.
          Bjørn 29/10-2026: «det bør kun tilføjes naturligt i enden af pacen».
          Pladsen reserveres mens den venter, så det er widgetten der fader
          ind og ikke layoutet der hopper. */}
      {ventendeLeverancer.length > 0 ? (
        <div className="chat-flow-leverance-plads" data-leverance-plads aria-hidden="true" />
      ) : null}
      {!venterPaaPace && answer.some(erLeverance) ? (
        <div className="chat-flow-leverance" data-leverance="widget" data-ankomst="ankommet">
          <BlocksRenderer blocks={answer.filter(erLeverance)} density={density}
            streaming={streaming} beskedId={beskedId} config={config} />
        </div>
      ) : null}
    </div>
  )
}
